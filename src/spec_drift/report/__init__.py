"""Report rendering: turn an ``AnalysisReport`` into terminal, Markdown, or JSON
output. Pure string rendering; the JSON form is the machine-readable contract in
``schemas/report.schema.json``.
"""

from spec_drift.report.render import (
    ReportFormat,
    render,
    render_json,
    render_markdown,
    render_terminal,
)
from spec_drift.report.serialize import finding_to_dict, report_to_dict

__all__ = [
    "ReportFormat",
    "finding_to_dict",
    "render",
    "render_json",
    "render_markdown",
    "render_terminal",
    "report_to_dict",
]
