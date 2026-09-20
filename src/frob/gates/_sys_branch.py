"""frob.gates._sys_branch -- SYS900 explicit worktree/branch SYS audit
entry point (T-4212).

Split out of `frob.gates._sys` (same one-family-per-land discipline
`_sys_selfaudit.py` established, T-1420 LARGE001 burndown) so `_sys.py`
stays under the large-file threshold. `sys_gate_for_branch` is the only
name this module is externally imported by; `_sys900_unmeasured` and
`_resolve_ref_worktree` stay private to it.

Consolidates F-317/M-1 and its addendum F-039-b/T-0297: `frob.gates._sys
.sys_gate` only ever evaluates whatever root a caller's own
`GraphSnapshot` was built from -- historically always the primary
checkout's current branch, `main` -- so code that exists only on a
parked/feature branch is structurally invisible to every SYS/capability
gate; a capability grant added or removed there passes with zero signal
either way. `sys_gate_for_branch` resolves an explicit branch (or
worktree directory) name to its checked-out worktree and evaluates
`sys_gate` against a fresh `GraphSnapshot` scoped to it, reporting SYS900
`Severity.UNRESOLVED` -- UNMEASURED, never an empty tuple standing in for
clean -- when that resolution or the snapshot build itself fails."""
# frob:ticket T-4212

from __future__ import annotations

import tempfile
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gates._sys import sys_gate
from frob.gitio import run_argv
from frob.logging import get_logger

_log = get_logger(__name__)


def _sys900_unmeasured(ref: str, reason: str) -> Violation:
    """SYS900, `Severity.UNRESOLVED` -- an explicit worktree/branch SYS
    audit (`sys_gate_for_branch`) could not be run for `ref` at all (no
    checked-out worktree found, or its `GraphSnapshot` build failed).
    Reported instead of an empty violation tuple, so a caller that cannot
    reach `ref` at all is never indistinguishable from one that scanned
    it and found nothing; see docs/modules/gates.md#self-audit-at-land-
    selfaudit001-t-0756."""
    _log.warning("sys_gate_for_branch: %s is UNMEASURED -- %s", ref, reason)
    return Violation(
        rule="SYS900",
        severity=Severity.UNRESOLVED,
        file=ref,
        line=1,
        message=(f"SYS900: SYS audit for {ref!r} is UNMEASURED, not clean -- {reason}"),
    )


def _resolve_ref_worktree(repo_root: Path, ref: str) -> Path | None:
    """The filesystem root of a git worktree of `repo_root` already
    checked out to `ref` -- a literal worktree path (if `ref` resolves to
    an existing directory under `repo_root`'s `git worktree list`), else
    the first worktree whose `branch refs/heads/<ref>` line matches `ref`
    by name. Parses `git worktree list --porcelain`'s stable
    blank-line-separated record format, same convention `frob.tickets.
    _worktree_sweep._list_agent_worktrees` uses. Returns `None` if the
    `git` call fails or no worktree matches -- the caller reports SYS900
    UNMEASURED rather than treating that as zero findings."""
    spawned = run_argv(("git", "-C", str(repo_root), "worktree", "list", "--porcelain"))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.warning(
            "sys_gate_for_branch: git worktree list --porcelain failed under %s",
            repo_root,
        )
        return None
    branch_ref = f"refs/heads/{ref}"
    current_path: Path | None = None
    for block in spawned.danger_ok.stdout.split("\n\n"):
        for line in block.splitlines():
            if line.startswith("worktree "):
                current_path = Path(line[len("worktree ") :])
            elif line.startswith("branch ") and current_path is not None:
                if line[len("branch ") :] == branch_ref:
                    return current_path
    direct = (repo_root / ref).resolve()
    if direct.is_dir():
        return direct
    return None


# frob:doc docs/modules/gates.md#self-audit-at-land-selfaudit001-t-0756
# frob:tests tests/gates_suite/test_sys.py::TestSysGateForBranch.test_finds_findings_only_visible_on_branch  # noqa: E501
# frob:tests tests/gates_suite/test_sys.py::TestSysGateForBranch.test_missing_worktree_reports_unmeasured  # noqa: E501
# frob:tests tests/gates_suite/test_sys.py::TestSysGateForBranch.test_snapshot_build_failure_reports_unmeasured  # noqa: E501
def sys_gate_for_branch(repo_root: Path, ref: str) -> tuple[Violation, ...]:
    """Run `sys_gate` (and the SELFAUDIT001/capability audit surface it
    composes) against `ref` -- a branch name or a worktree directory name
    under `repo_root` -- rather than whatever root a caller's own
    `GraphSnapshot` was built from. Builds a fresh, throwaway
    `GraphSnapshot` scoped to the resolved worktree -- never reuses a
    snapshot built for a different root. Returns a single SYS900
    `Severity.UNRESOLVED` violation (never an empty tuple) when `ref`
    cannot be resolved to a worktree or its snapshot fails to build:
    UNMEASURED is not the same claim as "scanned `ref` and found
    nothing". See docs/modules/gates.md#self-audit-at-land-selfaudit001-
    t-0756 for the rationale (T-4212)."""
    resolved = _resolve_ref_worktree(repo_root, ref)
    if resolved is None:
        return (
            _sys900_unmeasured(
                ref,
                f"no worktree checked out for {ref!r} was found under {repo_root}",
            ),
        )

    from frob.graph import build_graph

    with tempfile.TemporaryDirectory() as tmp:
        built = build_graph(resolved, Path(tmp) / "cache.db")
        if built.is_err:
            return (
                _sys900_unmeasured(
                    ref,
                    f"GraphSnapshot build failed for {resolved}: {built.danger_err}",
                ),
            )
        return sys_gate(resolved, built.danger_ok)
