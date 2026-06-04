"""
report_generator.py
===================
LLM-based grounded report generator.

Architecture
------------
- `BaseReportGenerator` is the interface every backend implements.
- `TemplateReportGenerator` is a zero-dependency, fully-deterministic
  fallback (no LLM). Useful for testing and as a safe default when no API
  key is configured.
- `ClaudeReportGenerator` calls the Anthropic API.
- `OpenAIReportGenerator` calls the OpenAI / GPT-4o API.

All generators take the same inputs:
- the structured `AggregatedFindings`
- the patient-level `LeukemiaClassification`
- the original `DetectionResult` (so we can build the grounding index)

All generators emit a `GroundedReport`. Every clinical claim in the
markdown is tagged with an inline citation key like `[C3]`, and the
`citations` dict maps each key to the list of cell_ids supporting it.

For LLM-based generators, the prompt builder:
- Encodes WHO/ICC criteria for the predicted class.
- Lists every available cell_id with its type and bounding box.
- Tells the LLM explicitly to insert `[C#]` citation markers in its output
  and emit a parallel JSON block mapping each `[C#]` to cell_ids.
"""

from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from typing import Any

from .schemas import (
    AggregatedFindings,
    DetectionResult,
    GroundedReport,
    LeukemiaClassification,
)


# ---------------------------------------------------------------------------
# WHO/ICC criteria knowledge base — small, focused, easy to extend.
# In production, swap this for retrieval over the full WHO 5th ed. + ICC.
# ---------------------------------------------------------------------------

WHO_ICC_CRITERIA: dict[str, dict[str, Any]] = {
    "ALL": {
        "full_name": "Acute Lymphoblastic Leukemia / Lymphoma",
        "key_morphology": [
            "Lymphoblasts comprising >= 20% of WBCs (WHO/ICC threshold).",
            "Small-to-medium cells with scanty cytoplasm and high N:C ratio.",
            "Open/finely dispersed chromatin; inconspicuous nucleoli (FAB L1) "
            "or one or more prominent nucleoli (FAB L2).",
        ],
        "confirmatory_workup": [
            "Flow cytometric immunophenotyping for lineage (B-ALL vs T-ALL).",
            "Bone marrow aspirate and trephine biopsy.",
            "Cytogenetics + FISH for BCR::ABL1, KMT2A, ETV6::RUNX1, TCF3::PBX1.",
            "Molecular: BCR::ABL1-like signature; IKZF1; CSF examination.",
        ],
    },
    "AML": {
        "full_name": "Acute Myeloid Leukemia",
        "key_morphology": [
            "Myeloblasts and/or monoblasts >= 20% of WBCs.",
            "Medium-to-large cells with prominent nucleoli and moderate-to-"
            "abundant basophilic cytoplasm.",
            "Auer rods (when present) are pathognomonic for AML.",
        ],
        "confirmatory_workup": [
            "Flow cytometry: CD13, CD33, CD117, MPO, HLA-DR.",
            "Bone marrow aspirate and biopsy.",
            "Cytogenetics + FISH for recurrent AML abnormalities.",
            "Molecular: NPM1, FLT3-ITD/TKD, CEBPA, RUNX1, TP53, AML fusion screen.",
        ],
    },
    "APML": {
        "full_name": "Acute Promyelocytic Leukemia (APL)",
        "key_morphology": [
            "Abnormal promyelocytes dominate the smear.",
            "Hypergranular cytoplasm; bilobed or folded ('butterfly') nuclei.",
            "Faggot cells (bundles of Auer rods) when present are diagnostic.",
        ],
        "confirmatory_workup": [
            "URGENT PML::RARA testing (RT-PCR or FISH) — APL is a medical "
            "emergency; initiate ATRA on clinical suspicion.",
            "Coagulation panel (PT/PTT, fibrinogen, D-dimer) — DIC risk.",
            "Flow cytometry: CD33+, CD13+, CD117 +/-, HLA-DR negative, CD34 negative.",
            "Cytogenetics for t(15;17) and variant RARA translocations.",
        ],
    },
    "CML": {
        "full_name": "Chronic Myeloid Leukemia",
        "key_morphology": [
            "Full spectrum of granulocytic maturation: myelocytes, "
            "metamyelocytes, mature neutrophils.",
            "Basophilia is a hallmark; eosinophilia often co-exists.",
            "Blast count typically < 10% in chronic phase; 10-19% accelerated "
            "phase; >= 20% blast phase.",
        ],
        "confirmatory_workup": [
            "BCR::ABL1 RT-PCR (qualitative and quantitative).",
            "FISH for t(9;22) / Philadelphia chromosome.",
            "Bone marrow aspirate + cytogenetics.",
            "Sokal / EUTOS / ELTS risk score; baseline IS transcript level.",
        ],
    },
    "CLL": {
        "full_name": "Chronic Lymphocytic Leukemia / Small Lymphocytic Lymphoma",
        "key_morphology": [
            "Small mature lymphocytes with clumped/coarse chromatin and "
            "inconspicuous nucleoli.",
            "Smudge cells are characteristic on Wright-Giemsa smear.",
            "Sustained absolute lymphocyte count >= 5 x 10^9/L of clonal B cells.",
        ],
        "confirmatory_workup": [
            "Flow cytometry CLL panel: CD5, CD19, CD20, CD23, CD79b, FMC7, "
            "kappa/lambda restriction.",
            "Matutes/CLL score; FISH del(13q), del(11q), del(17p), trisomy 12.",
            "IGHV mutation status; TP53 sequencing.",
            "Beta-2 microglobulin; Rai/Binet staging.",
        ],
    },
    "UNCLASSIFIED": {
        "full_name": "Unclassified abnormal smear",
        "key_morphology": [
            "Findings do not match a specific WHO/ICC entity on morphology alone.",
        ],
        "confirmatory_workup": [
            "Flow cytometric immunophenotyping.",
            "Bone marrow aspirate and trephine biopsy.",
            "Broad cytogenetic and molecular workup.",
            "Correlation with clinical findings and CBC.",
        ],
    },
}


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class BaseReportGenerator(ABC):
    @abstractmethod
    def generate(
        self,
        findings: AggregatedFindings,
        classification: LeukemiaClassification,
        detection_result: DetectionResult,
        clinical_context: str | None = None,
    ) -> GroundedReport:
        ...


