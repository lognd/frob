"""Git-tracked file listing helper shared by `pii_structural_gate`'s Python
scan and its TS/Rust cross-language scan (T-1076 split of
`frob.gates._pii_structural`, previously the module-level `_tracked_files_
by_pattern`/`_tracked_python_files` in the pre-split monolith)."""

from __future__ import annotations

from pathlib import Path

from frob.gitio import run_argv
from frob.logging import get_logger

_log = get_logger(__name__)


def _tracked_files_by_pattern(root: Path, pattern: str) -> tuple[str, ...]:
    """`git ls-files -- <pattern>` under `root`, root-relative POSIX paths,
    `()` on any git failure -- mirrors `frob.gates._secrets._tracked_
    files`'s degrade-don't-crash posture (module docstring: reuse, not a
    second copy of the same subprocess dance). Generalized (T-0352) so the
    same helper backs the Python (`*.py`), TypeScript (`*.ts`/`*.tsx`), and
    Rust (`*.rs`) file populations `pii_structural_gate` scans.

    Logs at WARNING (T-0705), not ERROR: a git-less target (no `.git`,
    or `git` itself unavailable) is a supported, silently-empty scan --
    the same posture `ref_gate`/`doc004` already use for the identical
    condition (docs/modules/gates.md#git-less-target-contract-t-0705)."""
    spawned = run_argv(("git", "-C", str(root), "ls-files", "--", pattern))
    if spawned.is_err:
        _log.warning("pii_structural_gate: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("pii_structural_gate: git ls-files exited %d", result.returncode)
        return ()
    return tuple(line for line in result.stdout.splitlines() if line.strip())


def _tracked_python_files(root: Path) -> tuple[str, ...]:
    """`git ls-files -- '*.py'` under `root` (`_tracked_files_by_pattern`)."""
    return _tracked_files_by_pattern(root, "*.py")
