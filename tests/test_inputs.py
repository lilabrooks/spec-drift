"""Milestone 2 verification: repository discovery, diff loading, filtering, and
governing-document resolution.

Integration tests drive ``collect_changes`` against real git fixture
repositories covering every change kind and exclusion reason; focused unit
tests cover the error paths and the map parser/matcher. Everything is offline
and read-only.
"""

import shutil
from pathlib import Path

import pytest

from repo_fixtures import build_clean_fixture, build_mixed_fixture
from spec_drift.inputs import (
    ChangeStatus,
    ExclusionReason,
    InvalidBaseError,
    MappingError,
    RepositoryError,
    collect_changes,
    git,
)
from spec_drift.inputs.collect import _governing_docs
from spec_drift.inputs.filtering import classify_exclusion, partition
from spec_drift.inputs.mapping import Mapping, parse_mappings, resolve_governing_docs
from spec_drift.inputs.model import ChangedFile

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git is required")


# --- discovery and diff errors -------------------------------------------------


def test_outside_git_repository_raises(tmp_path: Path) -> None:
    with pytest.raises(RepositoryError):
        collect_changes(tmp_path, "base")


def test_invalid_base_reference_raises(tmp_path: Path) -> None:
    fixture = build_clean_fixture(tmp_path)
    with pytest.raises(InvalidBaseError):
        collect_changes(fixture.path, "no-such-ref")


def test_clean_branch_has_no_changes(tmp_path: Path) -> None:
    fixture = build_clean_fixture(tmp_path)
    changeset = collect_changes(fixture.path, "HEAD")  # nothing between HEAD and HEAD
    assert changeset.included == ()
    assert changeset.excluded == ()


def test_collect_runs_from_a_subdirectory(tmp_path: Path) -> None:
    fixture = build_clean_fixture(tmp_path)
    changeset = collect_changes(fixture.path / "src", fixture.base_ref)
    assert Path(changeset.root) == fixture.path
    assert [c.file.path for c in changeset.included] == ["src/refunds.py"]


# --- the full mixed change set -------------------------------------------------


@pytest.fixture(name="mixed")
def mixed_fixture(tmp_path: Path):  # type: ignore[no-untyped-def]
    fixture = build_mixed_fixture(tmp_path)
    return collect_changes(fixture.path, fixture.base_ref)


def _by_path(changeset, path):  # type: ignore[no-untyped-def]
    for change in changeset.included:
        if change.file.path == path:
            return change
    raise AssertionError(f"{path} not in included changes")


def test_change_statuses_are_classified(mixed) -> None:  # type: ignore[no-untyped-def]
    assert _by_path(mixed, "src/refunds.py").file.status is ChangeStatus.MODIFIED
    assert _by_path(mixed, "src/legacy.py").file.status is ChangeStatus.DELETED
    assert _by_path(mixed, "src/newfeature.py").file.status is ChangeStatus.ADDED
    renamed = _by_path(mixed, "src/newname.py").file
    assert renamed.status is ChangeStatus.RENAMED
    assert renamed.old_path == "src/oldname.py"


def test_governed_change_resolves_to_its_spec(mixed) -> None:  # type: ignore[no-untyped-def]
    refunds = _by_path(mixed, "src/refunds.py")
    assert refunds.governing_docs == ("docs/specs/refunds.md",)
    assert not refunds.is_unmapped


def test_change_without_a_governing_document_is_unmapped(mixed) -> None:  # type: ignore[no-untyped-def]
    feature = _by_path(mixed, "src/newfeature.py")
    assert feature.governing_docs == ()
    assert feature.is_unmapped
    assert "src/newfeature.py" in {c.file.path for c in mixed.unmapped}


def test_governed_and_unmapped_partition_the_included(mixed) -> None:  # type: ignore[no-untyped-def]
    assert {c.file.path for c in mixed.governed} == {"src/refunds.py"}
    assert {c.file.path for c in mixed.unmapped} == {
        "src/newname.py",
        "src/legacy.py",
        "src/newfeature.py",
    }


def test_env_credential_binary_and_ignored_are_excluded(mixed) -> None:  # type: ignore[no-untyped-def]
    reasons = {ex.path: ex.reason for ex in mixed.excluded}
    assert reasons[".env"] is ExclusionReason.ENV_FILE  # env wins over ignored
    assert reasons["deploy/server.pem"] is ExclusionReason.CREDENTIAL
    assert reasons["assets/logo.bin"] is ExclusionReason.BINARY
    assert reasons["build/generated.txt"] is ExclusionReason.IGNORED
    included_paths = {c.file.path for c in mixed.included}
    assert included_paths.isdisjoint(reasons)


# --- filtering units (paths git diff cannot emit) ------------------------------


def test_path_escaping_the_root_is_excluded() -> None:
    change = ChangedFile(path="../outside.py", status=ChangeStatus.MODIFIED)
    assert classify_exclusion(change) is ExclusionReason.OUTSIDE_ROOT


def test_absolute_path_is_excluded() -> None:
    change = ChangedFile(path="/etc/passwd", status=ChangeStatus.MODIFIED)
    assert classify_exclusion(change) is ExclusionReason.OUTSIDE_ROOT


@pytest.mark.parametrize(
    "path",
    ["deploy/id_rsa", "secrets/server.pem", "app/keystore.jks", ".netrc", "certs/client.p12"],
)
def test_credential_files_are_excluded(path: str) -> None:
    change = ChangedFile(path=path, status=ChangeStatus.ADDED)
    assert classify_exclusion(change) is ExclusionReason.CREDENTIAL


def test_env_wins_over_ignored_and_credential_over_outside_never_applies() -> None:
    env = ChangedFile(path=".env", status=ChangeStatus.MODIFIED)
    assert classify_exclusion(env, ignored={".env"}) is ExclusionReason.ENV_FILE