# ---------------------------------------------------------------------------
# Shared prompt-building helpers
# ---------------------------------------------------------------------------

def build_findings_summary(findings: AggregatedFindings) -> str:
    """Compact JSON-y view of the case for the LLM prompt."""
    rr = findings.report_ready
    diff_sorted = sorted(
        findings.cell_percentages_clinical.items(),
        key=lambda kv: kv[1],
        reverse=True,
    )
    diff_str = "; ".join(f"{cell}: {pct:.1f}%" for cell, pct in diff_sorted)
    flags_on = [k for k, v in rr["diagnostic_flags"].items() if v]

    return (
        f"Case ID: {findings.case_id}\n"
        f"Fields of view: {findings.n_images}\n"
        f"Total annotated: {findings.n_cells_total} "
        f"(informative WBC: {findings.n_cells_identified_wbc}, "
        f"artefacts: {findings.n_cells_total - findings.n_cells_identified_wbc})\n"
        f"Differential (clinical denominator): {diff_str}\n"
        f"Dominant cell: {rr['dominant_cell_type']} "
        f"({rr['dominant_cell_pct']:.1f}%)\n"
        f"Blast pool: {rr['blast_pool_percentage_of_wbc']:.1f}% of WBC\n"
        f"Diagnostic flags ON: {', '.join(flags_on) if flags_on else 'none'}\n"
    )


def build_blast_morphology_summary(findings: AggregatedFindings) -> str:
    morph = findings.report_ready["blast_morphology"]
    lines = []
    for attr, val in morph.items():
        if val["dominant"]:
            lines.append(f"{attr}={val['dominant']} ({val['dominance_pct']:.1f}%)")
    return "; ".join(lines) if lines else "no blast cohort"


