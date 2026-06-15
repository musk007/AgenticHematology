"""
run_orchestrator.py
===================
Entry point showing how to wire the full agentic pipeline with the
two-model detector (YOLOv11 + EfficientNet) under the orchestrator.

Two modes:

  # Development — stub detector replays precomputed JSON (no GPU/models):
  python run_orchestrator.py \\
      --case-id 12 \\
      --backend stub --stub-source examples/sample_cases.json \\
      --instruction "Generate a full diagnostic report"

  # Production — YOLOv11 + EfficientNet:
  python run_orchestrator.py \\
      --case-id PT-0042 \\
      --backend wbc-unified \\
      --yolo-weights weights/yolov11_lld.pt \\
      --effnet-weights weights/best_attr.pt \\
      --images "data/PT-0042/*.png" \\
      --instruction "Generate a full diagnostic report"

  # Production — attribute ablation with DinoBloom linear probes:
  python run_orchestrator.py \\
      --case-id PT-0042 \\
      --backend dinobloom \\
      --yolo-weights weights/yolov11_lld.pt \\
      --dinobloom-weights weights/DinoBloom-B.pth \\
      --dinobloom-attr-weights weights/attribute_dinobloom/best_attr_probes.joblib \\
      --classifier-model weights/leukemia_rf.pkl \\
      --images "data/PT-0042/*.png" \\
      --instruction "Generate a full diagnostic report"
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

try:
    from leukemia_pipeline.detection_agent import StubDetector
    from leukemia_pipeline.leukemia_classifier import HybridClassifier, LearnedClassifier
    from leukemia_pipeline.orchestrator import Orchestrator, OrchestratorRequest, RuleBasedRouter
    from leukemia_pipeline.report_generator import (
        ClaudeReportGenerator,
        LocalLLMReportGenerator,
        OpenAIReportGenerator,
        TemplateReportGenerator,
    )
except ModuleNotFoundError:
    repo_parent = Path(__file__).resolve().parent.parent
    if str(repo_parent) not in sys.path:
        sys.path.insert(0, str(repo_parent))
    from agentic_hematology.detection_agent import StubDetector
    from agentic_hematology.leukemia_classifier import HybridClassifier, LearnedClassifier
    from agentic_hematology.orchestrator import Orchestrator, OrchestratorRequest, RuleBasedRouter
    from agentic_hematology.report_generator import (
        ClaudeReportGenerator,
        LocalLLMReportGenerator,
        OpenAIReportGenerator,
        TemplateReportGenerator,
    )


ROOT = Path(__file__).resolve().parent
WBC_UNIFIED = ROOT / "wbc_unified"
CV = WBC_UNIFIED / "cv"
sys.path.insert(0, str(CV))
from mll_helmholtz import (  # noqa: E402
    resolve_helmholtz_data_root,
    resolve_helmholtz_metadata_json,
    resolve_helmholtz_reports_dir,
)
from dinobloom_infer import resolve_dinobloom_attr_weights, resolve_dinobloom_cell_weights  # noqa: E402
DEFAULT_YOLO_WEIGHTS = WBC_UNIFIED / "cv/runs/detector/train/weights/best.pt"
DEFAULT_EFFNET_WEIGHTS = WBC_UNIFIED / "cv/runs/attribute/train/best_attr.pt"
DEFAULT_CLASSIFIER_MODEL = WBC_UNIFIED / "cv/runs/classifier/leukemia_rf_6class.pkl"
DEFAULT_DINOBLOOM_ATTR_WEIGHTS = resolve_dinobloom_attr_weights()
DEFAULT_DINOBLOOM_CELL_WEIGHTS = resolve_dinobloom_cell_weights()
DEFAULT_DINOBLOOM_KNN_MANIFEST = WBC_UNIFIED / "cv/generated/attr_manifest.csv"
DEFAULT_DINOBLOOM_KNN_CACHE = WBC_UNIFIED / "cv/runs/attribute_dinobloom/knn_train_embeddings.npz"


def _resolve_attribute_model(args) -> str:
    if args.backend == "dinobloom":
        return "dinobloom"
    return getattr(args, "attribute_model", "effnet") or "effnet"


def _resolve_yolo_weights(args) -> str:
    yolo_weights = args.yolo_weights or str(DEFAULT_YOLO_WEIGHTS)
    if not Path(yolo_weights).is_file():
        sys.exit(f"YOLO weights not found: {yolo_weights}")
    return yolo_weights


def _build_yolo_localizer(args):
    try:
        from leukemia_pipeline.detection_agent_v2 import YOLOv11Localizer
    except ModuleNotFoundError:
        from agentic_hematology.detection_agent_v2 import YOLOv11Localizer

    yolo_weights = _resolve_yolo_weights(args)
    print(f"Stage 1 — YOLO localizer: {yolo_weights}", flush=True)
    return YOLOv11Localizer(
        weights_path=yolo_weights,
        conf_threshold=args.conf_threshold,
        iou_threshold=args.iou_threshold,
        image_size=args.det_imgsz,
        batch_size=args.det_batch,
        half_precision=not args.no_half,
        device=args.device,
    )


def _build_attribute_classifier(args):
    attribute_model = _resolve_attribute_model(args)
    if attribute_model == "effnet":
        try:
            from leukemia_pipeline.detection_agent_v2 import EfficientNetAttributeClassifier
        except ModuleNotFoundError:
            from agentic_hematology.detection_agent_v2 import EfficientNetAttributeClassifier
        effnet_weights = args.effnet_weights or str(DEFAULT_EFFNET_WEIGHTS)
        return EfficientNetAttributeClassifier(
            weights_path=effnet_weights,
            device=args.device,
            predicts_cell_type=args.effnet_predicts_celltype,
        )

    if attribute_model == "dinobloom":
        try:
            from leukemia_pipeline.detection_agent_dinobloom import DinoBloomAttributeClassifier
        except ModuleNotFoundError:
            from agentic_hematology.detection_agent_dinobloom import DinoBloomAttributeClassifier

        attr_probes = args.dinobloom_attr_weights
        probes_path = Path(attr_probes) if attr_probes else None
        attr_mode = args.dinobloom_attr_mode
        if attr_mode == "auto" and probes_path and not probes_path.is_file():
            print(
                f"WARNING: DinoBloom attribute weights not found ({attr_probes}); "
                "falling back to k-NN over the train manifest.",
                file=sys.stderr,
            )
            attr_probes = None
            attr_mode = "knn"

        return DinoBloomAttributeClassifier(
            weights_path=args.dinobloom_weights or "auto",
            attr_probes_path=attr_probes,
            variant=args.dinobloom_variant,
            attr_mode=attr_mode,
            knn_manifest_path=args.dinobloom_knn_manifest,
            knn_cache_path=args.dinobloom_knn_cache,
            knn_k=args.dinobloom_knn_k,
            device=args.device,
            hub_dir=args.dinobloom_hub_dir,
        )

    sys.exit(f"Unknown attribute model: {attribute_model}")


def build_detector(args):
    if args.backend == "stub":
        return StubDetector(args.stub_source)
    if args.backend in {"two-stage", "wbc-unified", "dinobloom"}:
        try:
            from leukemia_pipeline.detection_agent_v2 import (
                EfficientNetAttributeClassifier,
                PrecroppedCellAgent,
                TwoStageDetectionAgent,
            )
        except ModuleNotFoundError:
            from agentic_hematology.detection_agent_v2 import (
                EfficientNetAttributeClassifier,
                PrecroppedCellAgent,
                TwoStageDetectionAgent,
            )

        attribute_model = _resolve_attribute_model(args)
        if args.dataset_source == "mll-helmholtz":
            sys.path.insert(0, str(CV))
            from dinobloom_infer import (  # noqa: E402
                build_dinobloom_attr_classifier,
                build_dinobloom_cell_classifier,
                resolve_dinobloom_attr_weights,
                resolve_dinobloom_cell_weights,
            )

            metadata = {}
            meta_path = getattr(args, "helmholtz_metadata", None)
            if meta_path and Path(meta_path).is_file():
                metadata = json.loads(Path(meta_path).read_text(encoding="utf-8"))

            cell_weights = resolve_dinobloom_cell_weights(
                getattr(args, "dinobloom_cell_weights", None) or None
            )
            use_metadata_types = bool(getattr(args, "helmholtz_metadata_cell_types", False))

            if cell_weights.is_file() and not use_metadata_types:
                print(
                    "Building precropped detector: DinoBloom cell classifier + MLP attributes "
                    f"({cell_weights.name})",
                    flush=True,
                )
                cell_clf = build_dinobloom_cell_classifier(
                    device=args.device,
                    cell_weights=cell_weights,
                    attr_weights=resolve_dinobloom_attr_weights(args.dinobloom_attr_weights or None),
                    dinobloom_weights=args.dinobloom_weights or "auto",
                    variant=args.dinobloom_variant,
                    hub_dir=args.dinobloom_hub_dir,
                    fallback_to_yolo_type=False,
                )
                return PrecroppedCellAgent(
                    cell_classifier=cell_clf,
                    helmholtz_metadata=metadata,
                    attribute_head_name="DinoBloom cell + MLP",
                )

            print(
                "Building precropped detector: DinoBloom MLP attributes + metadata cell types "
                "(train cell classifier or drop --helmholtz-metadata-cell-types for image-based types)",
                flush=True,
            )
            attr_weights = resolve_dinobloom_attr_weights(args.dinobloom_attr_weights or None)
            attr_clf = build_dinobloom_attr_classifier(
                device=args.device,
                attr_weights=attr_weights,
                dinobloom_weights=args.dinobloom_weights or "auto",
                variant=args.dinobloom_variant,
                hub_dir=args.dinobloom_hub_dir,
            )
            return PrecroppedCellAgent(
                attribute_classifier=attr_clf,
                helmholtz_metadata=metadata,
                attribute_head_name="DinoBloom MLP",
                use_metadata_cell_types=True,
            )

        print(
            f"Building two-stage detector: YOLO (localize+crop) → {attribute_model} (attributes)",
            flush=True,
        )
        localizer = _build_yolo_localizer(args)
        print(f"Stage 2 — attribute head: {attribute_model}", flush=True)
        attr_clf = _build_attribute_classifier(args)
        head_name = "EfficientNet" if attribute_model == "effnet" else "DinoBloom"
        return TwoStageDetectionAgent(
            localizer=localizer,
            attribute_classifier=attr_clf,
            prefer_efficientnet_celltype=args.effnet_predicts_celltype and attribute_model == "effnet",
            attribute_head_name=head_name,
        )
    sys.exit(f"Unknown backend: {args.backend}")


def build_report_generator(args):
    if args.report_backend == "template":
        return TemplateReportGenerator()
    if args.report_backend == "claude":
        return ClaudeReportGenerator()
    if args.report_backend == "openai":
        return OpenAIReportGenerator()
    if args.report_backend == "local-llm":
        return LocalLLMReportGenerator(
            model_path=args.llm_model,
            adapter_path=args.lora_adapter,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
        )
    sys.exit(f"Unknown report backend: {args.report_backend}")


def resolve_images(args) -> list[str]:
    if not args.images:
        return []
    image_suffixes = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
    paths: list[str] = []
    for spec in args.images:
        matches = sorted(glob.glob(spec))
        for match in matches:
            path = Path(match)
            if path.is_dir():
                paths.extend(
                    str(p)
                    for p in sorted(path.iterdir())
                    if p.suffix.lower() in image_suffixes
                )
            elif path.suffix.lower() in image_suffixes:
                paths.append(str(path))
    return paths


def _discover_patients(patients_dir: str) -> list[tuple[str, str]]:
    """Return [(case_id, images_dir)] for every patient subdirectory that has an images/ folder."""
    root = Path(patients_dir)
    if not root.is_dir():
        sys.exit(f"--patients-dir not found: {patients_dir}")
    patients = []
    for sub in sorted(root.iterdir()):
        if sub.is_dir() and (sub / "images").is_dir():
            patients.append((sub.name, str(sub / "images")))
    if not patients:
        sys.exit(f"No patient subdirectories with an images/ folder found under {patients_dir}")
    return patients


def _discover_helmholtz_patients(data_root: str) -> list[tuple[str, str]]:
    """Return [(patient_id, images_dir)] for Helmholtz control/<patient_id>/ layouts."""
    root = Path(data_root)
    if not root.is_dir():
        sys.exit(f"--helmholtz-data-root not found: {data_root}")
    patients = []
    for sub in sorted(root.iterdir()):
        if sub.is_dir() and not sub.name.startswith("."):
            patients.append((sub.name, str(sub)))
    if not patients:
        sys.exit(f"No patient folders under {data_root}")
    return patients


def _save_outputs(resp, case_id: str, out_dir: str | None) -> None:
    """Write all available pipeline outputs for one case."""
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # Detection + attribute output
    if resp.state.detection_result is not None:
        det = resp.state.detection_result
        det_payload = {
            "patient_id": det.case_id,
            "n_images": det.n_images,
            "detections": [
                {
                    "cell_id": d.cell_id,
                    "image_id": d.image_id,
                    "bbox_xyxy": [round(float(v), 4) for v in d.bbox_xyxy],
                    "class": d.cell_type,
                    "confidence": round(float(d.objectness), 4),
                    "attributes": {
                        k: (int(v >= 0.5) if isinstance(v, (int, float)) else int(bool(v)))
                        for k, v in d.attributes.items()
                        if k != "class_id"
                    },
                    "attribute_probs": {
                        k: round(float(v), 4) for k, v in d.attribute_probs.items()
                    },
                }
                for d in det.detections
            ],
        }
        if out_dir:
            det_path = os.path.join(out_dir, f"case_{case_id}_detections.json")
            with open(det_path, "w") as f:
                json.dump(det_payload, f, indent=2)
            print(f"  Wrote {det_path}  ({len(det.detections)} cells)")
        else:
            print(f"\n[Detection] {len(det.detections)} cells detected across {det.n_images} images")

    # Classification output
    if resp.state.classification is not None:
        clf = resp.state.classification
        clf_payload = {
            "patient_id": resp.case_id,
            "predicted_class": clf.predicted_class,
            "confidence": round(float(clf.confidence), 4),
            "rationale": clf.rationale,
        }
        if out_dir:
            clf_path = os.path.join(out_dir, f"case_{case_id}_classification.json")
            with open(clf_path, "w") as f:
                json.dump(clf_payload, f, indent=2)
            print(f"  Wrote {clf_path}  (class={clf.predicted_class}, conf={clf.confidence:.2f})")
        else:
            print(f"\n[Classification] {clf.predicted_class} (confidence={clf.confidence:.2f})")
            print(f"  Rationale: {clf.rationale}")

    # Report output
    if resp.state.report:
        if out_dir:
            rpt_path = os.path.join(out_dir, f"case_{case_id}_report.md")
            with open(rpt_path, "w") as f:
                f.write(resp.state.report.markdown)
            print(f"  Wrote {rpt_path}")
            print(f"  consistency_passed={resp.state.consistency_passed} "
                  f"llm_output_passed={resp.state.llm_output_passed}")
        else:
            print("\n" + resp.state.report.markdown)

    # Agent reflection trace (decision-control audit trail)
    if out_dir:
        trace_payload = {
            "patient_id": resp.case_id,
            "dataset_source": resp.state.dataset_source,
            "routing_notes": resp.state.routing_notes,
            "agent_actions": resp.state.agent_actions,
            "n_reflect_iterations": resp.state.n_reflect_iterations,
            "flagged_for_review": resp.state.flagged_for_review,
            "review_reasons": resp.state.review_reasons,
        }
        trace_path = os.path.join(out_dir, f"case_{case_id}_agent_trace.json")
        with open(trace_path, "w") as f:
            json.dump(trace_payload, f, indent=2)
        print(f"  Wrote {trace_path}")

    # Explain output
    if resp.answer:
        if out_dir:
            exp_path = os.path.join(out_dir, f"case_{case_id}_explain.txt")
            with open(exp_path, "w") as f:
                f.write(resp.answer)
            print(f"  Wrote {exp_path}")
        else:
            print("\n" + resp.answer)


def _run_one(
    orch,
    case_id: str,
    image_paths: list[str],
    instruction: str,
    out_dir: str | None,
    dataset_source: str = "lld",
) -> bool:
    """Run the orchestrator for a single case and save outputs. Returns True on success."""
    print(f"\n{'='*60}", flush=True)
    print(f"Case: {case_id}  ({len(image_paths)} images)", flush=True)

    req = OrchestratorRequest(
        case_id=case_id,
        image_paths=image_paths,
        instruction=instruction,
        dataset_source=dataset_source,
    )
    resp = orch.handle(req)

    print(f"Intent: {resp.intent.value}  ({resp.routing_rationale})")
    if resp.state.agent_actions:
        print("Agent reflection trace:")
        for a in resp.state.agent_actions:
            ct = f" conf_threshold={a['conf_threshold']}" if a.get("conf_threshold") else ""
            print(f"  [iter {a['iteration']}] {a['action']}: {a['reason']}{ct}")
    if resp.state.flagged_for_review:
        print(f"FLAGGED FOR REVIEW: {'; '.join(resp.state.review_reasons)}")
    if resp.state.errors:
        print("Errors:", file=sys.stderr)
        for e in resp.state.errors:
            print(f"  - {e}", file=sys.stderr)

    _save_outputs(resp, case_id, out_dir)
    return not bool(resp.state.errors)


def main() -> int:
    p = argparse.ArgumentParser()
    # Single-patient mode (--case-id + --images) OR batch mode (--patients-dir).
    mode = p.add_mutually_exclusive_group(required=False)
    mode.add_argument("--case-id", help="Single patient case ID.")
    mode.add_argument("--patients-dir",
                      help="LLD batch: subdirectories with images/ subfolder. "
                           "For MLL Helmholtz batch use --dataset-source mll-helmholtz instead.")
    p.add_argument(
        "--backend",
        choices=["stub", "two-stage", "wbc-unified", "dinobloom"],
        default="dinobloom",
        help="Detection stack. Default: dinobloom (DinoBloom-L MLP attributes).",
    )
    p.add_argument(
        "--attribute-model",
        choices=["effnet", "dinobloom"],
        default="dinobloom",
        help="Attribute head: dinobloom (default, DinoBloom-L MLP) or effnet.",
    )
    p.add_argument("--stub-source")
    p.add_argument("--yolo-weights", default=str(DEFAULT_YOLO_WEIGHTS))
    p.add_argument("--effnet-weights", default=str(DEFAULT_EFFNET_WEIGHTS))
    p.add_argument("--effnet-predicts-celltype", action="store_true")
    p.add_argument(
        "--dinobloom-weights",
        default="auto",
        help="DinoBloom checkpoint path, or 'auto' to download MarrLab/DinoBloom from HuggingFace.",
    )
    p.add_argument(
        "--dinobloom-attr-weights",
        default=str(DEFAULT_DINOBLOOM_ATTR_WEIGHTS),
        help="Trained DinoBloom attribute head (.pt) or sklearn probes (.joblib). "
             "Falls back to k-NN if file missing and mode=auto.",
    )
    p.add_argument(
        "--dinobloom-cell-weights",
        default=str(DEFAULT_DINOBLOOM_CELL_WEIGHTS),
        help="Trained DinoBloom cell-type head (.pt) for MLL Helmholtz precropped path.",
    )
    p.add_argument(
        "--helmholtz-metadata-cell-types",
        action="store_true",
        help="Use annotated metadata differentials for cell types instead of the cell classifier.",
    )
    p.add_argument(
        "--dinobloom-attr-mode",
        choices=["auto", "probes", "knn"],
        default="probes",
        help="Attribute inference: probes (default, trained MLP), knn, or auto.",
    )
    p.add_argument(
        "--dinobloom-knn-manifest",
        default=str(DEFAULT_DINOBLOOM_KNN_MANIFEST),
        help="Train manifest for k-NN attribute retrieval (default: cv/generated/attr_manifest.csv).",
    )
    p.add_argument(
        "--dinobloom-knn-cache",
        default=str(DEFAULT_DINOBLOOM_KNN_CACHE),
        help="Cached train embeddings for k-NN (built once on first run).",
    )
    p.add_argument("--dinobloom-knn-k", type=int, default=5, help="k for DinoBloom k-NN attributes.")
    p.add_argument("--dinobloom-variant", choices=["s", "b", "l", "g"], default="l")
    p.add_argument("--dinobloom-hub-dir",
                   help="Optional torch.hub cache dir for facebookresearch/dinov2.")
    p.add_argument("--images", nargs="*",
                   help="Image paths/globs for single-patient mode (ignored with --patients-dir).")
    p.add_argument("--conf-threshold", type=float, default=0.25)
    p.add_argument("--iou-threshold", type=float, default=0.5)
    p.add_argument("--det-imgsz", type=int, default=640)
    p.add_argument("--det-batch", type=int, default=1)
    p.add_argument("--no-half", action="store_true")
    p.add_argument("--device", default=None)
    p.add_argument(
        "--classifier-model",
        default=str(DEFAULT_CLASSIFIER_MODEL),
        help="Pickled patient-level leukemia classifier (RandomForest).",
    )
    p.add_argument(
        "--dataset-source",
        choices=["auto", "lld", "mll-helmholtz"],
        default="lld",
        help="Input layout: LLD PBS tiles (YOLO) or MLL Helmholtz pre-cropped cells (skip YOLO).",
    )
    p.add_argument(
        "--helmholtz-data-root",
        default=str(resolve_helmholtz_data_root() / "control"),
        help="Root with one folder per control patient (used with --dataset-source mll-helmholtz).",
    )
    p.add_argument(
        "--helmholtz-metadata",
        default=str(resolve_helmholtz_metadata_json()),
        help="Patient metadata JSON for MLL cell-type assignment.",
    )
    p.add_argument(
        "--helmholtz-reports-dir",
        default=str(resolve_helmholtz_reports_dir()),
        help="Directory of Helmholtz template reports (one .txt per case).",
    )
    p.add_argument(
        "--include-healthy-class",
        action="store_true",
        help="Enable 6-class HybridClassifier rules (Healthy threshold).",
    )
    p.add_argument(
        "--healthy-cell-pct-threshold",
        type=float,
        default=65.0,
        help="Rule threshold: mature WBC %% for Healthy call (default 65).",
    )
    p.add_argument("--report-backend", choices=["template", "local-llm", "claude", "openai"], default="template")
    p.add_argument("--llm-model", help="Local base model path for --report-backend local-llm")
    p.add_argument("--lora-adapter", help="Optional LoRA adapter path for local LLM reports")
    p.add_argument("--max-new-tokens", type=int, default=768)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--instruction", default="diagnose this case")
    p.add_argument("--no-agent", action="store_true",
                   help="Disable the agentic LLM router + reflection loop (runs the "
                        "deterministic automated pipeline only).")
    p.add_argument("--max-reflect-iterations", type=int, default=2,
                   help="Max reflection-agent iterations before forced escalation.")
    p.add_argument("--out", help="Output directory. In batch mode each patient gets its own subdirectory.")
    args = p.parse_args()

    ################################################
    # Build shared pipeline components (once, even in batch mode)
    ################################################
    detector = build_detector(args)
    learned = None
    if args.classifier_model and Path(args.classifier_model).is_file():
        model_path = Path(args.classifier_model)
        meta_path = model_path.with_name(f"{model_path.stem}_meta.json")
        learned = LearnedClassifier(
            model_path=model_path,
            meta_path=meta_path if meta_path.is_file() else None,
        )
    elif args.classifier_model:
        print(f"WARNING: classifier model not found ({args.classifier_model}); using rule-based classifier.",
              file=sys.stderr)
    classifier = HybridClassifier(
        learned=learned,
        include_healthy_class=args.include_healthy_class,
        healthy_cell_pct_threshold=args.healthy_cell_pct_threshold,
    )
    report_gen = build_report_generator(args)

    reflection_agent = None
    router = RuleBasedRouter()
    llm_explain = None
    if not args.no_agent:
        print("Agentic mode enabled: initializing LLM router and reflection agent.", flush=True)
        try:
            from agentic_hematology.agent_controller import QwenLLMClient, ReflectionAgent
            from agentic_hematology.orchestrator import LLMRouter
        except ModuleNotFoundError:
            from leukemia_pipeline.agent_controller import QwenLLMClient, ReflectionAgent  # type: ignore
            from leukemia_pipeline.orchestrator import LLMRouter  # type: ignore

        llm_client = QwenLLMClient(
            model_path=args.llm_model,
            adapter_path=args.lora_adapter,
            max_new_tokens=256,
            temperature=0.0,
        )
        reflection_agent = ReflectionAgent(llm_client)
        router = LLMRouter(llm_client.complete, fallback=RuleBasedRouter())
        llm_explain = llm_client.complete
        print("Agentic components initialized.", flush=True)

        if args.report_backend == "local-llm" and isinstance(report_gen, LocalLLMReportGenerator):
            try:
                report_gen.attach(llm_client.model, llm_client.tokenizer)
                print("Sharing one Qwen3 instance across agent and report generator.")
            except Exception as e:
                print(f"WARNING: could not share Qwen3 instance ({e}); "
                      f"falling back to separate loads.", file=sys.stderr)

    orch = Orchestrator(
        detector=detector,
        classifier=classifier,
        report_generator=report_gen,
        router=router,
        reflection_agent=reflection_agent,
        max_reflect_iterations=args.max_reflect_iterations,
        llm_explain=llm_explain,
    )

    ################################################
    # Single-patient mode
    ################################################
    if args.case_id:
        images = resolve_images(args)
        if args.backend != "stub" and not images:
            sys.exit("No images matched --images. Provide one or more patient image paths/globs.")
        _run_one(orch, args.case_id, images, args.instruction, args.out, args.dataset_source)
        return 0

    ################################################
    # Batch mode — iterate over all patients
    ################################################
    if args.dataset_source == "mll-helmholtz":
        patients = _discover_helmholtz_patients(args.helmholtz_data_root)
        batch_label = args.helmholtz_data_root
    elif args.patients_dir:
        patients = _discover_patients(args.patients_dir)
        batch_label = args.patients_dir
    else:
        sys.exit("Batch mode requires --patients-dir (LLD) or --dataset-source mll-helmholtz.")
    print(f"Batch mode: {len(patients)} patients found under {batch_label}", flush=True)

    image_suffixes = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
    failed: list[str] = []
    for i, (case_id, images_dir) in enumerate(patients, 1):
        image_paths = sorted(
            str(p) for p in Path(images_dir).iterdir()
            if p.suffix.lower() in image_suffixes
        )
        if not image_paths:
            print(f"[{i}/{len(patients)}] Skipping {case_id}: no images in {images_dir}",
                  file=sys.stderr)
            failed.append(case_id)
            continue

        # In batch mode each patient writes into its own subdirectory.
        out_dir = os.path.join(args.out, case_id) if args.out else None
        try:
            ok = _run_one(orch, case_id, image_paths, args.instruction, out_dir, args.dataset_source)
            if not ok:
                failed.append(case_id)
        except Exception as exc:
            print(f"[{i}/{len(patients)}] ERROR for {case_id}: {exc}", file=sys.stderr)
            failed.append(case_id)

    print(f"\nBatch complete: {len(patients) - len(failed)}/{len(patients)} succeeded.")
    if failed:
        print(f"Failed: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())