def test_ignored_and_binary_come_from_precomputed_sets() -> None:
    changes = [
        ChangedFile(path="src/app.py", status=ChangeStatus.MODIFIED),
        ChangedFile(path="src/gen.py", status=ChangeStatus.ADDED),
        ChangedFile(path="assets/pic.png", status=ChangeStatus.ADDED),
    ]
    kept, excluded = partition(changes, ignored={"src/gen.py"}, binary={"assets/pic.png"})
    assert [c.path for c in kept] == ["src/app.py"]
    reasons = {ex.path: ex.reason for ex in excluded}
    assert reasons == {
        "src/gen.py": ExclusionReason.IGNORED,
        "assets/pic.png": ExclusionReason.BINARY,
    }


def test_partition_keeps_ordinary_paths() -> None:
    changes = [ChangedFile(path="src/app.py", status=ChangeStatus.MODIFIED)]
    kept, excluded = partition(changes)
    assert [c.path for c in kept] == ["src/app.py"]
    assert excluded == []


# --- map parsing and glob matching ---------------------------------------------


def test_parse_mappings_reads_source_and_docs() -> None:
    text = (
        "layout:\n"
        "  specs_dir: docs/specs\n"
        "mappings:\n"
        '  - source: "src/app/**"\n'
        "    docs:\n"
        '      - "docs/specs/app.md"  # inline comment\n'
        '      - "docs/adr/0001-app.md"\n'
        '  - source: "schemas/*.json"\n'
        "    docs:\n"
        '      - "docs/specs/schema.md"\n'
    )
    mappings = parse_mappings(text)
    assert [m.source for m in mappings] == ["src/app/**", "schemas/*.json"]
    assert mappings[0].docs == ("docs/specs/app.md", "docs/adr/0001-app.md")


def test_recursive_glob_matches_across_directories() -> None:
    mappings = parse_mappings('mappings:\n  - source: "src/app/**"\n    docs:\n      - "d.md"\n')
    assert resolve_governing_docs("src/app/deep/module.py", mappings) == ("d.md",)
    assert resolve_governing_docs("src/other/module.py", mappings) == ()


def test_single_star_stays_within_a_segment() -> None:
    mappings = parse_mappings(
        'mappings:\n  - source: "schemas/*.json"\n    docs:\n      - "d.md"\n'
    )
    assert resolve_governing_docs("schemas/config.json", mappings) == ("d.md",)
    assert resolve_governing_docs("schemas/nested/config.json", mappings) == ()


def test_multiple_mappings_union_their_docs_in_order() -> None:
    text = (
        "mappings:\n"
        '  - source: "src/**"\n'
        "    docs:\n"
        '      - "docs/specs/a.md"\n'
        '  - source: "src/pay/**"\n'
        "    docs:\n"
        '      - "docs/specs/b.md"\n'
        '      - "docs/specs/a.md"\n'
    )
    mappings = parse_mappings(text)
    assert resolve_governing_docs("src/pay/refund.py", mappings) == (
        "docs/specs/a.md",
        "docs/specs/b.md",
    )


# --- malformed maps are rejected, valid-but-empty maps are not -----------------


def test_empty_or_comment_only_map_yields_no_mappings() -> None:
    assert parse_mappings("") == []
    assert parse_mappings("# just a comment\n") == []


def test_layout_or_mirrors_only_map_is_valid_and_empty() -> None:
    assert parse_mappings("layout:\n  specs_dir: docs/specs\n") == []
    assert parse_mappings("mirrors:\n  - .codex/hooks\n") == []


@pytest.mark.parametrize(
    "text",
    [
        'mappings:\n  - source: ""\n    docs:\n      - "d.md"\n',  # empty source
        'mappings:\n  - source: "src/**"\n',  # no docs for the entry
        '  - source: "src/**"\n    docs:\n      - "d.md"\n',  # fragment, no header
        "mappings:\n  # nothing here\n",  # header but empty
        "this is not a map at all\n",  # no top-level keys
        'mappings:\n  - source: "src/**"\n    docs:\n      - ""\n',  # empty doc path
        'mappings:\n  - source: "src/**"\n    junk line here\n',  # stray line in block
    ],
)
def test_malformed_map_raises(text: str) -> None:
    with pytest.raises(MappingError):
        parse_mappings(text)


def test_collect_raises_on_a_malformed_map(tmp_path: Path) -> None:
    fixture = build_clean_fixture(tmp_path)
    (fixture.path / "docs" / "okf-map.yml").write_text("mappings:\n  garbage\n", encoding="utf-8")
    with pytest.raises(MappingError):
        collect_changes(fixture.path, fixture.base_ref)


# --- rename handling (both ends resolve; the diff shows the rename) ------------


def test_rename_unions_old_and_new_path_governance() -> None:
    mappings = [Mapping(source="src/refunds.py", docs=("docs/specs/refunds.md",))]
    renamed_out = ChangedFile(
        path="src/legacy/refunds.py", status=ChangeStatus.RENAMED, old_path="src/refunds.py"
    )
    assert _governing_docs(renamed_out, mappings) == ("docs/specs/refunds.md",)
    modified = ChangedFile(path="src/other.py", status=ChangeStatus.MODIFIED)
    assert _governing_docs(modified, mappings) == ()


def test_rename_diff_reports_the_rename_not_a_wholesale_add(tmp_path: Path) -> None:
    fixture = build_mixed_fixture(tmp_path)
    root = Path(fixture.path)
    diff = git.load_file_diff(root, fixture.base_ref, "src/newname.py", "src/oldname.py")
    assert "rename from src/oldname.py" in diff
    assert "rename to src/newname.py" in diff
