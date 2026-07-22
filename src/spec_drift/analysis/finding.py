"""The validated finding model produced by drift analysis.

Per ADR 0001, a finding is a closed classification plus paired, repo-relative
citations. Severity relevant to the process exit code lives on the report so
milestone 4 can render it without recomputing: ``drift``,
``decision-required`` and ``insufficient-evidence`` are actionable; ``unmapped``
is actionable only under strict coverage; ``clean`` never is.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from spec_drift.inputs.model import ExcludedFile


class Classification(Enum):
    CLEAN = "clean"
    DRIFT = "drift"
    DECISION_REQUIRED = "decision-required"
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"
    UNMAPPED = "unmapped"


# Classifications a model is allowed to assign. ``unmapped`` is engine-only.
JUDGED: frozenset[Classification] = frozenset(
    {
        Classification.CLEAN,
        Classification.DRIFT,
        Classification.DECISION_REQUIRED,
        Classification.INSUFFICIENT_EVIDENCE,
    }
)

# Classifications that always require review (exit code 1).
ACTIONABLE: frozenset[Classification] = frozenset(
    {
        Classification.DRIFT,
        Classification.DECISION_REQUIRED,
        Classification.INSUFFICIENT_EVIDENCE,
    }
)


@dataclass(frozen=True, slots=True)
class Citation:
    """A repository-relative reference, optionally to a specific line."""

    path: str
    line: int | None = None


@dataclass(frozen=True, slots=True)
class Finding:
    """One classified change with the evidence supporting it."""

    path: str
    classification: Classification
    summary: str
    source: Citation | None = None
    document: Citation | None = None


@dataclass(frozen=True, slots=True)
class AnalysisReport:
    """The findings for one analysis run and the coverage policy applied.

    ``excluded`` carries the paths the input layer kept out of analysis (env,
    credential, ignored, binary, outside-root) so the safety behavior is
    auditable in the report. Excluded paths never influence the exit code and
    the model never saw them — only the path and reason are surfaced.
    """

    findings: tuple[Finding, ...] = ()
    strict_coverage: bool = False
    excluded: tuple[ExcludedFile, ...] = ()

    def _requires_review(self, finding: Finding) -> bool:
        if finding.classification in ACTIONABLE:
            return True
        return finding.classification is Classification.UNMAPPED and self.strict_coverage

    @property
    def review_required(self) -> bool:
        """Whether any finding requires review under the active coverage policy."""
        return any(self._requires_review(finding) for finding in self.findings)

    def exit_code(self) -> int:
        """0 when nothing needs review, 1 when something does.

        Exit code 2 is reserved for input/repository/provider failures and is
        decided by the CLI, not here.
        """
        return 1 if self.review_required else 0

    def counts(self) -> dict[Classification, int]:
        """How many findings carry each classification."""
        tally: dict[Classification, int] = dict.fromkeys(Classification, 0)
        for finding in self.findings:
            tally[finding.classification] += 1
        return tally