def build_grounding_inventory(
    findings: AggregatedFindings,
    detection_result: DetectionResult,
    max_per_finding: int = 5,
) -> tuple[str, dict[str, list[str]]]:
    """
    Build the inventory of cell_ids the LLM can cite, plus a compact text
    description it can copy citation tokens from. We cap per-finding lists
    so the prompt stays short.
    """
    bbox_by_id = {d.cell_id: d.bbox_xyxy for d in detection_result.detections}

    inventory_lines = ["Available citation tokens (cell_id → bbox):"]
    citation_pool: dict[str, list[str]] = {}

    for finding_key, cell_ids in findings.grounding_index.items():
        if not cell_ids:
            continue
        capped = cell_ids[:max_per_finding]
        citation_pool[finding_key] = cell_ids  # full list kept in code, capped in prompt
        inventory_lines.append(f"  [{finding_key}]: {len(cell_ids)} cells total. Examples:")
        for cid in capped:
            bb = bbox_by_id.get(cid)
            bb_str = f"({bb[0]:.0f},{bb[1]:.0f},{bb[2]:.0f},{bb[3]:.0f})" if bb else "n/a"
            inventory_lines.append(f"    - {cid} bbox={bb_str}")

    return "\n".join(inventory_lines), citation_pool


def build_criteria_block(predicted_class: str) -> str:
    crit = WHO_ICC_CRITERIA.get(predicted_class, WHO_ICC_CRITERIA["UNCLASSIFIED"])
    morph = "\n".join(f"  - {m}" for m in crit["key_morphology"])
    workup = "\n".join(f"  - {w}" for w in crit["confirmatory_workup"])
    return (
        f"WHO/ICC reference for {predicted_class} ({crit['full_name']}):\n"
        f"Key morphology:\n{morph}\n"
        f"Confirmatory workup:\n{workup}"
    )


SYSTEM_PROMPT = """You are a board-certified hematopathologist writing a structured
peripheral blood smear report. You receive structured findings from an automated
multi-image cell-detection pipeline and a patient-level leukemia classification
hypothesis. Your job:

1. Write a CONCISE diagnostic report (max ~250 words) using markdown.
2. Lead with the impression, then the supporting findings, then the workup.
3. Every clinical claim that depends on specific cells MUST be followed by an
   inline citation marker like [C1], [C2], etc., where each marker corresponds
   to a finding key from the grounding inventory.
4. After the markdown report, emit a single JSON block tagged
   ```json-citations``` that maps each citation marker to the list of cell_ids
   supporting it. Use ONLY cell_ids from the inventory.
5. If the classification is flagged as low_confidence, state explicitly that
   pathologist review is required before issuing as a final diagnosis.
6. Do not invent findings absent from the inputs.
"""


def build_user_prompt(
    findings: AggregatedFindings,
    classification: LeukemiaClassification,
    detection_result: DetectionResult,
    clinical_context: str | None,
) -> tuple[str, dict[str, list[str]]]:
    inventory_text, citation_pool = build_grounding_inventory(
        findings, detection_result
    )
    parts = [
        f"=== PATIENT-LEVEL CLASSIFICATION ===",
        f"Predicted class: {classification.predicted_class}",
        f"Confidence: {classification.confidence:.2f}",
        f"Low-confidence flag: {classification.low_confidence}",
        f"Rule-based route: {classification.rule_based_route}",
        f"Routing rationale: {classification.routing_rationale}",
        "",
        "=== STRUCTURED FINDINGS ===",
        build_findings_summary(findings),
        "",
        "=== BLAST COHORT MORPHOLOGY ===",
        build_blast_morphology_summary(findings),
        "",
        "=== GROUNDING INVENTORY ===",
        inventory_text,
        "",
        "=== WHO/ICC REFERENCE ===",
        build_criteria_block(classification.predicted_class),
    ]
    if clinical_context:
        parts += ["", "=== CLINICIAN-PROVIDED CONTEXT ===", clinical_context]
    return "\n".join(parts), citation_pool


# ---------------------------------------------------------------------------
# Citation parsing — extracts the ```json-citations``` block from LLM output
# ---------------------------------------------------------------------------

CITATION_BLOCK_RE = re.compile(
    r"```json-citations\s*(\{.*?\})\s*```", re.DOTALL
)


