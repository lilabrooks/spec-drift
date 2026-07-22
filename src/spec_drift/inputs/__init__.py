"""Analysis inputs: discover the repository, load the diff, filter unsafe paths,
and resolve governing documents — everything drift analysis consumes, produced
read-only and without any model call.
"""

from spec_drift.inputs.collect import collect_changes
from spec_drift.inputs.git import InvalidBaseError, RepositoryError
from spec_drift.inputs.mapping import MappingError
from spec_drift.inputs.model import (
    ChangedFile,
    ChangeSet,
    ChangeStatus,
    ExcludedFile,
    ExclusionReason,
    ResolvedChange,
)

__all__ = [
    "ChangeSet",
    "ChangeStatus",
    "ChangedFile",
    "ExcludedFile",
    "ExclusionReason",
    "InvalidBaseError",
    "MappingError",
    "RepositoryError",
    "ResolvedChange",
    "collect_changes",
]
