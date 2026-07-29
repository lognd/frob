"""Warm in-memory session state for `frob.serve`
(docs/modules/serve.md#daemon-lifecycle).

`frob serve` runs as one long-lived stdio process; before this module every
MCP tool call re-loaded the graph snapshot, the stamped violation baseline,
and the collected python test ids from disk on every single call, even
across two calls with nothing changed on disk between them. `_WarmState`
keeps the last-built copy of all three in process memory per repo root,
keyed by `_repo_dirty_key` -- a cheap `git rev-parse HEAD` + `git status
--porcelain` signature. An unchanged key means the working tree has not
moved since the last build, so `_warm_state` returns the cached copy with
zero re-walk/re-parse/subprocess cost; a changed key falls through to a
fresh `build_graph`/`load_baseline`/`collect_python_tests` pass, each of
which is itself already incremental on disk (`build_graph` only reparses
files whose content hash moved, `collect_python_tests` is cached on its own
content key, T-0333) -- so even a "cold" refresh here only redoes the work
the on-disk caches could not already answer.

Scope note (T-0177 Done report): this gives incremental reuse at the
GRAPH/baseline/test-list level, not true per-obligation dependency-tracked
gate re-evaluation -- `frob.gates.run_gates` still evaluates every selected
gate fully on each `frob_check_delta` call (docs/modules/serve.md's
staleness/correctness contract spells out exactly what is and is not
covered).
"""
# frob:waive INV006 reason="T-1023 INV006 burn-down: this file's \
# exclusivity-vocabulary hit is source-level design-rationale/scope-cut prose (a \
# docstring or comment describing already-implemented internal behavior, verifiable by \
# reading the code it annotates) rather than a separate cross-module contract needing \
# its own tracked invariant; disposed as a calibration batch, not claim-by-claim, same \
# INV006 first-turn-on-pool disposition this repo already applies elsewhere (T-0585)"

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani import Err, Ok
from typani.result import Result

from frob.gates import load_baseline
from frob.gitio import run_argv
from frob.graph import BuildError, GraphSnapshot, build_graph
from frob.logging import get_logger
from frob.testing import CollectedTests, collect_python_tests

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "cache.db"
# Sentinel `_repo_dirty_key` for a root `git` cannot answer for (not a repo,
# or git itself unavailable) -- never matches a cached key, so `_warm_state`
# always takes the cold path there. Correct (never serves a stale answer),
# merely uncached.
_ALWAYS_DIRTY = "frob-serve-no-git-signal"


