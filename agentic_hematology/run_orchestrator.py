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

  # Production — real YOLOv11 + EfficientNet:
  python run_orchestrator.py \\
      --case-id PT-0042 \\
      --backend two-stage \\
      --yolo-weights weights/yolov11_lld.pt \\
      --effnet-weights weights/effnet_attrs.ts \\
      --images "data/PT-0042/*.png" \\
      --instruction "Generate a full diagnostic report" \\
      --report-backend claude
"""

from __future__ import annotations

import argparse
import glob
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


def build_detector(args):
    if args.backend == "stub":
        return StubDetector(args.stub_source)
    if args.backend in {"two-stage", "wbc-unified"}:
        # Imported lazily so the stub path doesn't require torch/ultralytics.
        try:
            from leukemia_pipeline.detection_agent_v2 import (
                EfficientNetAttributeClassifier,
                TwoStageDetectionAgent,
                YOLOv11Localizer,
            )
        except ModuleNotFoundError:
            from agentic_hematology.detection_agent_v2 import (
                EfficientNetAttributeClassifier,
                TwoStageDetectionAgent,
                YOLOv11Localizer,
            )
        yolo_weights = args.yolo_weights or str(WBC_UNIFIED / "cv/runs/detector/train/weights/best.pt")
        effnet_weights = args.effnet_weights or str(WBC_UNIFIED / "cv/runs/attribute/train/best_attr.pt")
        localizer = YOLOv11Localizer(
            weights_path=yolo_weights,
            conf_threshold=args.conf_threshold,
            iou_threshold=args.iou_threshold,
            image_size=args.det_imgsz,
            batch_size=args.det_batch,
            half_precision=not args.no_half,
            device=args.device,
        )
        attr_clf = EfficientNetAttributeClassifier(
            weights_path=effnet_weights,
            device=args.device,
            predicts_cell_type=args.effnet_predicts_celltype,
        )
        return TwoStageDetectionAgent(
            localizer=localizer,
            attribute_classifier=attr_clf,
            prefer_efficientnet_celltype=args.effnet_predicts_celltype,
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


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--case-id", required=True)
    p.add_argument("--backend", choices=["stub", "two-stage", "wbc-unified"], default="wbc-unified")
    p.add_argument("--stub-source")
    p.add_argument("--yolo-weights")
    p.add_argument("--effnet-weights")
    p.add_argument("--effnet-predicts-celltype", action="store_true")
    p.add_argument("--images", nargs="*")
    p.add_argument("--conf-threshold", type=float, default=0.25)
    p.add_argument("--iou-threshold", type=float, default=0.5)
    p.add_argument("--det-imgsz", type=int, default=640)
    p.add_argument("--det-batch", type=int, default=1)
    p.add_argument("--no-half", action="store_true")
    p.add_argument("--device", default=None)
    p.add_argument("--classifier-model", help="Optional pickled sklearn model.")
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
    p.add_argument("--out")
    args = p.parse_args()

    detector = build_detector(args)
    images = resolve_images(args)
    if args.backend != "stub" and not images:
        sys.exit("No images matched --images. Provide one or more patient image paths/globs.")
    learned = LearnedClassifier(model_path=args.classifier_model) if args.classifier_model else None
    classifier = HybridClassifier(learned=learned)
    report_gen = build_report_generator(args)

    # --- Agentic components: one shared Qwen3 client drives the LLM router,
    #     the reflection agent, and EXPLAIN answers. Enabled unless --no-agent.
    reflection_agent = None
    router = RuleBasedRouter()
    llm_explain = None
    if not args.no_agent:
        try:
            from agentic_hematology.agent_controller import (
                QwenLLMClient,
                ReflectionAgent,
            )
            from agentic_hematology.orchestrator import LLMRouter
        except ModuleNotFoundError:
            from leukemia_pipeline.agent_controller import (  # type: ignore
                QwenLLMClient,
                ReflectionAgent,
            )
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

        # Share one Qwen3 instance: if the report backend is also the local
        # LLM, reuse the agent's loaded weights instead of loading a second
        # copy. Both QwenLLMClient and LocalLLMReportGenerator were given the
        # same --llm-model and --lora-adapter, so the loaded model is
        # identical and safe to share. The load happens lazily here.
        if (
            args.report_backend == "local-llm"
            and isinstance(report_gen, LocalLLMReportGenerator)
        ):
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

    req = OrchestratorRequest(
        case_id=args.case_id,
        image_paths=images,
        instruction=args.instruction,
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

    if resp.answer:
        print("\n" + resp.answer)

    if resp.state.report:
        if args.out:
            import os
            os.makedirs(args.out, exist_ok=True)
            path = os.path.join(args.out, f"case_{args.case_id}_report.md")
            with open(path, "w") as f:
                f.write(resp.state.report.markdown)
            print(f"Wrote {path}")
            print(f"  consistency_passed={resp.state.consistency_passed} "
                  f"llm_output_passed={resp.state.llm_output_passed}")
        else:
            print("\n" + resp.state.report.markdown)

    return 0


if __name__ == "__main__":
    sys.exit(main())