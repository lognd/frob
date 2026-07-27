"""Worktree warm pool (T-0738, part 2 of T-0732): pre-create N git
worktrees with native extensions already built and `main` already
merged in, so a dispatched agent leases a ready-to-go worktree instead
of paying the per-worktree `cargo`/`maturin` build cost (and the
`git worktree add` + merge step) on its own critical path.

Part 1 of T-0732 (the shared `CARGO_TARGET_DIR` keyed on the git common
dir, see the Makefile's own comment) already cut a from-scratch build
from ~34s to ~11s by letting every worktree reuse one clone-wide cargo
cache. This closes the REMAINING per-worktree cost: even with a warm
cargo cache, `maturin develop` still re-links per worktree (cargo keys
its build cache by absolute output path, so a worktree at a new path is
never a 100% no-op), and `git worktree add` + a `main` merge still costs
real wall-clock time on the dispatch path itself. Pre-warming a pool
ahead of dispatch moves that cost off the critical path entirely: it
happens in the background, before an agent is even assigned a ticket.

State lives in a small JSON manifest under the pool directory itself
(`<pool_dir>/manifest.json`), one entry per warmed worktree -- there is
no cross-worktree side channel like `frob.tickets._leases`'s shared-
git-common-dir lease files, because pool worktrees are not yet assigned
to any ticket; `lease_worktree` is the one operation that hands a ready
entry to a caller and removes it from the pool's own bookkeeping.

Concurrency: this module does not add its own file locking beyond
`_write_manifest`'s atomic replace. It is the same posture
`frob.tickets._leases` and `frob.scaffold.project` already take with
their own JSON state files in this repo -- a best-effort, single-writer-
at-a-time convenience layer, not a distributed lock service. A `frob
scaffold pool` CLI subcommand wiring `warm_pool`/`lease_worktree` through
`frob.app.scaffold_runner` is tracked separately (out of this ticket's
`src/frob/scaffold/**`-only scope, since that wiring touches
`src/frob/app/**`) -- see the ticket filed alongside this module's Done
report.
"""
# frob:waive INV006 reason="T-0738 first-turn-on pool: this module's few 'only' hits \
# (the scope-cut prose above, 'informational only' on PoolEntry.created_at, \
# 'ready=True only if both...' on warm_worktree, 'read-only wrapper' on pool_status) \
# are source-level design-rationale comments/docstrings describing already-implemented \
# internal behavior, verifiable by reading the code they annotate, rather than a \
# separate cross-module contract needing its own tracked invariant -- same disposition \
# as frob.tickets._leases's own INV006 waiver."

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob import gitio
from frob.logging import get_logger

_log = get_logger(__name__)

# frob:doc docs/guides/worktree-pool.md#pool-directory
MANIFEST_FILENAME = "manifest.json"

# frob:doc docs/guides/worktree-pool.md#pool-directory
DEFAULT_POOL_DIRNAME = "frob-pool"

# frob:doc docs/guides/worktree-pool.md#pool-directory
DEFAULT_BASE_REF = "main"


# frob:doc docs/guides/worktree-pool.md#public-api-frobscaffold
class PoolError(ErrorSet):
    """Fallible outcomes of every warm-pool operation in this module."""

    GitCommonDirUnavailable = "could not resolve the shared git common dir"
    WorktreeAddFailed = "git worktree add failed for a new pool slot"
    MergeFailed = "merging the base ref into a leased worktree failed"
    BuildFailed = "the natives-build step failed for a pool slot"
    ManifestWriteFailed = "writing the pool manifest failed"
    ManifestReadFailed = "reading the pool manifest failed (malformed JSON)"
    Empty = "no ready worktree is available in the pool"


# frob:doc docs/guides/worktree-pool.md#public-api-frobscaffold
# The `build_fn` callback shape every warm/lease/refill function accepts:
# given a freshly `git worktree add`-ed path, return `Ok(None)` if the
# natives build succeeded or `Err(PoolError.BuildFailed)` (or any other
# `PoolError` member) if it did not. `_default_build_fn` is the real
# implementation (`make core`); tests inject a fast fake instead.
BuildFn = Callable[[Path], Result[None, PoolError]]


