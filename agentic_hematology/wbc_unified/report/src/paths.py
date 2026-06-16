"""Project layout: wbc_unified/{cv,report,verl_scripts,config,pipeline}."""
from __future__ import annotations

from pathlib import Path

REPORT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = REPORT_ROOT.parent
REPO_ROOT = PROJECT_ROOT.parent
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "default.yaml"
CV_ROOT = PROJECT_ROOT / "cv"
