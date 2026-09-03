"""frob.tickets._unlanded_cache -- T-3567's `doable`-summary TTL cache
write path for `_unlanded_branch_work`'s own findings (T-3734).

Split out of `frob.tickets._unlanded` (T-3734, LARGE001: T-3731's branch-
scan-budget addition pushed that module to 818 lines against the 800-line
threshold): this pair -- `_frob_dir_is_gitignored` and `_maybe_save_
unlanded_summary_cache` -- is a self-contained "persist reconcile's own
unlanded-branch findings" concern with a single caller
(`frob.tickets._reconcile.reconcile`), separable from `_unlanded`'s own
git-plumbing branch scan without breaking any internal reference. `_unlanded.py`
re-exports both names so this split stays invisible to every existing
caller/import site."""

# frob:ticket T-3734
# frob:waive REF002 reason="T-3734: this module has exactly one inbound reference by \
# design -- frob.tickets._unlanded re-exports _frob_dir_is_gitignored/_maybe_save_ \
# unlanded_summary_cache (`from frob.tickets._unlanded_cache import ...`) so every \
# existing `frob.tickets._unlanded.<name>` call/import site (frob.tickets._reconcile, \
# this module's only real caller) keeps working unchanged after this LARGE001 split, \
# the same re-export shape T-2826's sibling _check_chunking_baseline.py split already \
# established this precedent for."
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from frob.gitio import run_argv
from frob.logging import get_logger

_log = get_logger(__name__)


class _HasBranch(Protocol):
    """Structural type for `_maybe_save_unlanded_summary_cache`'s
    `unlanded_findings` elements: anything exposing `.branch: str`
    (`frob.tickets._unlanded._UnlandedWork`'s own shape) -- avoids this
    module importing `_unlanded` back, since `_unlanded` imports THIS
    module to re-export these two names (a reverse import would cycle)."""

    branch: str


# frob:ticket T-3567
# frob:ticket T-3734
# frob:tests tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork.test_populates_the_doable_summary_cache kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork.test_skips_the_cache_write_when_frob_dir_is_not_gitignored kind="unit"  # noqa: E501
def _frob_dir_is_gitignored(root: Path) -> bool:
    """Whether `root`'s own git configuration (`.gitignore` at any level
    `git check-ignore` consults, including a repo-root `.gitignore`, a
    global `core.excludesFile`, or `.git/info/exclude`) already excludes
    `.frob/` -- the precondition `reconcile` requires before writing
    `.frob/unlanded-summary-cache.json` (T-3522).

    T-3567: every OTHER `.frob/` writer this repo's own tests exercise
    (`ledger_lock`'s `.frob/tickets.lock`, principally) only ever appears
    clean in a bare test fixture with no `.gitignore` at all because an
    EARLIER `git add -A` in that same test's own setup already staged and
    committed it as ordinary tracked content before the write this test
    actually measures runs -- not because `.frob/` is genuinely ignored
    there. A first-time write to a path `git add -A` never touched before
    (this cache file, in a fixture exactly like T-1936's) has no such
    accidental cover, and writing it unconditionally regressed T-1936's
    own "reconcile --apply leaves the ledger clean" contract (measured:
    windows-latest run 33370059331). Every REAL frob-managed repo already
    gitignores `.frob/` (this project's own `.gitignore` template, `docs/
    guides/*` and this file's own module docstring elsewhere both assume
    it) -- this guard only ever actually skips the write in a bare test
    fixture that has not set that up, matching `_save_unlanded_summary_
    cache`'s own existing best-effort, log-and-swallow posture (a skipped
    write here just means `doable`'s cache stays cold, not an error)."""
    checked = run_argv(["git", "-C", str(root), "check-ignore", "--quiet", ".frob/"])
    return checked.is_ok and checked.danger_ok.returncode == 0


# frob:ticket T-3567
# frob:ticket T-3734
# frob:tests tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork.test_populates_the_doable_summary_cache kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork.test_skips_the_cache_write_when_frob_dir_is_not_gitignored kind="unit"  # noqa: E501
def _maybe_save_unlanded_summary_cache(
    root: Path, unlanded_findings: "tuple[_HasBranch, ...]"
) -> None:
    """`reconcile`'s own ARCH001 split (T-3567): populate the TTL cache
    `doable` reads (`frob.app.ticket_runner._query.
    _load_unlanded_summary_cache`) with the branch names `unlanded_
    findings` (`_unlanded_branch_work`'s own output, T-2127) just found --
    lazy import to avoid a core (`frob.tickets`) -> app-layer (`frob.app.
    ticket_runner`) import at module load time, same posture as `_land.
    py`'s own lazy `frob.app._check_chunking` import. This was the
    missing production write side `_save_unlanded_summary_cache`'s own
    docstring already documented as the intended caller; `doable` itself
    never scans branches inline (T-2629), so this reconcile call is now
    the only thing that keeps the cache fresh.

    T-3567: gated on `_frob_dir_is_gitignored` -- see that function's own
    docstring for why an unconditional write regressed T-1936.

    T-3734: `unlanded_findings` takes any iterable of objects with a
    `.branch: str` attribute (`_UnlandedWork`, `frob.tickets._unlanded`'s
    own scan-result type) -- typed loosely here to avoid this module
    importing `_unlanded` back (that module imports THIS one to re-export
    these two names, so a reverse import would cycle)."""
    from frob.app.ticket_runner._query import _save_unlanded_summary_cache

    branches = tuple(dict.fromkeys(finding.branch for finding in unlanded_findings))
    if _frob_dir_is_gitignored(root):
        _save_unlanded_summary_cache(root, branches)
    else:
        _log.debug(
            "reconcile: skipping unlanded-summary cache write under %s -- "
            ".frob/ is not gitignored here (T-3567), writing it would leave "
            "an untracked file `git status` (and every ledger-cleanliness "
            "contract this function's own callers rely on, T-1936) would "
            "see as dirty",
            root,
        )