# frob:doc docs/guides/worktree-pool.md#public-api-frobscaffold
# frob:ticket T-0738
class PoolEntry(BaseModel):
    """One pool slot: an absolute worktree `path`, its `index` (stable
    slot number reused across refills), and whether it is `ready`
    (natives built, `main` merged, waiting to be leased) or still being
    warmed. `created_at` is an ISO-8601 UTC timestamp, informational only
    -- nothing in this module currently expires a pool entry by age the
    way `frob.tickets._leases` expires a ticket lease."""

    model_config = {}

    path: str
    index: int
    ready: bool
    created_at: str


def _now_iso() -> str:
    """Current UTC time as an ISO-8601 string, the same shape
    `frob.tickets._leases` writes for `recorded_at` -- kept as a tiny
    private helper here rather than imported, since this module has no
    other dependency on that package and duplicating one `datetime.now`
    call is cheaper than adding a cross-package import for it."""
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


# frob:doc docs/guides/worktree-pool.md#public-api-frobscaffold
# frob:tests \
# tests/system/test_scaffold_pool.py::TestDefaultPoolDir.test_resolves_under_git_common\
# _dir kind="unit"  # noqa: E501
def default_pool_dir(repo_root: Path) -> Result[Path, PoolError]:
    """`<git-common-dir>/frob-pool`, the pool directory used when a
    caller does not pass its own `pool_dir` -- lives under the shared
    git common dir (T-0784's `gitio.git_common_dir`) so, like
    `frob.tickets._leases`'s leases directory, it is visible and stable
    across every worktree of the same clone rather than living inside
    one worktree's own tree (which would vanish if that worktree were
    ever removed)."""
    common = gitio.git_common_dir(repo_root)
    if common.is_err:
        _log.warning("scaffold.pool: git common dir unavailable under %s", repo_root)
        return Err(PoolError.GitCommonDirUnavailable)
    return Ok(common.danger_ok / DEFAULT_POOL_DIRNAME)


def _resolve_pool_dir(
    repo_root: Path, pool_dir: Path | None
) -> Result[Path, PoolError]:
    """`pool_dir` itself if given, else `default_pool_dir(repo_root)` --
    the one place every public function in this module resolves its
    optional `pool_dir` parameter, so the git-common-dir fallback rule
    lives in exactly one spot rather than being re-derived at each call
    site."""
    if pool_dir is not None:
        return Ok(pool_dir)
    return default_pool_dir(repo_root)


def _manifest_path(pool_dir: Path) -> Path:
    """The manifest JSON file for `pool_dir`."""
    return pool_dir / MANIFEST_FILENAME


# frob:doc docs/guides/worktree-pool.md#public-api-frobscaffold
# frob:tests \
# tests/system/test_scaffold_pool.py::TestManifestRoundTrip.test_write_then_read_round_\
# trips kind="unit"  # noqa: E501
def read_manifest(pool_dir: Path) -> Result[tuple[PoolEntry, ...], PoolError]:
    """Every currently-recorded pool entry, in slot-`index` order. An
    absent manifest file (a pool directory that has never been warmed
    yet) is `Ok(())`, not an error -- there is nothing malformed about a
    pool that simply has not been created yet. A present-but-unparseable
    file is `Err(ManifestReadFailed)`, logged."""
    path = _manifest_path(pool_dir)
    if not path.is_file():
        return Ok(())
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _log.warning("scaffold.pool: could not parse manifest %s: %s", path, exc)
        return Err(PoolError.ManifestReadFailed)
    entries = tuple(PoolEntry.model_validate(item) for item in raw)
    return Ok(tuple(sorted(entries, key=lambda e: e.index)))


def _write_manifest(
    pool_dir: Path, entries: tuple[PoolEntry, ...]
) -> Result[None, PoolError]:
    """Overwrite `pool_dir`'s manifest with exactly `entries` (sorted by
    `index`), creating `pool_dir` first if needed. Writes to a `.tmp`
    sibling and renames over the real path -- `Path.rename` is an atomic
    replace on the same filesystem (POSIX and Windows both), so a reader
    never observes a half-written manifest."""
    try:
        pool_dir.mkdir(parents=True, exist_ok=True)
        tmp = _manifest_path(pool_dir).with_suffix(".tmp")
        ordered = sorted(entries, key=lambda e: e.index)
        tmp.write_text(
            json.dumps([e.model_dump() for e in ordered], indent=2),
            encoding="utf-8",
        )
        tmp.rename(_manifest_path(pool_dir))
    except OSError as exc:
        _log.warning(
            "scaffold.pool: could not write manifest under %s: %s", pool_dir, exc
        )
        return Err(PoolError.ManifestWriteFailed)
    return Ok(None)


