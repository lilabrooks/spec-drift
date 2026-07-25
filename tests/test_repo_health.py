"""Repository health invariants.

These tests guard repo-level consistency rather than package behavior: the
declared version must agree everywhere it appears, tracked files must not
match .gitignore, the scanner manifest must mirror the optional dependencies,
and any second-agent config mirror must stay in parity with the Claude stack.
"""

import filecmp
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

import spec_drift

REPO_ROOT = Path(__file__).resolve().parent.parent

ARTIFACT_VERSION = re.compile(r"spec_drift-(\d+\.\d+\.\d+)")
TAG_VERSION = re.compile(r"@v(\d+\.\d+\.\d+)")
PINNED_REQUIREMENT = re.compile(r"^[A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?==")


def declared_version() -> str:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = data["project"]["version"]
    assert isinstance(version, str)
    return version


def project_metadata() -> dict[str, object]:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    assert isinstance(project, dict)
    return project


def scanner_requirements() -> list[str]:
    return [
        line.strip()
        for line in (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def test_package_version_matches_pyproject() -> None:
    assert spec_drift.__version__ == declared_version()


def test_changelog_latest_entry_matches_pyproject() -> None:
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(r"^## \[?(\d+\.\d+\.\d+)\]?", changelog, flags=re.MULTILINE)
    assert match is not None, "CHANGELOG.md has no '## [x.y.z]' release heading"
    assert match.group(1) == declared_version(), (
        f"CHANGELOG.md latest entry is {match.group(1)}, pyproject.toml says {declared_version()}"
    )


def test_docs_reference_current_version() -> None:
    version = declared_version()
    docs = [REPO_ROOT / "README.md", *sorted((REPO_ROOT / "docs").rglob("*.md"))]
    stale: list[str] = []
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        for pattern in (ARTIFACT_VERSION, TAG_VERSION):
            stale.extend(
                f"{doc.relative_to(REPO_ROOT)}: {found}"
                for found in pattern.findall(text)
                if found != version
            )
    assert not stale, f"stale version references (expected {version}): {stale}"


def test_doc_frontmatter_version_matches_pyproject() -> None:
    version = declared_version()
    frontmatter_version = re.compile(r"^version:\s*(\S+)\s*$", flags=re.MULTILINE)
    stale: list[str] = []
    for doc in sorted((REPO_ROOT / "docs").rglob("*.md")):
        text = doc.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        frontmatter = text.split("\n---", maxsplit=1)[0]
        stale.extend(
            f"{doc.relative_to(REPO_ROOT)}: {found}"
            for found in frontmatter_version.findall(frontmatter)
            if found != version
        )
    assert not stale, f"stale frontmatter versions (expected {version}): {stale}"


def test_scanner_requirements_mirror_optional_dependencies() -> None:
    optional_dependencies = project_metadata()["optional-dependencies"]
    assert isinstance(optional_dependencies, dict)
    expected = sorted(
        dependency for dependencies in optional_dependencies.values() for dependency in dependencies
    )
    actual = sorted(scanner_requirements())
    missing = sorted(set(expected) - set(actual))
    assert not missing, f"requirements.txt is missing optional dependencies: {missing}"


def test_scanner_requirements_avoid_exact_pins() -> None:
    pinned = [line for line in scanner_requirements() if PINNED_REQUIREMENT.match(line)]
    assert not pinned, f"requirements.txt should use lower bounds, not exact pins: {pinned}"


def test_formatter_does_not_reach_into_markdown() -> None:
    """The formatter stays on Python, so it cannot rewrite captured evidence.

    ruff 0.16.0 began discovering Markdown and reformatting the Python inside
    fenced blocks. The docs bundle is governed knowledge and some of it is
    captured verbatim from live runs, so a formatter that rewrites it would
    silently falsify it. This pins the exclusion against a future ruff bump
    re-widening the scope without anyone noticing.

    This asserts the *configured* scope, not that ruff honors it; the probe
    below exercises the real binary.
    """
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    excluded = data["tool"]["ruff"]["format"]["exclude"]
    assert "*.md" in excluded, f"ruff format no longer excludes Markdown: {excluded}"


def test_formatter_ignores_an_unformatted_markdown_block(tmp_path: Path) -> None:
    """The real ruff binary leaves a badly formatted Markdown block alone.

    Guards the behavior rather than the setting: a deliberately unformatted
    Python block inside Markdown must not fail `ruff format --check`.
    """
    ruff = REPO_ROOT / ".venv" / "bin" / "ruff"
    if not ruff.is_file():  # pragma: no cover - depends on local env layout
        pytest.skip("ruff is not installed in the project virtualenv")

    probe = tmp_path / "probe.md"
    probe.write_text("```python\nx   =    1\ndef  f( a ):\n  return   a\n```\n", encoding="utf-8")
    result = subprocess.run(
        # --config keeps the probe outside the repo while still exercising this
        # project's settings; naming the path explicitly is what force-exclude
        # has to defeat.
        [str(ruff), "format", "--check", "--config", str(REPO_ROOT / "pyproject.toml"), str(probe)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, (
        f"ruff format reached into Markdown: {result.stdout}{result.stderr}"
    )


def test_no_tracked_files_match_gitignore() -> None:
    """No committed file should match a .gitignore pattern.

    Guards against build/test artifacts (e.g. the .coverage database) being
    re-committed after they've been ignored. Skipped when run outside a git
    checkout, such as against an installed wheel.
    """
    if shutil.which("git") is None or not (REPO_ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    result = subprocess.run(
        ["git", "ls-files", "-i", "-c", "--exclude-standard"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    tracked_but_ignored = result.stdout.split()
    assert not tracked_but_ignored, (
        f"tracked files match .gitignore (untrack with 'git rm --cached'): {tracked_but_ignored}"
    )


def test_gitignore_covers_local_artifacts_without_hiding_project_files() -> None:
    if shutil.which("git") is None or not (REPO_ROOT / ".git").exists():
        pytest.skip("not a git checkout")

    def is_ignored(path: str) -> bool:
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "--quiet", path],
            cwd=REPO_ROOT,
            check=False,
        )
        return result.returncode == 0

    ignored = [
        ".venv",
        ".venv.nosync/bin/python",
        "src/example/__pycache__/module.pyc",
        "dist/package.whl",
        "build/package/file.py",
        ".coverage.worker",
        "htmlcov/index.html",
        "coverage.xml",
        ".env.local",
        ".codex-log/session.jsonl",
    ]
    trackable = [
        "uv.lock",
        ".python-version",
        ".env.example",
        "AGENTS.md",
        "AGENTS.override.md",
        ".codex/config.toml",
        ".codex/hooks/pre-tool.sh",
        ".codex/settings.local.json",
        "Codex.local.md",
        "src/dist/__init__.py",
        "src/build/__init__.py",
    ]

    missing_ignores = [path for path in ignored if not is_ignored(path)]
    unexpectedly_ignored = [path for path in trackable if is_ignored(path)]
    assert not missing_ignores, f"local artifacts are not ignored: {missing_ignores}"
    assert not unexpectedly_ignored, (
        f"project files that should remain trackable are ignored: {unexpectedly_ignored}"
    )


def test_codex_hooks_match_claude_hooks() -> None:
    """The Codex hook mirror must contain every Claude hook byte-for-byte.

    The Codex stack is optional: when `.codex/hooks/` is absent the check
    no-ops, keeping a Claude-only checkout green. Once the mirror exists, a
    missing, extra, or changed hook is an error.
    """
    claude_hooks = REPO_ROOT / ".claude" / "hooks"
    codex_hooks = REPO_ROOT / ".codex" / "hooks"
    if not codex_hooks.is_dir():
        pytest.skip("no Codex hook mirror in this repo")

    assert claude_hooks.is_dir(), ".codex/hooks exists without the source .claude/hooks directory"
    claude_names = {path.name for path in claude_hooks.glob("*.sh") if path.is_file()}
    codex_names = {path.name for path in codex_hooks.glob("*.sh") if path.is_file()}
    assert claude_names == codex_names, (
        "hook sets are not paired across the two agent stacks "
        f"(only in .claude: {sorted(claude_names - codex_names)}; "
        f"only in .codex: {sorted(codex_names - claude_names)})"
    )

    mismatched: list[str] = []
    for name in sorted(claude_names):
        if not filecmp.cmp(claude_hooks / name, codex_hooks / name, shallow=False):
            mismatched.append(name)
    assert not mismatched, (
        "Codex hooks have drifted from the Claude source of truth "
        f"(re-sync from .claude/hooks/): {mismatched}"
    )


def test_codex_skills_pair_with_claude_skills() -> None:
    """Every `okf-*` skill must exist in both agent stacks when both are present.

    Skill contents are deliberately adapted per agent, so only the *set* of
    skills is compared. The Codex stack is optional: when `.agents/skills/` is
    absent the check no-ops.
    """
    claude_skills = REPO_ROOT / ".claude" / "skills"
    codex_skills = REPO_ROOT / ".agents" / "skills"
    if not codex_skills.is_dir():
        pytest.skip("no Codex skill mirror in this repo")
    assert claude_skills.is_dir(), (
        ".agents/skills exists without the source .claude/skills directory"
    )
    claude_names = {p.name for p in claude_skills.glob("okf-*") if p.is_dir()}
    codex_names = {p.name for p in codex_skills.glob("okf-*") if p.is_dir()}
    assert claude_names == codex_names, (
        "okf-* skills are not paired across the two agent stacks "
        f"(only in .claude: {sorted(claude_names - codex_names)}; "
        f"only in .agents: {sorted(codex_names - claude_names)})"
    )
