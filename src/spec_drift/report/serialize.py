"""Serialize an ``AnalysisReport`` to the plain dict the JSON report emits.

This dict is the machine-readable contract; ``schemas/report.schema.json``
describes it and a test validates output against that schema. Keeping the
serialization in one place means the terminal and Markdown renderers and the
JSON renderer all describe the same findings.
"""

from __future__ import annotations

from spec_drift.analysis.finding import AnalysisReport, Citation, Classification, Finding


def _citation_to_dict(citation: Citation | None) -> dict[str, object] | None:
    if citation is None:
        return None
    return {"path": citation.path, "line": citation.line}


def finding_to_dict(finding: Finding) -> dict[str, object]:
    return {
        "path": finding.path,
        "classification": finding.classification.value,
        "summary": finding.summary,
        "source": _citation_to_dict(finding.source),
        "document": _citation_to_dict(finding.document),
    }


def report_to_dict(report: AnalysisReport) -> dict[str, object]:
    counts = report.counts()
    return {
        "exit_code": report.exit_code(),
        "strict_coverage": report.strict_coverage,
        "summary": {
            classification.value: counts[classification] for classification in Classification
        },
        "findings": [finding_to_dict(finding) for finding in report.findings],
    }