def _default_build_fn(path: Path) -> Result[None, PoolError]:
    """The real natives-build step a warmed pool slot runs by default:
    `make core` in the new worktree, matching exactly what an agent's own
    warm-up (`docs/guides/agent-playbook.md` section 1) would otherwise
    run on its own critical path. Callers (tests, or a caller that has
    nothing to build) inject their own `build_fn` instead of this one --
    see `warm_worktree`'s `build_fn` parameter."""
    spawned = gitio.run_argv(("make", "core"), cwd=path, timeout_s=900.0)
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.warning("scaffold.pool: make core failed in %s", path)
        return Err(PoolError.BuildFailed)
    return Ok(None)


# frob:doc docs/guides/worktree-pool.md#public-api-frobscaffold
# frob:tests \
# tests/system/test_scaffold_pool.py::TestWarmWorktree.test_creates_worktree_and_marks_\
# ready kind="unit"  # noqa: E501
# frob:tests \
# tests/system/test_scaffold_pool.py::TestWarmWorktree.test_build_failure_marks_not_rea\
# dy kind="unit"  # noqa: E501
def warm_worktree(
    repo_root: Path,
    pool_dir: Path,
    index: int,
    *,
    base_ref: str = DEFAULT_BASE_REF,
    build_fn: BuildFn | None = None,
) -> Result[PoolEntry, PoolError]:
    """Create a FRESH worktree for pool slot `index` under `pool_dir`
    (`git worktree add -B frob-pool/<index>-<token> <path> <base_ref>`,
    where `<token>` is a short random suffix -- see below for why), then
    run `build_fn(path)` (defaults to `_default_build_fn`, i.e. `make
    core`) to warm the natives. Records a `PoolEntry` in the manifest
    either way -- `ready=True` only if both the `git worktree add` and
    the build step succeeded; a build failure still leaves the worktree
    on disk (so it is not silently lost) but marks it `ready=False`, and
    `lease_worktree` never hands out a not-ready entry.

    The path/branch are NOT simply `pool-<index>`/`frob-pool/<index>`
    reused verbatim across refills: `lease_worktree` hands a slot's
    worktree out to a caller WITHOUT deleting it from disk (the caller
    now owns and works in it), then starts a background `warm_worktree`
    call for the SAME `index` to refill the pool. If that refill reused
    the identical path/branch, `git worktree add` would collide with the
    just-leased, still-in-use directory the moment a caller's own agent
    starts working in it -- a real bug caught by this module's own
    `TestRefillAsync` test. A short random token keeps `index` as a
    stable, human-readable SLOT NUMBER for status/manifest display while
    guaranteeing every `warm_worktree` call gets a path/branch no
    previous call (leased or not) could still be occupying.

    `build_fn`, if given, replaces `_default_build_fn` entirely -- tests
    inject a fast fake (`Ok(None)` or `Err(PoolError.BuildFailed)`
    instantly) instead of a real `make core` compile."""
    fn: BuildFn = build_fn if build_fn is not None else _default_build_fn
    token = uuid4().hex[:8]
    path = pool_dir / f"pool-{index}-{token}"
    branch = f"frob-pool/{index}-{token}"
    added = gitio.run_argv(
        (
            "git",
            "-C",
            str(repo_root),
            "worktree",
            "add",
            "-B",
            branch,
            str(path),
            base_ref,
        ),
        timeout_s=120.0,
    )
    if added.is_err or added.danger_ok.returncode != 0:
        _log.warning(
            "scaffold.pool: git worktree add failed for slot %d under %s",
            index,
            pool_dir,
        )
        return Err(PoolError.WorktreeAddFailed)

    built = fn(path)
    ready = built.is_ok
    if not ready:
        _log.warning(
            "scaffold.pool: build step failed for pool slot %d at %s", index, path
        )

    entries = read_manifest(pool_dir)
    remaining = (
        tuple(e for e in entries.danger_ok if e.index != index) if entries.is_ok else ()
    )
    entry = PoolEntry(path=str(path), index=index, ready=ready, created_at=_now_iso())
    write_result = _write_manifest(pool_dir, (*remaining, entry))
    if write_result.is_err:
        return Err(write_result.danger_err)
    return Ok(entry)


