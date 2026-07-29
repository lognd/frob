"""frob.clean: tiered, artifact-only workspace cleanup (T-0457)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.clean import CleanTier, clean, extra_patterns_from_config, scan, tier_patterns
from frob.clean._models import CleanReport


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A minimal git repo with a tracked source tree plus tier 1/2/3 artifact
    fixtures and one untracked-but-not-an-artifact "real work" file."""
    root = tmp_path / "proj"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")

    (root / "src").mkdir()
    (root / "src" / "mod.py").write_text("x = 1\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")

    # tier 1 artifacts
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "mod.cpython-311.pyc").write_bytes(b"\x00" * 10)
    (root / ".coverage.host.12345.abcd").write_text("frag")
    (root / ".pytest_cache").mkdir()
    (root / ".pytest_cache" / "v" / "cache").mkdir(parents=True)
    (root / ".pytest_cache" / "v" / "cache" / "lastfailed").write_text("{}")

    # tier 2 artifacts
    (root / "build").mkdir()
    (root / "build" / "out.txt").write_text("built")
    (root / "coverage.xml").write_text("<coverage/>")
    (root / ".coverage").write_text("combined")

    # tier 3 artifacts
    (root / ".frob").mkdir()
    (root / ".frob" / "cache.db").write_text("{}")
    (root / "FROBLEMS.md").write_text("# problems\n")

    # a real untracked source file that must NEVER be removed
    (root / "src" / "wip.py").write_text("# work in progress\n")

    return root


# frob:tests tests/test_clean.py::test_tier_patterns_cumulative
def test_tier_patterns_cumulative() -> None:
    """`tier_patterns` is strictly cumulative: SAFE subset of ALL subset of DEEP."""
    safe = set(tier_patterns(CleanTier.SAFE))
    full = set(tier_patterns(CleanTier.ALL))
    deep = set(tier_patterns(CleanTier.DEEP))
    assert safe <= full <= deep
    assert deep - full  # tier 3 adds at least one new pattern
    assert full - safe  # tier 2 adds at least one new pattern


# frob:tests tests/test_clean.py::test_extra_patterns_missing_toml
def test_extra_patterns_missing_toml(tmp_path: Path) -> None:
    """No `frob.toml` at all degrades to no extra patterns, never an error."""
    assert extra_patterns_from_config(tmp_path) == ()


# frob:tests tests/test_clean.py::test_extra_patterns_from_config
def test_extra_patterns_from_config(tmp_path: Path) -> None:
    """`[clean].extra_patterns` in `frob.toml` is read verbatim."""
    (tmp_path / "frob.toml").write_text('[clean]\nextra_patterns = ["*.tmp"]\n')
    assert extra_patterns_from_config(tmp_path) == ("*.tmp",)


# frob:tests tests/test_clean.py::test_scan_tier1_matches_expected
def test_scan_tier1_matches_expected(repo: Path) -> None:
    """Tier 1 matches exactly the pycache/coverage-fragment/pytest-cache set,
    never the tier 2/3 fixtures or the real source."""
    report = scan(repo, CleanTier.SAFE).danger_ok
    matched = {p.name for p in (e.path for e in report.entries)}
    assert "__pycache__" in matched
    assert ".coverage.host.12345.abcd" in matched
    assert ".pytest_cache" in matched
    assert "build" not in matched
    assert ".frob" not in matched
    assert report.dry_run is True


# frob:tests tests/test_clean.py::test_scan_skips_tracked_files
# invariant spec: [INV-008](invariants/INV-008.md)
def test_scan_skips_tracked_files(repo: Path) -> None:
    """A file that matches an allowlist pattern but is git-tracked is skipped,
    never reported as a removal candidate."""
    (repo / "coverage.xml").write_text("<coverage/>")
    _git(repo, "add", "-f", "coverage.xml")
    _git(repo, "commit", "-q", "-m", "oops, tracked an artifact")

    report = scan(repo, CleanTier.ALL).danger_ok
    matched_names = {e.path.name for e in report.entries}
    assert "coverage.xml" not in matched_names
    assert any(p.name == "coverage.xml" for p in report.skipped_tracked)


# frob:tests tests/test_clean.py::test_clean_dry_run_removes_nothing
def test_clean_dry_run_removes_nothing(repo: Path) -> None:
    """The default (`dry_run=True`) never mutates the tree."""
    before = sorted(p.relative_to(repo) for p in repo.rglob("*"))
    report = clean(repo, CleanTier.DEEP).danger_ok
    after = sorted(p.relative_to(repo) for p in repo.rglob("*"))
    assert before == after
    assert report.dry_run is True
    assert report.count > 0


# frob:tests tests/test_clean.py::test_clean_execute_removes_matched
def test_clean_execute_removes_matched(repo: Path) -> None:
    """`dry_run=False` removes every tier-1 match and nothing else."""
    report = clean(repo, CleanTier.SAFE, dry_run=False).danger_ok
    assert report.dry_run is False
    assert not (repo / "__pycache__").exists()
    assert not (repo / ".coverage.host.12345.abcd").exists()
    assert not (repo / ".pytest_cache").exists()
    # tier 2/3 fixtures untouched by a tier-1 run
    assert (repo / "build").exists()
    assert (repo / ".frob").exists()
    assert (repo / "FROBLEMS.md").exists()


# frob:tests tests/test_clean.py::test_clean_never_touches_src
# frob:tests src/frob/clean kind="integration"
def test_clean_never_touches_src(repo: Path) -> None:
    """Every tier leaves `git diff --stat` over the tracked tree empty, and the
    untracked-but-not-an-artifact `src/wip.py` survives even a DEEP clean."""
    for tier in (CleanTier.SAFE, CleanTier.ALL, CleanTier.DEEP):
        result = clean(repo, tier, dry_run=False)
        assert result.is_ok, result.danger_err

    diff = subprocess.run(
        ["git", "diff", "--stat", "--", "src/"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert diff.stdout.strip() == ""
    assert (repo / "src" / "wip.py").exists()


# frob:tests tests/test_clean.py::test_clean_deep_removes_frob_state
def test_clean_deep_removes_frob_state(repo: Path) -> None:
    """`--deep` (tier 3) removes `.frob/` and `FROBLEMS.md` in addition to
    tiers 1 and 2."""
    report = clean(repo, CleanTier.DEEP, dry_run=False).danger_ok
    assert report.dry_run is False
    assert not (repo / ".frob").exists()
    assert not (repo / "FROBLEMS.md").exists()
    assert not (repo / "build").exists()
    assert not (repo / "coverage.xml").exists()


# frob:tests tests/test_clean.py::test_reclaimed_bytes_sums_matched_entries
def test_reclaimed_bytes_sums_matched_entries(repo: Path) -> None:
    """`CleanReport.reclaimed_bytes` sums exactly the matched entries' sizes,
    not the skipped-tracked ones -- proves the non-empty summation branch."""
    # frob:tests src/frob/clean/_models.py::CleanReport.reclaimed_bytes kind="unit"
    report = scan(repo, CleanTier.SAFE).danger_ok
    assert report.reclaimed_bytes == sum(e.size_bytes for e in report.entries)
    assert report.reclaimed_bytes > 0


def test_reclaimed_bytes_is_zero_for_no_matches(tmp_path: Path) -> None:
    """An empty `entries` list sums to `0`, not a crash -- proves
    `reclaimed_bytes`'s zero-entries branch."""
    report = CleanReport(tier=CleanTier.SAFE, dry_run=True, entries=[])
    assert report.reclaimed_bytes == 0
