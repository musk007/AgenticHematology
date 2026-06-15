"""Shared DinoBloom attribute classifier wiring for cv scripts."""
from __future__ import annotations

import sys
from pathlib import Path

CV_ROOT = Path(__file__).resolve().parent
REPO_ROOT = CV_ROOT.parent.parent
sys.path.insert(0, str(REPO_ROOT.parent))
sys.path.insert(0, str(REPO_ROOT))

from agentic_hematology.detection_agent_dinobloom import (  # noqa: E402
    DinoBloomAttributeClassifier,
    DinoBloomCellClassifier,
)

_ATTR_MLP_CANDIDATES = [
    CV_ROOT / "runs" / "attribute_dinobloom" / "train" / "best_attr_dinobloom.pt",
    REPO_ROOT / "runs" / "attribute_dinobloom" / "train" / "best_attr_dinobloom.pt",
]
_CELL_CLF_CANDIDATES = [
    CV_ROOT / "runs" / "cell_dinobloom" / "train" / "best_cell_dinobloom.pt",
    REPO_ROOT / "runs" / "cell_dinobloom" / "train" / "best_cell_dinobloom.pt",
]


def resolve_dinobloom_attr_weights(path: Path | str | None = None) -> Path:
    if path is not None:
        candidate = Path(path)
        if candidate.is_file():
            return candidate
    for candidate in _ATTR_MLP_CANDIDATES:
        if candidate.is_file():
            return candidate
    return _ATTR_MLP_CANDIDATES[0]


DEFAULT_DINOBLOOM_ATTR_WEIGHTS = resolve_dinobloom_attr_weights()


def resolve_dinobloom_cell_weights(path: Path | str | None = None) -> Path:
    if path is not None:
        candidate = Path(path)
        if candidate.is_file():
            return candidate
    for candidate in _CELL_CLF_CANDIDATES:
        if candidate.is_file():
            return candidate
    return _CELL_CLF_CANDIDATES[0]


DEFAULT_DINOBLOOM_CELL_WEIGHTS = resolve_dinobloom_cell_weights()


def _variant_from_cell_checkpoint(weights: Path) -> str | None:
    import torch

    ckpt = torch.load(weights, map_location="cpu", weights_only=False)
    if isinstance(ckpt, dict):
        variant = ckpt.get("dinobloom_variant")
        if variant in {"s", "b", "l", "g"}:
            return str(variant)
    return None


def build_dinobloom_cell_classifier(
    *,
    device: str | None = None,
    cell_weights: Path | str | None = None,
    attr_weights: Path | str | None = None,
    dinobloom_weights: str = "auto",
    variant: str = "l",
    hub_dir: str | None = None,
    fallback_to_yolo_type: bool = False,
) -> DinoBloomCellClassifier:
    """DinoBloom cell-type head + attribute MLP for precropped single-cell images."""
    cell_path = resolve_dinobloom_cell_weights(cell_weights)
    if not cell_path.is_file():
        raise FileNotFoundError(
            f"DinoBloom cell classifier not found: {cell_path}\n"
            "Train with: python wbc_unified/cv/train_dinobloom_cell_classifier.py"
        )
    attr_clf = build_dinobloom_attr_classifier(
        device=device,
        attr_weights=attr_weights,
        dinobloom_weights=dinobloom_weights,
        variant=_variant_from_cell_checkpoint(cell_path) or variant,
        hub_dir=hub_dir,
    )
    resolved_variant = _variant_from_cell_checkpoint(cell_path) or variant
    return DinoBloomCellClassifier(
        weights_path=dinobloom_weights,
        variant=resolved_variant,
        classifier_path=str(cell_path),
        device=device,
        hub_dir=hub_dir,
        attribute_classifier=attr_clf,
        fallback_to_yolo_type=fallback_to_yolo_type,
    )


def _variant_from_attr_checkpoint(weights: Path) -> str | None:
    import torch

    ckpt = torch.load(weights, map_location="cpu", weights_only=False)
    if isinstance(ckpt, dict):
        variant = ckpt.get("dinobloom_variant")
        if variant in {"s", "b", "l", "g"}:
            return str(variant)
    return None


def build_dinobloom_attr_classifier(
    *,
    device: str | None = None,
    attr_weights: Path | str | None = None,
    dinobloom_weights: str = "auto",
    variant: str = "l",
    hub_dir: str | None = None,
) -> DinoBloomAttributeClassifier:
    """Load frozen DinoBloom + trained MLP attribute head (``best_attr_dinobloom.pt``)."""
    weights = resolve_dinobloom_attr_weights(attr_weights)
    if not weights.is_file():
        raise FileNotFoundError(
            f"DinoBloom attribute MLP not found: {weights}\n"
            "Train with: python wbc_unified/cv/train_dinobloom_attributes_torch.py --dinobloom-variant l"
        )
    resolved_variant = _variant_from_attr_checkpoint(weights) or variant
    return DinoBloomAttributeClassifier(
        weights_path=dinobloom_weights,
        attr_probes_path=str(weights),
        variant=resolved_variant,
        attr_mode="probes",
        device=device,
        hub_dir=hub_dir,
    )
