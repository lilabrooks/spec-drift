"""Drift analysis: judge each governed change against its documents with a
model provider, producing validated findings (ADR 0001). Provider-neutral and
read-only; unmapped changes are recorded, never judged.
"""

from spec_drift.analysis.engine import analyze
from spec_drift.analysis.finding import (
    ACTIONABLE,
    JUDGED,
    AnalysisReport,
    Citation,
    Classification,
    Finding,
)

__all__ = [
    "ACTIONABLE",
    "JUDGED",
    "AnalysisReport",
    "Citation",
    "Classification",
    "Finding",
    "analyze",
]