# frob:doc docs/guides/worktree-pool.md#public-api-frobscaffold
# frob:tests \
# tests/system/test_scaffold_pool.py::TestWarmPool.test_fills_pool_to_n_slots \
# kind="unit"  # noqa: E501
# frob:tests \
# tests/system/test_scaffold_pool.py::TestWarmPool.test_leaves_existing_ready_slots_alo\
# ne kind="unit"  # noqa: E501
def warm_pool(
    repo_root: Path,
    n: int,
    *,
    pool_dir: Path | None = None,
    base_ref: str = DEFAULT_BASE_REF,
    build_fn: BuildFn | None = None,
) -> Result[tuple[PoolEntry, ...], PoolError]:
    """Ensure the pool under `pool_dir` (default `default_pool_dir(repo_root)`)
    holds exactly `n` slots, warming (`warm_worktree`) whichever of slots
    `0..n-1` are missing or not already `ready` -- a slot that is already
    `ready` in the manifest is left untouched (so re-running `warm_pool`
    after a partial fill is cheap and idempotent, not a full n-worktree
    rebuild every time). Returns the full resulting set of `n` entries in
    slot order, or the first `Err` encountered warming any slot (earlier
    successfully-warmed slots are still recorded in the manifest even if
    a later slot fails -- `warm_pool` does not roll those back)."""
    resolved = _resolve_pool_dir(repo_root, pool_dir)
    if resolved.is_err:
        return Err(resolved.danger_err)
    dir_path = resolved.danger_ok

    existing = read_manifest(dir_path)
    by_index = {e.index: e for e in existing.danger_ok} if existing.is_ok else {}

    for index in range(n):
        current = by_index.get(index)
        if current is not None and current.ready:
            continue
        warmed = warm_worktree(
            repo_root, dir_path, index, base_ref=base_ref, build_fn=build_fn
        )
        if warmed.is_err:
            return Err(warmed.danger_err)
        by_index[index] = warmed.danger_ok

    final = read_manifest(dir_path)
    if final.is_err:
        return Err(final.danger_err)
    return Ok(tuple(e for e in final.danger_ok if e.index < n))


# frob:doc docs/guides/worktree-pool.md#public-api-frobscaffold
# frob:tests \
# tests/system/test_scaffold_pool.py::TestLeaseWorktree.test_leases_ready_slot_and_remo\
# ves_it kind="unit"  # noqa: E501
# frob:tests \
# tests/system/test_scaffold_pool.py::TestLeaseWorktree.test_empty_pool_returns_err \
# kind="unit"  # noqa: E501
# frob:tests \
# tests/system/test_scaffold_pool.py::TestLeaseWorktree.test_lease_merges_base_ref_curr\
# ent kind="unit"  # noqa: E501
def lease_worktree(
    repo_root: Path,
    *,
    pool_dir: Path | None = None,
    base_ref: str = DEFAULT_BASE_REF,
    refill: bool = True,
    build_fn: BuildFn | None = None,
) -> Result[PoolEntry, PoolError]:
    """Hand out the lowest-`index` `ready` pool slot: merges `base_ref`
    into it (so a slot warmed a while ago still starts current with
    `main`, not just current as of its own warm time -- the acceptance
    criterion's "main current" half), removes it from the manifest (a
    leased slot is no longer a pool entry; it is now the caller's
    worktree to use and eventually clean up like any other dispatched
    worktree), and -- unless `refill=False` -- starts a background
    daemon thread that re-warms the same slot index so the pool refills
    without blocking the caller (the acceptance criterion's "pool
    refills in the background" half).

    `Err(Empty)` if no `ready` entry exists; `Err(MergeFailed)` if the
    merge step itself fails (the slot is NOT removed from the manifest
    in that case, so a caller can retry or fall back to a from-scratch
    worktree instead of losing a warmed-but-now-stuck slot silently)."""
    resolved = _resolve_pool_dir(repo_root, pool_dir)
    if resolved.is_err:
        return Err(resolved.danger_err)
    dir_path = resolved.danger_ok

    existing = read_manifest(dir_path)
    if existing.is_err:
        return Err(existing.danger_err)
    ready_entries = [e for e in existing.danger_ok if e.ready]
    if not ready_entries:
        return Err(PoolError.Empty)
    chosen = min(ready_entries, key=lambda e: e.index)

    merged = gitio.run_argv(
        ("git", "-C", chosen.path, "merge", base_ref), timeout_s=60.0
    )
    if merged.is_err or merged.danger_ok.returncode != 0:
        _log.warning(
            "scaffold.pool: merge of %s into leased slot %d (%s) failed",
            base_ref,
            chosen.index,
            chosen.path,
        )
        return Err(PoolError.MergeFailed)

    remaining = tuple(e for e in existing.danger_ok if e.index != chosen.index)
    written = _write_manifest(dir_path, remaining)
    if written.is_err:
        return Err(written.danger_err)

    if refill:
        refill_pool_async(
            repo_root,
            chosen.index,
            pool_dir=dir_path,
            base_ref=base_ref,
            build_fn=build_fn,
        )
    return Ok(chosen)


