"""Report generation backends for the agentic hematology orchestrator."""
from __future__ import annotations

import json
import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .schemas import AggregatedFindings, GroundedReport, LeukemiaClassification


ROOT = Path(__file__).resolve().parent
WBC_UNIFIED = ROOT / "wbc_unified"
if str(WBC_UNIFIED) not in sys.path:
    sys.path.insert(0, str(WBC_UNIFIED))


def _load_default_cfg() -> dict[str, Any]:
    cfg_path = WBC_UNIFIED / "config" / "default.yaml"
    if cfg_path.is_file():
        import yaml

        return yaml.safe_load(cfg_path.read_text()) or {}
    return {}


class BaseReportGenerator(ABC):
    @abstractmethod
    def generate(
        self,
        findings: AggregatedFindings,
        classification: LeukemiaClassification | None,
        instruction: str | None = None,
    ) -> GroundedReport:
        raise NotImplementedError


class TemplateReportGenerator(BaseReportGenerator):
    """Deterministic report backend using the wbc_unified template."""

    def __init__(self, cfg: dict[str, Any] | None = None):
        self.cfg = cfg or _load_default_cfg()

    def generate(
        self,
        findings: AggregatedFindings,
        classification: LeukemiaClassification | None,
        instruction: str | None = None,
    ) -> GroundedReport:
        from report.src.template_report import generate_template_report

        summary = _summary_with_agent_context(findings, classification, instruction)
        markdown = generate_template_report(summary, self.cfg)
        markdown = _append_quantitative_summary(markdown, findings)
        markdown = _append_grounding(markdown, findings, classification)
        return GroundedReport(
            markdown=markdown,
            grounding_index=findings.grounding_index,
            backend="template",
        )


