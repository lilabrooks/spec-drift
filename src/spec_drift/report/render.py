"""Render an ``AnalysisReport`` to terminal text, Markdown, or JSON.

All three describe the same findings; JSON is the machine-readable form
validated against ``schemas/report.schema.json``. Rendering is pure — it
returns a string and performs no I/O — so the CLI decides where output goes.
"""

from __future__ import annotations

import json
from enum import Enum

from spec_drift.analysis.finding import AnalysisReport, Citation, Classification, Finding
from spec_drift.report.serialize import report_to_dict

_EMPTY = "No governed or unmapped changes found."


class ReportFormat(Enum):
    TERMINAL = "terminal"
    MARKDOWN = "markdown"
    JSON = "json"


def _citation_str(citation: Citation | None) -> str:
    if citation is None:
        return "-"
    return f"{citation.path}:{citation.line}" if citation.line is not None else citation.path


def _summary_line(report: AnalysisReport) -> str:
    counts = report.counts()
    parts = [
        f"{counts[classification]} {classification.value}"
        for classification in Classification
        if counts[classification]
    ]
    tally = ", ".join(parts) if parts else "nothing to report"
    return f"{tally} (exit {report.exit_code()})"


def _terminal_citations(finding: Finding) -> str:
    parts = []
    if finding.source is not None:
        parts.append(f"source {_citation_str(finding.source)}")
    if finding.document is not None:
        parts.append(f"doc {_citation_str(finding.document)}")
    return f"  [{'; '.join(parts)}]" if parts else ""


def render_terminal(report: AnalysisReport) -> str:
    if not report.findings:
        return _EMPTY
    width = max(len(finding.classification.value) for finding in report.findings)
    lines = [
        f"{finding.classification.value:<{width}}  {finding.path}  "
        f"{finding.summary}{_terminal_citations(finding)}"
        for finding in report.findings
    ]
    lines.append("")
    lines.append(_summary_line(report))
    return "\n".join(lines)


def _markdown_row(finding: Finding) -> str:
    return (
        f"| {finding.path} | {finding.classification.value} | "
        f"{_citation_str(finding.source)} | {_citation_str(finding.document)} | "
        f"{finding.summary} |"
    )


def render_markdown(report: AnalysisReport) -> str:
    if not report.findings:
        return f"# spec-drift report\n\n{_EMPTY}\n"
    header = (
        "# spec-drift report\n\n"
        "| File | Classification | Source | Document | Summary |\n"
        "| --- | --- | --- | --- | --- |\n"
    )
    rows = "\n".join(_markdown_row(finding) for finding in report.findings)
    return f"{header}{rows}\n\n_{_summary_line(report)}_\n"


def render_json(report: AnalysisReport) -> str:
    return json.dumps(report_to_dict(report), indent=2, sort_keys=True)


def render(report: AnalysisReport, report_format: ReportFormat) -> str:
    if report_format is ReportFormat.JSON:
        return render_json(report)
    if report_format is ReportFormat.MARKDOWN:
        return render_markdown(report)
    return render_terminal(report)