# frob:doc docs/guides/worktree-pool.md#public-api-frobscaffold
# frob:tests \
# tests/system/test_scaffold_pool.py::TestRefillAsync.test_refill_thread_rewarms_slot \
# kind="unit"  # noqa: E501
def refill_pool_async(
    repo_root: Path,
    index: int,
    *,
    pool_dir: Path | None = None,
    base_ref: str = DEFAULT_BASE_REF,
    build_fn: BuildFn | None = None,
) -> threading.Thread:
    """Start (and return, already-started) a daemon background thread
    that re-warms pool slot `index` via `warm_worktree` -- the mechanism
    `lease_worktree` uses to refill after handing a slot out, exposed as
    its own function so a caller (or a test) can start a refill directly
    and `.join()` it deterministically instead of racing a lease call's
    internal thread. Failures inside the thread are logged (`warm_worktree`
    already logs its own `Err` cases) and never raised into the caller's
    thread -- a background refill that fails leaves the slot simply
    absent from the manifest until a later `warm_pool`/`lease_worktree`
    call notices and retries it, same as any other missing slot."""
    resolved = _resolve_pool_dir(repo_root, pool_dir)
    if resolved.is_err:
        _log.warning(
            "scaffold.pool: cannot refill slot %d, git common dir unavailable",
            index,
        )
        thread = threading.Thread(target=lambda: None, daemon=True)
        thread.start()
        return thread
    dir_path = resolved.danger_ok

    def _run() -> None:
        """Thread body: warm the one slot, logging (not raising) on failure."""
        result = warm_worktree(
            repo_root, dir_path, index, base_ref=base_ref, build_fn=build_fn
        )
        if result.is_err:
            _log.warning(
                "scaffold.pool: background refill of slot %d failed: %s",
                index,
                result.danger_err.value,
            )

    thread = threading.Thread(
        target=_run, daemon=True, name=f"frob-pool-refill-{index}"
    )
    thread.start()
    return thread


# frob:doc docs/guides/worktree-pool.md#public-api-frobscaffold
# frob:tests \
# tests/system/test_scaffold_pool.py::TestPoolStatus.test_status_reflects_manifest \
# kind="unit"  # noqa: E501
def pool_status(
    repo_root: Path, *, pool_dir: Path | None = None
) -> Result[tuple[PoolEntry, ...], PoolError]:
    """The current pool manifest, as-is, for a status/inspection caller
    (`make pool-status`) -- a thin, read-only wrapper over
    `read_manifest` that also resolves the default `pool_dir` the same
    way every other public function here does, so a caller never needs
    to know the git-common-dir resolution rule itself."""
    resolved = _resolve_pool_dir(repo_root, pool_dir)
    if resolved.is_err:
        return Err(resolved.danger_err)
    return read_manifest(resolved.danger_ok)


__all__ = [
    "DEFAULT_BASE_REF",
    "DEFAULT_POOL_DIRNAME",
    "MANIFEST_FILENAME",
    "PoolEntry",
    "PoolError",
    "default_pool_dir",
    "lease_worktree",
    "pool_status",
    "read_manifest",
    "refill_pool_async",
    "warm_pool",
    "warm_worktree",
]