def parse_citations(llm_text: str) -> tuple[str, dict[str, list[str]]]:
    """Strip the citation JSON block from the markdown body."""
    m = CITATION_BLOCK_RE.search(llm_text)
    if not m:
        return llm_text.strip(), {}
    try:
        citations = json.loads(m.group(1))
        # Coerce to dict[str, list[str]].
        citations = {k: list(v) for k, v in citations.items()}
    except (json.JSONDecodeError, TypeError, ValueError):
        citations = {}
    markdown = CITATION_BLOCK_RE.sub("", llm_text).strip()
    return markdown, citations


# ---------------------------------------------------------------------------
# Template fallback (no LLM)
# ---------------------------------------------------------------------------

class TemplateReportGenerator(BaseReportGenerator):
    """Deterministic, dependency-free report generator. Always works.

    Emits the canonical markdown format that `ReportConsistencyValidator`
    parses: a specimen line with exact phrasing, a piped differential table,
    a cohort morphology paragraph, an impression line, a differential
    considerations list, and a QC line.
    """

    # Cell-type display labels (singular JSON key → plural markdown label).
    _DISPLAY_LABEL = {
        "lymphoblast": "Lymphoblasts",
        "myeloblast": "Myeloblasts",
        "monoblast": "Monoblasts",
        "promonocyte": "Promonocytes",
        "abnormal promyelocyte": "Abnormal promyelocytes",
        "atypical lymphocyte": "Atypical lymphocytes",
        "lymphocyte": "Lymphocytes",
        "monocyte": "Monocytes",
        "neutrophil": "Neutrophils",
        "eosinophil": "Eosinophils",
        "basophil": "Basophils",
        "myelocyte": "Myelocytes",
        "metamyelocyte": "Metamyelocytes",
    }

    # Blast-like cell types for the cohort morphology block.
    _BLAST_TYPES = {
        "lymphoblast", "myeloblast", "monoblast",
        "promonocyte", "abnormal promyelocyte",
    }

    def generate(
        self,
        findings: AggregatedFindings,
        classification: LeukemiaClassification,
        detection_result: DetectionResult,
        clinical_context: str | None = None,
    ) -> GroundedReport:
        rr = findings.report_ready
        qc = rr["qc"]
        crit = WHO_ICC_CRITERIA.get(
            classification.predicted_class, WHO_ICC_CRITERIA["UNCLASSIFIED"]
        )

        # ----- Specimen line (exact phrasing parsed by the validator) ------
        n_images = qc["n_fields_of_view"]
        n_wbc = qc["n_identified_wbc"]
        n_total = qc["n_annotated_cells"]
        n_artefacts = qc["n_artifacts"]
        specimen_line = (
            f"**Specimen:** Peripheral blood smear, {n_images} fields of view, "
            f"{n_wbc} of {n_total} annotated objects classified as informative "
            f"WBCs ({n_artefacts} artefacts excluded)."
        )

        # ----- Differential table ------------------------------------------
        diff_rows = sorted(
            findings.cell_percentages_clinical.items(),
            key=lambda kv: kv[1],
            reverse=True,
        )
        diff_table = "| Cell type | % of informative WBCs |\n|---|---|\n"
        for cell_key, pct in diff_rows:
            label = self._DISPLAY_LABEL.get(
                cell_key.lower(), cell_key.capitalize()
            )
            diff_table += f"| {label} | {pct:.1f}% |\n"

        # ----- Cohort morphology paragraph ---------------------------------
        cohort_para = self._build_cohort_morphology(findings)

        # ----- Diagnostic flags line ---------------------------------------
        active_flags = [
            self._humanise_flag(k) for k, v in rr["diagnostic_flags"].items() if v
        ]
        flags_line = (
            "**Diagnostic flags:** " + "; ".join(active_flags) + "."
            if active_flags
            else "**Diagnostic flags:** none triggered."
        )

        # ----- Impression --------------------------------------------------
        # Use the canonical short form so it survives the alias matcher in
        # the consistency validator.
        impression_line = (
            f"**Impression:** {crit['full_name']} "
            f"({classification.predicted_class})."
        )

        # ----- Blast pool sentence -----------------------------------------
        # Phrased exactly so the validator's regex picks up the percentage.
        blast_sentence = self._build_blast_sentence(findings, classification)

        # ----- Differential considerations ---------------------------------
        differential_block = self._build_differential_considerations(
            classification.predicted_class
        )

        # ----- QC line (exact phrasing parsed by the validator) ------------
        artefact_pct = (
            round(n_artefacts / n_total * 100, 1) if n_total else 0.0
        )
        stitching = (
            "active" if qc.get("global_canvas_stitching_active") else "inactive"
        )
        qc_line = (
            f"**QC:** {n_images} FOVs; {n_wbc}/{n_total} cells classifiable "
            f"({artefact_pct:.1f}% artefact); cohort cell count = "
            f"{qc['n_cells_in_cohort']}; global canvas stitching {stitching}."
        )

        # ----- Assemble ----------------------------------------------------
        parts: list[str] = [
            f"# Hematology Report — Case {findings.case_id}",
            "",
            specimen_line,
            "",
            "**Differential (clinical denominator):**",
            "",
            diff_table.rstrip(),
        ]
        if cohort_para:
            parts += ["", cohort_para]
        parts += [
            "",
            flags_line,
            "",
            impression_line,
        ]
        if blast_sentence:
            parts += ["", blast_sentence]
        if differential_block:
            parts += ["", differential_block]
        if classification.low_confidence:
            parts += [
                "",
                "**⚠ Low-confidence classification — pathologist review required before issuing as a final diagnosis.**",
            ]
        parts += ["", qc_line, ""]
        markdown = "\n".join(parts)

        # ----- Citations from the grounding index --------------------------
        gi = findings.grounding_index
        c1 = gi.get("blast_cohort", []) or gi.get("flag::blast_threshold_met", [])
        c2 = gi.get(f"celltype::{rr['dominant_cell_type']}", [])
        citations = {k: v for k, v in (("C1", c1), ("C2", c2)) if v}

        return GroundedReport(
            case_id=findings.case_id,
            leukemia_class=classification.predicted_class,
            confidence=classification.confidence,
            markdown=markdown,
            citations=citations,
            flagged_for_review=classification.low_confidence,
            review_reasons=(
                ["low_confidence_classification"]
                if classification.low_confidence else []
            ),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_cohort_morphology(self, findings: AggregatedFindings) -> str:
        """Cohort morphology paragraph for the blast cohort, if present."""
        rr = findings.report_ready
        dominant = (rr.get("dominant_cell_type") or "").lower()
        if dominant not in self._BLAST_TYPES:
            return ""
        cohort_n = rr["qc"]["n_cells_in_cohort"]
        if not cohort_n:
            return ""

        morph = rr["blast_morphology"]

        def fmt(attr: str) -> str:
            v = morph.get(attr, {})
            d = v.get("dominant")
            pct = v.get("dominance_pct", 0.0)
            return f"{d} ({pct:.1f}%)" if d else "n/a"

        cohort_label = self._DISPLAY_LABEL.get(dominant, dominant).lower()
        return (
            f"**Cohort morphology (n = {cohort_n} {cohort_label}):** "
            f"predominantly {fmt('cell_size')} cells with "
            f"{fmt('cytoplasm')}, {fmt('cytoplasmic_basophilia')} "
            f"basophilic cytoplasm and {fmt('cytoplasmic_vacuoles')} "
            f"cytoplasmic vacuolation; nuclei show {fmt('nuclear_chromatio')} "
            f"chromatin, {fmt('nuclear_shape')} contours, and "
            f"{fmt('nucleolus')} nucleoli."
        )

    def _build_blast_sentence(
        self,
        findings: AggregatedFindings,
        classification: LeukemiaClassification,
    ) -> str:
        """The 'Xblasts comprise Y% of WBCs' line the validator parses."""
        rr = findings.report_ready
        dominant = (rr.get("dominant_cell_type") or "").lower()
        if dominant not in self._BLAST_TYPES:
            return ""
        pct = rr["blast_pool_percentage_of_wbc"]
        label = self._DISPLAY_LABEL.get(dominant, dominant.capitalize())
        if classification.predicted_class == "APML":
            return (
                f"{label} comprise {pct:.1f}% of WBCs with a blast-equivalent "
                f"burden meeting acute leukemia criteria."
            )
        return (
            f"{label} comprise {pct:.1f}% of WBCs, exceeding the 20% "
            f"blast threshold for acute leukemia."
        )

    def _build_differential_considerations(self, predicted_class: str) -> str:
        considerations = {
            "ALL": [
                "B-lymphoblastic leukemia/lymphoma (most common in adults and children).",
                "T-lymphoblastic leukemia/lymphoma.",
                "Mixed-phenotype acute leukemia (excluded by immunophenotyping).",
            ],
            "AML": [
                "AML with recurrent genetic abnormalities (per WHO/ICC).",
                "AML, not otherwise specified.",
                "Mixed-phenotype acute leukemia (excluded by immunophenotyping).",
            ],
            "APML": [
                "AML, not otherwise specified (less likely given promyelocyte morphology).",
            ],
            "CML": [
                "Leukemoid reaction (basophilia argues against this).",
                "Other MPN (PV, ET, primary myelofibrosis).",
                "Atypical CML, BCR::ABL1 negative.",
            ],
            "CLL": [
                "Mantle cell lymphoma in leukemic phase.",
                "Marginal zone lymphoma, leukemic.",
                "Prolymphocytic leukemia (>55% prolymphocytes).",
            ],
        }
        items = considerations.get(predicted_class)
        if not items:
            return ""
        return "**Differential considerations:**\n" + "\n".join(
            f"- {x}" for x in items
        )

    @staticmethod
    def _humanise_flag(flag_key: str) -> str:
        return flag_key.replace("_", " ")


# ---------------------------------------------------------------------------
# Claude (Anthropic) backend
# ---------------------------------------------------------------------------

class ClaudeReportGenerator(BaseReportGenerator):
    def __init__(
        self,
        model: str = "claude-opus-4-7",
        api_key: str | None = None,
        max_tokens: int = 1500,
    ):
        try:
            import anthropic  # type: ignore
        except ImportError as e:
            raise ImportError(
                "Install the anthropic SDK: `pip install anthropic`"
            ) from e
        self._anthropic = anthropic
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = model
        self.max_tokens = max_tokens

    def generate(
        self,
        findings: AggregatedFindings,
        classification: LeukemiaClassification,
        detection_result: DetectionResult,
        clinical_context: str | None = None,
    ) -> GroundedReport:
        user_prompt, _citation_pool = build_user_prompt(
            findings, classification, detection_result, clinical_context
        )

        resp = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        )
        markdown, citations = parse_citations(text)

        return GroundedReport(
            case_id=findings.case_id,
            leukemia_class=classification.predicted_class,
            confidence=classification.confidence,
            markdown=markdown,
            citations=citations,
            flagged_for_review=classification.low_confidence,
            review_reasons=(
                ["low_confidence_classification"] if classification.low_confidence else []
            ),
        )


# ---------------------------------------------------------------------------
# OpenAI backend
# ---------------------------------------------------------------------------

class OpenAIReportGenerator(BaseReportGenerator):
    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
        max_tokens: int = 1500,
    ):
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as e:
            raise ImportError("Install the openai SDK: `pip install openai`") from e
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        self.model = model
        self.max_tokens = max_tokens

    def generate(
        self,
        findings: AggregatedFindings,
        classification: LeukemiaClassification,
        detection_result: DetectionResult,
        clinical_context: str | None = None,
    ) -> GroundedReport:
        user_prompt, _citation_pool = build_user_prompt(
            findings, classification, detection_result, clinical_context
        )
        resp = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = resp.choices[0].message.content or ""
        markdown, citations = parse_citations(text)

        return GroundedReport(
            case_id=findings.case_id,
            leukemia_class=classification.predicted_class,
            confidence=classification.confidence,
            markdown=markdown,
            citations=citations,
            flagged_for_review=classification.low_confidence,
            review_reasons=(
                ["low_confidence_classification"] if classification.low_confidence else []
            ),
        )
