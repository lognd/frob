"""T-4407: coverage-lock auto-commit helper for `frob verify now`, split out
of `verify_runner.py` to keep that module under LARGE001's 800-line
threshold. No behavior change from the code this replaces -- see
`_auto_commit_coverage_lock` for the full T-4041 rationale.
"""

from __future__ import annotations

from pathlib import Path

from frob.logging import get_logger

_log = get_logger(__name__)

#: The tracked, committed coverage-lock file `run_coalesced_verification`'s
#: own `frob check --full` pass can rewrite (`frob.gates._coverage.
#: write_coverage_lock`) as a deterministic side effect of measuring
#: coverage -- never a human decision, so `_auto_commit_coverage_lock`
#: (T-4041) attributes it automatically rather than leaving it as
#: unexplained debt on the primary. Path kept in sync with `frob.gates.
#: _coverage._LOCK_REL` by name (importing that private constant here
#: would pull `frob.gates` into this CLI-wiring module's import graph,
#: exactly the cycle `_default_verify_fn`'s own docstring already avoids).
_COVERAGE_LOCK_REL = "frob-coverage.lock.json"


def _auto_commit_coverage_lock(root: Path) -> None:
    """T-4041: `frob verify now` draining debt used to leave a rewritten
    `frob-coverage.lock.json` dirty on the primary -- a maintenance verb
    whose entire purpose is closing out debt was manufacturing new,
    unattributed ledger debt of its own (DirtyMain-blocking every
    concurrent `frob ticket land`, and requiring a human to invent a
    ticket just to explain a file frob itself rewrote for its own
    bookkeeping). The rewrite is a deterministic consequence of the
    verify pass's own coverage measurement -- no human decision is
    involved -- so it is committed here with a self-describing message,
    the same "attribute it automatically" contract the ledger's own
    auto-commit (`frob.tickets._leases.commit_full_ledger_change`)
    already gives every other frob-owned tracked-file write. A no-op
    when the file is unchanged, untracked, or `root` is not a git
    worktree at all -- never raises, since a failed auto-commit here
    must not turn a successful verify run into a hard failure; it is
    logged instead so the dirty file is at least explained."""
    from frob import gitio

    status = gitio.run_argv(
        ["git", "-C", str(root), "status", "--porcelain", "--", _COVERAGE_LOCK_REL]
    )
    if (
        status.is_err
        or status.danger_ok.returncode != 0
        or not status.danger_ok.stdout.strip()
    ):
        return
    add = gitio.run_argv(["git", "-C", str(root), "add", "--", _COVERAGE_LOCK_REL])
    if add.is_err or add.danger_ok.returncode != 0:
        _log.warning(
            "verify now: could not stage %s for auto-commit (%s) -- left "
            "dirty on the primary, will DirtyMain-block a concurrent land",
            _COVERAGE_LOCK_REL,
            add.danger_err if add.is_err else add.danger_ok.stderr,
        )
        return
    commit = gitio.run_argv(
        [
            "git",
            "-C",
            str(root),
            "commit",
            "-m",
            "chore(verify): refresh frob-coverage.lock.json (frob verify now, T-4041)",
            "--",
            _COVERAGE_LOCK_REL,
        ]
    )
    if commit.is_err or commit.danger_ok.returncode != 0:
        _log.warning(
            "verify now: could not auto-commit %s (%s) -- left dirty on "
            "the primary, will DirtyMain-block a concurrent land",
            _COVERAGE_LOCK_REL,
            commit.danger_err if commit.is_err else commit.danger_ok.stderr,
        )
