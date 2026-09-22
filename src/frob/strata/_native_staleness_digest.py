"""T-4431/T-4434: seed a freshly-cut worktree's native source mtimes.

Split out of `_native_staleness.py` (T-4443, LARGE001: the parent module
crossed the 800-line threshold) -- this is the tracked-content-digest
comparison and mtime-backdating logic `seed_worktree_native_source_mtimes`
uses, kept as a sibling module rather than folded elsewhere so the split
follows one cohesive concern (worktree seeding) rather than an arbitrary
line cut. Every name here is re-exported from `_native_staleness` so no
caller needs to know the split happened.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from frob.excludes import walk_pruned
from frob.gitio import run_argv
from frob.logging import get_logger
from frob.testing._models import NativeSpec
from frob.testing._runners import load_natives

_log = get_logger(__name__)


def _tracked_source_digest(repo_like: Path, source_dir: str) -> str | None:
    """sha256 over every GIT-TRACKED file's (relative path, content bytes)
    under `repo_like/source_dir`, deterministic and order-stable -- private
    helper of `_seed_one_native_source_mtime` (T-4434). Deliberately NOT
    `_source_content_digest` (which walks the filesystem via `walk_pruned`):
    that walk is blind to `repo_like`'s REPO-ROOT `.gitignore` when called
    with a crate subdirectory as its own `root` argument (`_load_repo_
    ignore_globs` only ever reads `<root>/.gitignore`, and neither crate
    directory has its own), so a locally-generated, root-gitignored file
    that exists in one working tree but not the other (`uv.lock`, from
    `uv sync`/`maturin develop`, present in the primary checkout but never
    checked out into a fresh disposable worktree) reads as a genuine
    content divergence when it is really just build-tool noise (T-4434,
    the frob_core-still-stale follow-up to T-4431). `git ls-files` only
    ever lists TRACKED paths, so `uv.lock` (or any other future crate-local
    generated file the root `.gitignore` covers) never enters this digest
    at all -- a freshly checked-out worktree's tracked content for a path
    is, by construction, identical to `repo_like`'s own tracked content
    for that path whenever `repo_like` has no uncommitted edit there.
    Returns `None` on any git failure (not a git repo, spawn failure) --
    the caller's safe fallback is to skip backdating, never to guess."""
    listed = run_argv(("git", "-C", str(repo_like), "ls-files", "-z", "--", source_dir))
    if listed.is_err or listed.danger_ok.returncode != 0:
        _log.debug(
            "_tracked_source_digest: git ls-files failed for %s under %s",
            source_dir,
            repo_like,
        )
        return None
    rel_paths = sorted(p for p in listed.danger_ok.stdout.split("\0") if p)
    hasher = hashlib.sha256()
    for rel in rel_paths:
        try:
            content = (repo_like / rel).read_bytes()
        except OSError:
            continue
        hasher.update(rel.encode())
        hasher.update(b"\0")
        hasher.update(hashlib.sha256(content).digest())
        hasher.update(b"\n")
    return hasher.hexdigest()