# frob:doc docs/modules/serve.md#warm-state
# frob:waive COV007 reason="T-0871: same -- docs/modules/serve.md#warm-state documents this warm-cache internal; demoted to private in this ticket (frob-exports: every real caller, including tests, already accessed it module-qualified) but remains the thing the doc section describes, and the doc text/directives were updated to the new name"  # noqa: E501
class _WarmState(BaseModel):
    """One repo root's cached graph snapshot, stamped baseline, and
    collected python test ids, tagged with the `_repo_dirty_key` they were
    built at -- `_warm_state` reuses this verbatim while the key still
    matches the live tree."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    root: str
    dirty_key: str
    snapshot: GraphSnapshot
    baseline: dict | None
    tests: CollectedTests | None


_STATES: dict[str, _WarmState] = {}


def _dirty_path_from_porcelain_line(line: str) -> str | None:
    """The path a `git status --porcelain=v1` line names -- everything after
    the 2-char status + 1 space prefix, and after `" -> "` for a rename
    (`R  old -> new`, T-0177: only the NEW path's content matters here)."""
    if len(line) < 4:
        return None
    rest = line[3:]
    if " -> " in rest:
        rest = rest.rsplit(" -> ", 1)[1]
    return rest


# frob:waive EXHAUST001 reason="T-1062: leaked Unknown traces to st.st_mtime_ns/ \
# st.st_size, plain attribute access on the os.stat_result the caught full.stat() call \
# already produced; no further raise path is reachable from this function's \
# locally-visible calls"
def _stat_tag(root: Path, rel_path: str) -> str:
    """`"path:mtime_ns:size"` for `rel_path` under `root`, or `"path:gone"`
    if it no longer exists (deleted since `git status` was run) -- folded
    into `_repo_dirty_key` so an UNTRACKED file's own CONTENT edit is
    observable. `git status --porcelain` alone only reports "this path is
    untracked" (`?? path`), never a content signal, so editing an
    already-untracked file's bytes without staging/committing would
    otherwise never change the key at all -- a real gap this closes."""
    full = root / rel_path
    try:
        st = full.stat()
    except OSError:
        return f"{rel_path}:gone"
    return f"{rel_path}:{st.st_mtime_ns}:{st.st_size}"


# frob:doc docs/modules/serve.md#warm-state
# frob:tests tests/test_serve.py::TestRepoDirtyKey.test_non_git_root_is_always_dirty kind="unit"  # noqa: E501
# frob:waive COV007 reason="T-0871: same -- docs/modules/serve.md#warm-state documents this warm-cache internal; demoted to private in this ticket (frob-exports: every real caller, including tests, already accessed it module-qualified) but remains the thing the doc section describes, and the doc text/directives were updated to the new name"  # noqa: E501
def _repo_dirty_key(root: Path) -> str:
    """`git rev-parse HEAD` + `git status --porcelain=v1 --untracked-files=all`
    (excluding `.frob/`, via the `:!.frob` pathspec, not `.gitignore` --
    `build_graph`/`collect_python_tests` write `.frob/cache.db` and friends
    as a SIDE EFFECT of the very warm-build this key gates, so including it
    would make every build self-_invalidate on the next call regardless of
    whether the tracked tree actually moved), PLUS an `(mtime_ns, size)` tag
    per path the status output names (`_stat_tag` -- porcelain status alone
    only reports THAT a path is untracked/modified, never its content, so
    editing an already-untracked file's bytes without staging it would
    otherwise be invisible to this key). Unchanged across two calls means
    nothing that matters has moved since the first, so the tree is provably
    identical for `_warm_state`'s purposes. Returns the `_ALWAYS_DIRTY`
    sentinel (never cacheable) for a non-git `root` or if either git
    invocation fails."""
    head = run_argv(("git", "-C", str(root), "rev-parse", "HEAD"))
    if head.is_err or head.danger_ok.returncode != 0:
        return _ALWAYS_DIRTY
    status = run_argv(
        (
            "git",
            "-C",
            str(root),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "--",
            ":!.frob",
        )
    )
    if status.is_err or status.danger_ok.returncode != 0:
        return _ALWAYS_DIRTY
    lines = status.danger_ok.stdout.splitlines()
    dirty_paths = sorted(
        {p for p in (_dirty_path_from_porcelain_line(ln) for ln in lines) if p}
    )
    stat_tags = "\n".join(_stat_tag(root, p) for p in dirty_paths)
    return f"{head.danger_ok.stdout.strip()}\n{status.danger_ok.stdout}\n{stat_tags}"


def _collect_tests_or_none(root: Path) -> CollectedTests | None:
    """`collect_python_tests(root).ok`, logging and returning `None` on
    failure -- a collection failure degrades `frob_run_touched_tests`'s
    warm cache, it must not fail graph/baseline warmup."""
    collected = collect_python_tests(root)
    if collected.is_err:
        _log.warning("serve: warm: test collection failed: %s", collected.danger_err)
        return None
    return collected.danger_ok


def _build_cold(root: Path, dirty_key: str) -> Result[_WarmState, BuildError]:
    """Cold-build a fresh `_WarmState` at `dirty_key`: graph snapshot
    (`build_graph`, itself incremental via the `.frob` sqlite cache), the
    stamped baseline (`None` if never stamped), and collected python test
    ids (best-effort, `None` on failure) -- then cache it for `root`."""
    cache = root / _CACHE_REL
    snapshot_result = build_graph(root, cache)
    if snapshot_result.is_err:
        _log.error(
            "serve: warm: graph build failed for %s: %s",
            root,
            snapshot_result.danger_err,
        )
        return Err(snapshot_result.danger_err)

    state = _WarmState(
        root=str(root),
        dirty_key=dirty_key,
        snapshot=snapshot_result.danger_ok,
        baseline=load_baseline(root),
        tests=_collect_tests_or_none(root),
    )
    _STATES[str(root)] = state
    _log.info(
        "serve: warm: cold-built state for %s at dirty_key=%s", root, dirty_key[:12]
    )
    return Ok(state)


# frob:doc docs/modules/serve.md#warm-state
# frob:tests tests/test_serve.py::TestWarmState.test_second_call_is_cache_hit kind="unit"  # noqa: E501
# frob:tests tests/test_serve.py::TestWarmState.test_file_change_forces_rebuild kind="unit"  # noqa: E501
# frob:waive COV007 reason="T-0871: same -- docs/modules/serve.md#warm-state documents this warm-cache internal; demoted to private in this ticket (frob-exports: every real caller, including tests, already accessed it module-qualified) but remains the thing the doc section describes, and the doc text/directives were updated to the new name"  # noqa: E501
def _warm_state(root: Path) -> Result[_WarmState, BuildError]:
    """The cached `_WarmState` for `root` if its `_repo_dirty_key` still
    matches the live tree (a pure memory hit for the graph snapshot and
    collected tests -- the two genuinely expensive parts); otherwise a
    fresh `_build_cold` pass, cached for the next call. The single entry
    point every `frob.serve` tool should use instead of loading the graph/
    baseline/tests cold itself.

    The baseline is always re-read fresh even on a cache hit
    (`load_baseline` is a plain json read, not worth gating behind
    `_repo_dirty_key`) -- `.frob/baseline` is itself under `.frob/`, which
    `_repo_dirty_key` deliberately excludes (it is the write-target of the
    very build this key gates), so a stamp written between two calls with
    no OTHER tree change would otherwise never be observed."""
    root = root.resolve()
    dirty_key = _repo_dirty_key(root)
    cached = _STATES.get(str(root))
    if cached is not None and cached.dirty_key == dirty_key:
        _log.debug(
            "serve: warm: cache hit for %s at dirty_key=%s", root, dirty_key[:12]
        )
        fresh_baseline = load_baseline(root)
        if fresh_baseline != cached.baseline:
            cached = cached.model_copy(update={"baseline": fresh_baseline})
            _STATES[str(root)] = cached
        return Ok(cached)
    return _build_cold(root, dirty_key)


# frob:doc docs/modules/serve.md#warm-state
# frob:waive COV007 reason="T-0871: same -- docs/modules/serve.md#warm-state documents this warm-cache internal; demoted to private in this ticket (frob-exports: every real caller, including tests, already accessed it module-qualified) but remains the thing the doc section describes, and the doc text/directives were updated to the new name"  # noqa: E501
def _invalidate(root: Path) -> None:
    """Drop `root`'s cached `_WarmState` so the next `_warm_state` call is
    guaranteed to rebuild cold -- used by the `frob_check_delta` verify
    mode and by tests; a no-op if nothing was cached."""
    _STATES.pop(str(root.resolve()), None)


__all__ = [
    "_WarmState",
    "_invalidate",
    "_repo_dirty_key",
    "_warm_state",
]