class LocalLLMReportGenerator(BaseReportGenerator):
    """Local HuggingFace/Qwen backend with optional LoRA adapter."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        adapter_path: str | Path | None = None,
        max_new_tokens: int = 768,
        temperature: float = 0.0,
    ):
        cfg = _load_default_cfg()
        inf = cfg.get("inference", {})
        self.model_path = Path(model_path or os.environ.get("MODEL_PATH") or inf.get("base_model"))
        adapter = adapter_path or os.environ.get("LORA_ADAPTER") or inf.get("lora_adapter")
        self.adapter_path = Path(adapter) if adapter else None
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self._model = None
        self._tokenizer = None

    def attach(self, model, tokenizer) -> "LocalLLMReportGenerator":
        """Reuse an already-loaded model/tokenizer (e.g. from QwenLLMClient)
        so only one copy of the weights is resident on the GPU."""
        self._model = model
        self._tokenizer = tokenizer
        return self

    def generate(
        self,
        findings: AggregatedFindings,
        classification: LeukemiaClassification | None,
        instruction: str | None = None,
    ) -> GroundedReport:
        from report.src.llm_infer import generate_from_messages, load_model_and_tokenizer

        if self._model is None or self._tokenizer is None:
            self._model, self._tokenizer = load_model_and_tokenizer(
                self.model_path,
                self.adapter_path,
            )
        summary = _summary_with_agent_context(findings, classification, instruction)
        messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a hematopathology assistant. Write a structured peripheral blood "
                        "smear report narrative in Markdown using ONLY the supplied JSON. "
                        "Your output must resemble a hematology report, but you must NOT generate "
                        "any quantitative table, count table, QC section, or cell grounding section; "
                        "those will be appended deterministically by the pipeline.\n\n"

                        "Output exactly these sections:\n"
                        "**Morphologic interpretation:** one concise paragraph.\n"
                        "**Diagnostic flags:** semicolon-separated flags supported by the JSON.\n"
                        "**Impression:** one diagnosis line using case_summary['agentic_classification']['predicted_class'].\n"
                        "**Differential considerations:** 2–4 bullet points.\n"
                        "**Recommended workup:** 3–5 bullet points.\n\n"

                        "Strict rules:\n"
                        "- Do not invent numbers, percentages, counts, morphology, clinical history, CBC values, cytogenetics, or immunophenotype.\n"
                        "- Do not create a Differential table.\n"
                        "- Do not create a Quantitative Cell Summary.\n"
                        "- Do not create an Agentic Diagnosis section.\n"
                        "- Do not create a Cell Grounding section.\n"
                        "- Do not say a cell type is absent if it appears anywhere in case_summary['differential_pct'].\n"
                        "- Use only the predicted diagnosis from case_summary['agentic_classification'].\n"
                        "- For morphology, use only case_summary['morphology_cohort']; if morphology values are generic or unavailable, keep the interpretation conservative.\n"
                        "- Do not use textbook morphology for ALL/AML/CML/CLL/APML unless it is supported by this patient's JSON.\n"
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Instruction: {instruction or 'Diagnose this case'}\n\n"
                        f"<case_summary>\n{json.dumps(summary, indent=2)}\n</case_summary>"
                    ),
                },
            ]
        markdown = generate_from_messages(
            self._model,
            self._tokenizer,
            messages,
            max_new_tokens=self.max_new_tokens,
            temperature=self.temperature,
        )
        markdown = _append_quantitative_summary(markdown, findings)
        markdown = _append_grounding(
            markdown,
            findings,
            classification,
        )

        return GroundedReport(
            markdown=markdown,
            grounding_index=findings.grounding_index,
            backend="local_llm",
        )


class ClaudeReportGenerator(TemplateReportGenerator):
    """Placeholder kept for CLI compatibility; uses template unless extended."""


class OpenAIReportGenerator(TemplateReportGenerator):
    """Placeholder kept for CLI compatibility; uses template unless extended."""


def _summary_with_agent_context(
    findings: AggregatedFindings,
    classification: LeukemiaClassification | None,
    instruction: str | None,
) -> dict[str, Any]:
    summary = dict(findings.report_ready)
    summary["user_instruction"] = instruction or "Diagnose this case"
    if classification is not None:
        summary["agentic_classification"] = {
            "predicted_class": classification.predicted_class,
            "confidence": classification.confidence,
            "rationale": classification.rationale,
            "scores": classification.scores,
        }
        summary["disease_label_file"] = classification.predicted_class
    summary["grounding_index"] = findings.grounding_index
    return summary


def _append_quantitative_summary(markdown: str, findings: AggregatedFindings) -> str:
    summary = findings.report_ready
    lines = [markdown.rstrip(), "", "## Quantitative Cell Summary", ""]
    lines.append(
        f"- Fields of view: {summary.get('n_images', findings.n_images)}"
    )
    lines.append(
        f"- Detected cells: {summary.get('n_cells_total', findings.n_cells_total)}"
    )
    lines.append(
        f"- Informative WBCs: {summary.get('n_cells_informative', findings.n_cells_identified_wbc)}"
    )
    lines.append(
        f"- Artefacts/non-WBC detections: {summary.get('n_cells_artifact', 0)}"
    )
    lines.append("")
    lines.append("| Cell type | Count | % informative WBCs |")
    lines.append("|---|---:|---:|")
    pct = findings.cell_percentages_clinical
    for cell_type, count in sorted(
        findings.cell_counts.items(),
        key=lambda item: (-item[1], item[0]),
    ):
        lines.append(f"| {cell_type} | {count} | {pct.get(cell_type, 0.0)}% |")

    return "\n".join(lines)


def _append_grounding(
    markdown: str,
    findings: AggregatedFindings,
    classification: LeukemiaClassification | None,
    limit: int = 8,
) -> str:
    lines = [markdown.rstrip(), "", "## Agentic Diagnosis"]

    if classification is not None:
        lines.append(
            f"Predicted diagnosis: **{classification.predicted_class}** "
            f"(confidence {classification.confidence:.2f}). "
            f"Rationale: {classification.rationale}."
        )
    else:
        lines.append(
            "No leukemia classification was available for this report."
        )

    lines.extend(["", "## Cell Grounding", ""])

    for cell_id, rec in list(findings.grounding_index.items())[:limit]:
        attrs = rec.get("attributes", {})
        pos = [name.replace("_", " ").lower() for name, val in attrs.items() if val]
        morph = "; ".join(pos[:4]) if pos else "no positive morphology attributes"

        lines.append(
            f"- `{cell_id}` in `{rec['image_id']}` bbox={rec['bbox_xyxy']}: "
            f"{rec['cell_type']} ({rec['confidence']:.2f}); {morph}."
        )

    return "\n".join(lines)