"""Scan/remove logic for `frob.clean` (T-0457, docs/modules/clean.md).

`scan` is always read-only; `clean(..., dry_run=False)` is the ONLY path
that mutates the tree, and it never removes anything `scan` did not already
report as a matched, non-tracked artifact -- the fail-safe is structural,
not a bolt-on check.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from typani import Err, Ok
from typani.result import Result

from frob.clean._models import ArtifactEntry, CleanError, CleanReport, CleanTier
from frob.clean._rules import extra_patterns_from_config, tier_patterns
from frob.gitio import repo_root, run_argv
from frob.logging import get_logger

_log = get_logger(__name__)

# Directories `**`-patterns never descend into: version-control internals,
# the virtualenv, and JS dependency trees are never "this project's"
# artifacts even though a `**/__pycache__`-style pattern would otherwise
# happily match inside them.
_EXCLUDED_ANCESTORS = frozenset({".git", ".venv", "node_modules"})


def _tracked_paths(root: Path) -> frozenset[Path]:
    """Every git-tracked file's absolute path under `root`; empty (never an
    error) if `git ls-files` fails -- the allowlist-only match in `scan`
    already keeps removal scoped to known artifacts regardless."""
    spawned = run_argv(("git", "-C", str(root), "ls-files"), cwd=root)
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.warning("clean: git ls-files failed, treating tracked set as empty")
        return frozenset()
    return frozenset(
        (root / line).resolve()
        for line in spawned.danger_ok.stdout.splitlines()
        if line
    )


def _dir_size(path: Path) -> int:
    """Recursive byte size of a directory, best-effort (unreadable entries
    contribute 0 rather than raising)."""
    total = 0
    # frob:waive WALK001 reason="sizes one already-matched artifact dir; excludes would prune the dirs this module exists to find"  # noqa: E501
    try:
        for p in path.rglob("*"):
            if p.is_file() and not p.is_symlink():
                try:
                    total += p.stat().st_size
                except OSError:
                    continue
    except OSError:
        return total
    except Exception as exc:  # noqa: BLE001 -- best-effort size, never fatal
        _log.debug("_dir_size: %s failed: %s", path, exc)
        return total
    return total


def _match_candidates(root: Path, patterns: tuple[str, ...]) -> dict[Path, str]:
    """Every path under `root` matching any allowlist pattern, deduplicated and
    pruned so a match nested inside another matched directory is reported
    once (via its outermost matching ancestor), not twice."""
    candidates: dict[Path, str] = {}
    root_resolved = root.resolve()
    for pattern in patterns:
        # frob:waive WALK001 reason="allowlist patterns deliberately target __pycache__/build/dist/etc, the exact dirs frob.excludes prunes; that's this module's whole job"  # noqa: E501
        for match in root.glob(pattern):
            if _EXCLUDED_ANCESTORS.intersection(match.parts):
                continue
            resolved = match.resolve()
            if resolved == root_resolved:
                continue
            candidates.setdefault(resolved, pattern)

    matched_dirs = sorted(
        (p for p in candidates if p.is_dir()), key=lambda p: len(p.parts)
    )
    pruned: dict[Path, str] = {}
    for path, rule in candidates.items():
        if any(path != d and path.is_relative_to(d) for d in matched_dirs):
            continue
        pruned[path] = rule
    return pruned


# frob:doc docs/modules/clean.md#public-api
# frob:tests tests/test_clean.py::test_scan_tier1_matches_expected
# frob:tests tests/test_clean.py::test_scan_skips_tracked_files
# frob:invariant INV-008
# invariant spec: [INV-008](invariants/INV-008.md)
def scan(
    root: Path, tier: CleanTier, *, extra_patterns: tuple[str, ...] = ()
) -> Result[CleanReport, CleanError]:
    """Every artifact `tier` would remove, WITHOUT removing anything -- always
    a dry-run report. `clean(..., dry_run=False)` is the only mutating path."""
    root_result = repo_root(root)
    if root_result.is_err:
        return Err(CleanError.NotARepo)
    real_root = root_result.danger_ok

    patterns = (
        tier_patterns(tier) + extra_patterns_from_config(real_root) + extra_patterns
    )
    candidates = _match_candidates(real_root, patterns)
    tracked = _tracked_paths(real_root)

    entries: list[ArtifactEntry] = []
    skipped: list[Path] = []
    for path, rule in sorted(candidates.items()):
        if path in tracked:
            skipped.append(path)
            _log.warning(
                "clean: %s matched %r but is git-tracked, skipping", path, rule
            )
            continue
        is_dir = path.is_dir()
        if is_dir:
            size = _dir_size(path)
        else:
            size = path.stat().st_size if path.exists() else 0
        entries.append(
            ArtifactEntry(
                path=path, tier=tier, rule=rule, size_bytes=size, is_dir=is_dir
            )
        )

    return Ok(
        CleanReport(tier=tier, dry_run=True, entries=entries, skipped_tracked=skipped)
    )


# frob:doc docs/modules/clean.md#public-api
# frob:tests tests/test_clean.py::test_clean_dry_run_removes_nothing
# frob:tests tests/test_clean.py::test_clean_execute_removes_matched
# frob:tests tests/test_clean.py::test_clean_never_touches_src
def clean(
    root: Path,
    tier: CleanTier,
    *,
    dry_run: bool = True,
    extra_patterns: tuple[str, ...] = (),
) -> Result[CleanReport, CleanError]:
    """`scan` for `tier`'s artifacts and, only when `dry_run` is False, remove
    exactly the entries `scan` reported -- never a broader set."""
    scanned = scan(root, tier, extra_patterns=extra_patterns)
    if scanned.is_err:
        return scanned
    report = scanned.danger_ok
    if dry_run:
        return Ok(report)

    for entry in report.entries:
        try:
            if entry.is_dir:
                shutil.rmtree(entry.path)
            else:
                entry.path.unlink(missing_ok=True)
            _log.info(
                "clean: removed %s (%d bytes, rule=%r)",
                entry.path,
                entry.size_bytes,
                entry.rule,
            )
        except OSError as exc:
            _log.error("clean: failed to remove %s: %s", entry.path, exc)
            return Err(CleanError.RemoveFailed)

    return Ok(report.model_copy(update={"dry_run": False}))