def _seed_one_native_source_mtime(
    repo: Path, worktree: Path, spec: NativeSpec, source_dir_for
) -> str | None:
    """Backdate ONE declared native's source dir under `worktree` to the
    epoch, iff it exists there and its GIT-TRACKED content is identical to
    `repo`'s own copy -- private per-native split-out of
    `seed_worktree_native_source_mtimes` (T-4431, ARCH001 length budget;
    T-4434, tracked-only comparison). Returns `spec.name` if backdated,
    `None` if there was nothing to do (no matching source dir under
    `worktree`, or either side's git query failed) or the two copies
    genuinely diverge (left untouched, so a real content divergence still
    reads as stale to `stale_natives`). `source_dir_for` is
    `_native_staleness._source_dir_for`, passed in rather than imported
    back to avoid a circular import between the two sibling modules."""
    source_dir = source_dir_for(repo, spec)
    if source_dir is None:
        return None
    wt_source = worktree / source_dir
    if not wt_source.is_dir():
        return None
    repo_digest = _tracked_source_digest(repo, source_dir)
    wt_digest = _tracked_source_digest(worktree, source_dir)
    if repo_digest is None or wt_digest is None or repo_digest != wt_digest:
        _log.debug(
            "seed_worktree_native_source_mtimes: %s source diverges "
            "between %s and %s -- leaving checkout mtimes untouched",
            spec.name,
            repo,
            worktree,
        )
        return None
    for path in walk_pruned(wt_source):
        try:
            st = path.stat()
            os.utime(path, (st.st_atime, 0.0))
        except OSError as exc:
            _log.debug(
                "seed_worktree_native_source_mtimes: could not backdate %s: %s",
                path,
                exc,
            )
    return spec.name


# frob:ticket T-4431
# frob:ticket T-4434
# frob:doc docs/modules/testing.md#public-api
# tests/unit/strata/test_native_staleness.py::TestSeedWorktreeNativeSourceMtimes.test_i\
# dentical_source_is_backdated_and_reads_fresh
# tests/unit/strata/test_native_staleness.py::TestSeedWorktreeNativeSourceMtimes.test_d\
# iverged_source_is_left_untouched_and_still_stale
# tests/unit/strata/test_native_staleness.py::TestSeedWorktreeNativeSourceMtimes.test_r\
# epo_side_untracked_file_does_not_block_seeding
def seed_worktree_native_source_mtimes(
    repo: Path, worktree: Path, source_dir_for
) -> tuple[str, ...]:
    """T-4431: backdate a freshly-cut disposable worktree's native source
    directories so `stale_natives(worktree)` does not mistake a `git
    worktree add` checkout for a genuine source edit.

    Root cause: `_artifact_mtime` resolves a native's compiled artifact via
    `find_spec`, which always points at the SAME physical artifact
    regardless of which `root` `stale_natives` is called with (a land's
    synchronous check runs in-process against the primary's own venv) --
    only the SOURCE side of the comparison varies with `root`. `git
    worktree add` stamps every checked-out file's mtime at checkout time,
    so a brand-new worktree's native source reads "just edited" even when
    byte-identical to what the artifact was built from, and `stale_natives`
    reports every native stale on its very first call there, triggering
    T-1213's full auto-rebuild on every single land.

    Fix (delegated per-native to `_seed_one_native_source_mtime`): only a
    native whose worktree source is byte-identical to `repo`'s own gets its
    mtimes backdated to the epoch (never exceeds a real artifact mtime, so
    the mtime check reads "not stale" honestly); a genuinely diverged
    native is left untouched so T-1213's rebuild guarantee is unweakened.

    Returns the sorted names of natives backdated (empty if none matched,
    including when `load_natives(repo)` itself errors -- a no-op is always
    the safe fallback: worst case is paying the pre-existing rebuild cost
    this ticket exists to remove, never a wrong staleness verdict).
    `source_dir_for` is `_native_staleness._source_dir_for`, passed in to
    avoid a circular import between the two sibling modules."""
    loaded = load_natives(repo)
    if loaded.is_err:
        _log.debug(
            "seed_worktree_native_source_mtimes: could not load [[native]] "
            "entries (%s) -- skipping",
            loaded.danger_err,
        )
        return ()
    seeded = [
        name
        for spec in loaded.danger_ok
        if (name := _seed_one_native_source_mtime(repo, worktree, spec, source_dir_for))
        is not None
    ]
    if seeded:
        _log.info(
            "seed_worktree_native_source_mtimes: backdated %s under %s "
            "(content identical to %s)",
            sorted(seeded),
            worktree,
            repo,
        )
    return tuple(sorted(seeded))


__all__ = [
    "seed_worktree_native_source_mtimes",
]
