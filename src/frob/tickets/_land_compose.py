"""Out-of-tree tree/commit-object compose plus CAS ref publish (T-3088).

DECOMPOSITION CHILD 1 of T-3053 (parent epic). This module is a pure git-
plumbing primitive: it builds a prospective commit against a scratch index
file and publishes a ref move with compare-and-swap semantics. It is wired
to NOTHING yet -- `frob.tickets._land_squash` still runs `git merge --squash
--no-commit` against the root's own checked-out working tree, unchanged.
Wiring this primitive into that stage is T-3089's scope, not this one's.

WHY this exists: every stage of the current land pipeline
(`src/frob/tickets/_land*.py`) mutates root's checked-out working tree
directly (`git merge --squash --no-commit`, `git reset --hard`, a final
unconditional `git commit`). A concurrent land observes that intermediate
state as a dirty root mid-land (the T-3066 incident). Composing a commit
object out-of-tree -- against a private `GIT_INDEX_FILE`, never touching
`HEAD` or the worktree -- and publishing it with a single CAS `git
update-ref <ref> <new> <old>` removes that shared-tree window entirely.
Both halves are proven here against a scratch bare repo, not the live root.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pydantic import BaseModel
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.gitio import excerpt, run_argv
from frob.logging import get_logger
from frob.tickets._store import ledger_lock

_log = get_logger(__name__)


# frob:ticket T-3088
# frob:doc \
# docs/modules/tickets-landing.md#frobtickets_land_compose----out-of-tree-compose--cas-\
# publish-primitive-t-3088
# frob:tests tests/unit/test_land_compose.py::TestComposeTreeOutOfTree.test_compose_failure_returns_err  # noqa: E501
# frob:tests tests/unit/test_land_compose.py::TestPublishRefCas.test_racing_publish_second_gets_ref_moved  # noqa: E501
class LandComposeError(ErrorSet):
    """Fallible outcomes of the out-of-tree compose + CAS publish primitive
    (T-3088); kept as its own ErrorSet rather than folded into
    `frob.tickets._models.LandError` because this module has no caller yet
    -- T-3089 maps these onto the real `LandError` variants (`RefMoved`
    onto the existing `DirtyMain` refusal) at the wiring point."""

    ComposeFailed = "building the out-of-tree commit object failed"
    RefMoved = (
        "the target ref moved since expected_old_sha was captured (CAS lost the race)"
    )
    WorktreeSetupFailed = "could not cut the disposable git worktree to compose in"
    ResyncBlocked = (
        "root's index/worktree could not be advanced to the published tip -- a "
        "concurrent uncommitted edit touches a path the changeset also changed"
    )


def _apply_diff_to_scratch_index(
    repo: Path,
    base_commit: str,
    patch_source: str,
    scratch: str,
    env: dict[str, str],
) -> Result[None, LandComposeError]:
    """Diff `base_commit` against `patch_source` and `git apply --cached`
    the result into the scratch index `env["GIT_INDEX_FILE"]` names --
    private split-out of `compose_tree_out_of_tree` (T-2214 length budget).
    `--cached` never touches `repo`'s checked-out working tree."""
    diffed = run_argv(("git", "-C", str(repo), "diff", base_commit, patch_source))
    if diffed.is_err:
        _log.warning("land_compose: diff %s..%s failed", base_commit, patch_source)
        return Err(LandComposeError.ComposeFailed)
    diff_text = diffed.danger_ok.stdout
    if not diff_text.strip():
        return Ok(None)

    patch_file = Path(scratch) / "patch.diff"
    patch_file.write_text(diff_text)
    applied = run_argv(
        ("git", "-C", str(repo), "apply", "--cached", str(patch_file)), env=env
    )
    if applied.is_err or applied.danger_ok.returncode != 0:
        _log.warning(
            "land_compose: apply --cached %s..%s failed: %s",
            base_commit,
            patch_source,
            excerpt(applied.danger_ok.stderr) if applied.is_ok else applied.danger_err,
        )
        return Err(LandComposeError.ComposeFailed)
    return Ok(None)


# frob:ticket T-3088
# frob:doc \
# docs/modules/tickets-landing.md#frobtickets_land_compose----out-of-tree-compose--cas-\
# publish-primitive-t-3088
# frob:tests tests/unit/test_land_compose.py::TestComposeTreeOutOfTree.test_worktree_untouched_by_compose  # noqa: E501
# frob:tests tests/unit/test_land_compose.py::TestComposeTreeOutOfTree.test_composed_commit_contains_the_patch  # noqa: E501
# frob:tests tests/unit/test_land_compose.py::TestComposeTreeOutOfTree.test_compose_failure_returns_err  # noqa: E501
def compose_tree_out_of_tree(
    repo: Path, base_commit: str, patch_source: str
) -> Result[str, LandComposeError]:
    """Build a commit object representing `base_commit` plus the changes
    introduced by `patch_source` (a commit-ish, typically a branch tip),
    entirely against a scratch `GIT_INDEX_FILE` -- never invokes `git
    checkout`/`git reset` and never touches `repo`'s checked-out working
    tree or `HEAD`. Returns `Ok(new_commit_sha)` with `base_commit` as the
    sole parent, or `Err(ComposeFailed)` on any git-plumbing failure
    (including a diff that does not apply cleanly against `base_commit`).

    Mechanism: `git diff base_commit patch_source` piped through `git apply
    --cached` against a private index seeded via `git read-tree
    base_commit`, then `git write-tree` + `git commit-tree`. `--cached`
    means `git apply` only ever touches the index it is pointed at via
    `GIT_INDEX_FILE` -- it neither reads nor writes any file in the actual
    worktree, which is what makes this safe to run concurrently with a
    live checkout of `repo`.
    """
    with tempfile.TemporaryDirectory(prefix="frob-land-compose-") as scratch:
        index_file = Path(scratch) / "index"
        env = dict(os.environ)
        env["GIT_INDEX_FILE"] = str(index_file)

        read_tree = run_argv(
            ("git", "-C", str(repo), "read-tree", base_commit), env=env
        )
        if read_tree.is_err or read_tree.danger_ok.returncode != 0:
            _log.warning(
                "land_compose: read-tree %s failed: %s",
                base_commit,
                excerpt(read_tree.danger_ok.stderr)
                if read_tree.is_ok
                else read_tree.danger_err,
            )
            return Err(LandComposeError.ComposeFailed)

        applied = _apply_diff_to_scratch_index(
            repo, base_commit, patch_source, scratch, env
        )
        if applied.is_err:
            return Err(applied.danger_err)

        return _write_and_commit_scratch_index(repo, base_commit, patch_source, env)


def _write_and_commit_scratch_index(
    repo: Path, base_commit: str, patch_source: str, env: dict[str, str]
) -> Result[str, LandComposeError]:
    """`git write-tree` + `git commit-tree` against the scratch index
    `env["GIT_INDEX_FILE"]` names -- private split-out of
    `compose_tree_out_of_tree` (T-2214 length budget)."""
    written = run_argv(("git", "-C", str(repo), "write-tree"), env=env)
    if written.is_err or written.danger_ok.returncode != 0:
        _log.warning("land_compose: write-tree failed after applying %s", patch_source)
        return Err(LandComposeError.ComposeFailed)
    tree_sha = written.danger_ok.stdout.strip()

    committed = run_argv(
        (
            "git",
            "-C",
            str(repo),
            "commit-tree",
            tree_sha,
            "-p",
            base_commit,
            "-m",
            f"land_compose: {patch_source} onto {base_commit}",
        )
    )
    if committed.is_err or committed.danger_ok.returncode != 0:
        _log.warning("land_compose: commit-tree failed for tree %s", tree_sha)
        return Err(LandComposeError.ComposeFailed)
    new_sha = committed.danger_ok.stdout.strip()
    _log.info(
        "land_compose: composed %s (base=%s patch_source=%s) without "
        "touching the worktree",
        new_sha,
        base_commit,
        patch_source,
    )
    return Ok(new_sha)


# frob:ticket T-3088
# frob:doc \
# docs/modules/tickets-landing.md#frobtickets_land_compose----out-of-tree-compose--cas-\
# publish-primitive-t-3088
# frob:tests \
# tests/unit/test_land_compose.py::TestPublishRefCas.test_sequential_publishes_succeed
# frob:tests tests/unit/test_land_compose.py::TestPublishRefCas.test_racing_publish_second_gets_ref_moved  # noqa: E501
def publish_ref_cas(
    repo: Path, ref: str, expected_old_sha: str, new_sha: str
) -> Result[None, LandComposeError]:
    """Move `ref` to `new_sha` iff it currently points at `expected_old_sha`
    (`git update-ref <ref> <new_sha> <expected_old_sha>`, git's own atomic
    compare-and-swap). Returns `Ok(None)` on success; `Err(RefMoved)` --
    never a silent no-op, never a corrupted ref -- when `ref` no longer
    matches `expected_old_sha` (someone else published first) or the
    update-ref call otherwise fails."""
    result = run_argv(
        ("git", "-C", str(repo), "update-ref", ref, new_sha, expected_old_sha)
    )
    if result.is_err:
        _log.warning("land_compose: publish_ref_cas spawn failed for %s", ref)
        return Err(LandComposeError.RefMoved)
    if result.danger_ok.returncode != 0:
        _log.info(
            "land_compose: publish_ref_cas lost the race on %s "
            "(expected_old=%s new=%s): %s",
            ref,
            expected_old_sha,
            new_sha,
            excerpt(result.danger_ok.stderr),
        )
        return Err(LandComposeError.RefMoved)
    _log.info(
        "land_compose: published %s -> %s (was %s) via CAS",
        ref,
        new_sha,
        expected_old_sha,
    )
    return Ok(None)


# frob:ticket T-3107
# frob:doc \
# docs/modules/tickets-landing.md#frobtickets_land_compose----disposable-worktree-three\
# -way-squash-compose-t-3107
# frob:tests tests/unit/test_land_compose.py::TestDisposableSquashWorktree.test_clean_squash_reports_no_conflicts  # noqa: E501
# frob:tests tests/unit/test_land_compose.py::TestDisposableSquashWorktree.test_conflicting_squash_reports_the_conflicted_paths  # noqa: E501
class SquashStage(BaseModel):
    """A prepared disposable worktree holding a squash-merge result plus
    the paths git left unmerged in it -- the handle
    `compose_squash_in_disposable_worktree` yields so a caller can run the
    existing working-tree-based resolution/splice/bump/sweep stages against
    somewhere that is not the shared root."""

    model_config = {}

    worktree: Path
    conflicted: tuple[str, ...]


def _conflicted_paths(worktree: Path) -> Result[tuple[str, ...], LandComposeError]:
    """Paths git left unmerged in `worktree` after a merge
    (`git diff --name-only --diff-filter=U`), sorted -- private helper of
    `compose_squash_in_disposable_worktree`."""
    listed = run_argv(
        ("git", "-C", str(worktree), "diff", "--name-only", "--diff-filter=U")
    )
    if listed.is_err or listed.danger_ok.returncode != 0:
        _log.warning("land_compose: could not list unmerged paths in %s", worktree)
        return Err(LandComposeError.ComposeFailed)
    return Ok(
        tuple(
            sorted(
                line.strip()
                for line in listed.danger_ok.stdout.splitlines()
                if line.strip()
            )
        )
    )


def _squash_into_worktree(
    worktree: Path, branch_name: str
) -> Result[SquashStage, LandComposeError]:
    """`git merge --squash --no-commit branch_name` inside `worktree` and
    report what it left unmerged -- private helper of
    `compose_squash_in_disposable_worktree`. A conflicted merge is NOT an
    error here: it is the caller's data, exactly as it is when the same
    merge runs against the root today."""
    merged = run_argv(
        ("git", "-C", str(worktree), "merge", "--squash", "--no-commit", branch_name)
    )
    if merged.is_err:
        _log.warning("land_compose: squash-merge spawn failed in %s", worktree)
        return Err(LandComposeError.ComposeFailed)
    conflicted = _conflicted_paths(worktree)
    if conflicted.is_err:
        return Err(conflicted.danger_err)
    paths = conflicted.danger_ok
    if merged.danger_ok.returncode != 0 and not paths:
        _log.warning(
            "land_compose: squash-merge of %s failed in %s with no unmerged "
            "path to explain it: %s",
            branch_name,
            worktree,
            excerpt(merged.danger_ok.stderr),
        )
        return Err(LandComposeError.ComposeFailed)
    _log.info(
        "land_compose: squashed %s into disposable worktree %s (%d unmerged)",
        branch_name,
        worktree,
        len(paths),
    )
    return Ok(SquashStage(worktree=worktree, conflicted=paths))


# frob:ticket T-3107
# frob:tests tests/unit/test_land_compose.py::TestDisposableSquashWorktree.test_clean_squash_reports_no_conflicts  # noqa: E501
# frob:tests tests/unit/test_land_compose.py::TestDisposableSquashWorktree.test_conflicting_squash_reports_the_conflicted_paths  # noqa: E501
# frob:tests tests/unit/test_land_compose.py::TestDisposableSquashWorktree.test_root_worktree_untouched_by_clean_squash  # noqa: E501
# frob:tests tests/unit/test_land_compose.py::TestDisposableSquashWorktree.test_root_worktree_untouched_by_conflicted_squash  # noqa: E501
# frob:ticket T-3163
# frob:doc \
# docs/modules/tickets-landing.md#frobtickets_land_compose----disposable-worktree-three\
# -way-squash-compose-t-3107
# frob:tests tests/test_ticket_land.py::TestSquashSpliceLedgerChurn.test_concurrent_write_between_squash_and_splice_survives_land  # noqa: E501
@contextmanager
def compose_squash_in_disposable_worktree(
    repo: Path, base_commit: str, branch_name: str
) -> Iterator[Result[SquashStage, LandComposeError]]:
    """Run a REAL three-way `git merge --squash --no-commit` of
    `branch_name` onto `base_commit` inside a disposable `git worktree`,
    yielding the prepared worktree and whatever git left unmerged; the
    worktree is always removed on exit. `repo`'s own working tree, index
    and HEAD are never touched.

    WHY a worktree rather than the scratch-index plumbing
    `compose_tree_out_of_tree` uses: that primitive is diff-and-apply, so
    it has exactly two outcomes (applies / `ComposeFailed`) and cannot
    classify a conflicted path or take one side per path. The land's
    squash stage needs true three-way semantics, because
    `_auto_resolve_out_of_scope_conflicts` resolves out-of-scope conflicts
    by keeping `ours` (T-0479), union-merges registered zones (T-1002) and
    elementwise-max-merges the coverage lock (T-1434) -- all per-path
    decisions over an unmerged index. `git merge-tree --write-tree` would
    give that out-of-tree, but it needs git 2.38+ and this repo's floor is
    lower, so a disposable worktree is the only mechanism that keeps the
    real merge semantics off the shared root (the same technique T-3095's
    `_apply_release_bump_out_of_tree` already uses).

    Check out at the land's `pre_land_tip`, never at an already-composed
    commit: T-3095 established that checking out the composed commit
    breaks `_apply_release_bump`'s own `_verified_reset_root` unwind
    invariant.

    A conflicted merge yields `Ok` with a non-empty
    `SquashStage.conflicted`, not an `Err` -- resolution is the caller's
    job and is deliberately unchanged by this primitive.

    T-3163: held under `repo`'s `ledger_lock` for this generator's ENTIRE
    lifetime -- from before the squash-merge runs, across the whole
    `yield` (i.e. everything the caller does with the composed stage:
    resolve conflicts, splice the ledger, bump the version, rebuild
    natives, sync gate rules, run an optional pre-commit sweep, fold,
    CAS-publish, resync `repo`), through worktree teardown. Before this
    fix, NOTHING serialized this whole span against a concurrent single-
    ticket ledger write: T-1036's `ledger_lock` was only ever acquired
    deep inside the pipeline, well after the squash-merge (which is what
    this function's own injected-hook test point fires on), so a sibling
    `new_ticket()` routinely won the lock, read `repo`'s still-pre-land
    tickets.md, appended its own ticket, and committed straight back
    BEFORE this land ever reached its own first `ledger_lock`
    acquisition -- landing its pathspec-scoped commit on top of the
    eventually-CAS-published tip and silently REPLACING tickets.md with
    its stale-based version, discarding this land's own ledger splice
    entirely (T-3163's incident). `ledger_lock` is re-entrant per thread
    (its own docstring), so the narrower holds `_squash_and_splice_
    ledger`/`_publish_squash_apply` already take internally nest inside
    this one at no extra cost. `frob.tickets._store` cannot import this
    module (no cycle): `_store` sits below the land pipeline in this
    package's own layering, so a downward import here is safe.
    """
    with ledger_lock(repo), tempfile.TemporaryDirectory(prefix="frob-land-squash-") as (
        scratch
    ):
        worktree = Path(scratch) / "wt"
        added = run_argv(
            (
                "git",
                "-C",
                str(repo),
                "worktree",
                "add",
                "--detach",
                "-q",
                str(worktree),
                base_commit,
            )
        )
        if added.is_err or added.danger_ok.returncode != 0:
            _log.warning(
                "land_compose: could not cut a disposable worktree at %s: %s",
                base_commit,
                excerpt(added.danger_ok.stderr) if added.is_ok else added.danger_err,
            )
            yield Err(LandComposeError.WorktreeSetupFailed)
            return
        try:
            yield _squash_into_worktree(worktree, branch_name)
        finally:
            run_argv(
                ("git", "-C", str(repo), "worktree", "remove", "--force", str(worktree))
            )
            run_argv(("git", "-C", str(repo), "worktree", "prune"))


# frob:ticket T-3107
# frob:tests tests/unit/test_land_compose.py::TestFoldWorktreeIntoCommit.test_folded_commit_contains_both_sides  # noqa: E501
# frob:tests tests/unit/test_land_compose.py::TestFoldWorktreeIntoCommit.test_fold_refuses_while_paths_are_unmerged  # noqa: E501
# frob:doc \
# docs/modules/tickets-landing.md#frobtickets_land_compose----disposable-worktree-three\
# -way-squash-compose-t-3107
def fold_worktree_into_commit(
    repo: Path, worktree: Path, base_commit: str, message: str
) -> Result[str, LandComposeError]:
    """Stage everything in `worktree` and fold it into a commit object with
    `base_commit` as its sole parent, returning the new sha -- the second
    half of the disposable-worktree compose, run once the caller has
    finished every content-mutating stage (conflict resolution, ledger
    splice, REL001 bump, Tier-A sweep) inside that worktree. Publishing the
    result is `publish_ref_cas`'s job; this function moves no ref.

    Returns `Err(ComposeFailed)` while any path is still unmerged, checked
    BEFORE staging: `git add -A` would otherwise RESOLVE each unmerged
    entry by staging the conflict-marker text verbatim, after which
    `git write-tree` happily succeeds and the markers land in a real
    commit. Refusing up front is the only thing standing between an
    unresolved squash and a corrupted landing commit; do not reorder this
    check after the `add`."""
    unmerged = _conflicted_paths(worktree)
    if unmerged.is_err:
        return Err(unmerged.danger_err)
    if unmerged.danger_ok:
        _log.error(
            "land_compose: refusing to fold %s -- %d path(s) still unmerged "
            "(%s); staging them would commit conflict markers",
            worktree,
            len(unmerged.danger_ok),
            ", ".join(unmerged.danger_ok),
        )
        return Err(LandComposeError.ComposeFailed)
    staged = run_argv(("git", "-C", str(worktree), "add", "-A"))
    if staged.is_err or staged.danger_ok.returncode != 0:
        _log.warning("land_compose: staging %s before fold failed", worktree)
        return Err(LandComposeError.ComposeFailed)
    written = run_argv(("git", "-C", str(worktree), "write-tree"))
    if written.is_err or written.danger_ok.returncode != 0:
        _log.warning(
            "land_compose: write-tree in %s failed (unmerged paths?): %s",
            worktree,
            excerpt(written.danger_ok.stderr) if written.is_ok else written.danger_err,
        )
        return Err(LandComposeError.ComposeFailed)
    tree_sha = written.danger_ok.stdout.strip()
    committed = run_argv(
        (
            "git",
            "-C",
            str(repo),
            "commit-tree",
            tree_sha,
            "-p",
            base_commit,
            "-m",
            message,
        )
    )
    if committed.is_err or committed.danger_ok.returncode != 0:
        _log.warning("land_compose: commit-tree failed for folded tree %s", tree_sha)
        return Err(LandComposeError.ComposeFailed)
    new_sha = committed.danger_ok.stdout.strip()
    _log.info(
        "land_compose: folded %s into %s (base=%s)", worktree, new_sha, base_commit
    )
    return Ok(new_sha)


# frob:ticket T-3114
# frob:doc \
# docs/modules/tickets-landing.md#frobtickets_land_compose----post-cas-root-resync-t-31\
# 14
# frob:tests tests/unit/test_land_compose.py::TestResyncRootToPublishedTip.test_unrelated_dirty_path_resyncs_and_is_preserved  # noqa: E501
# frob:tests tests/unit/test_land_compose.py::TestResyncRootToPublishedTip.test_dirty_path_the_land_also_changed_blocks_atomically  # noqa: E501
def resync_root_to_published_tip(
    root: Path, old_tip: str, new_tip: str
) -> Result[None, LandComposeError]:
    """Bring `root`'s INDEX and WORKING TREE from `old_tip` up to the
    `new_tip` a preceding `publish_ref_cas` just made public, without
    touching any ref and without clobbering a sibling agent's uncommitted
    work (T-3114; the mechanism settled in T-3089's body).

    Root's `HEAD` is a symref to the published branch, so the CAS publish
    ALREADY moved `HEAD` as a side effect -- only the index and working
    tree are left describing `old_tip`, which is why `git status` in root
    reports the whole landed changeset as reverted local modifications
    until this runs. `git read-tree -m -u` is a two-tree twoway_merge (the
    same plumbing `git checkout` uses): it updates index+worktree, touches
    no ref (unlike `reset --keep`, which would redundantly re-point the ref
    just published), and is forbidden from being `reset --hard` by T-1740,
    already encoded in `_commit_squash_apply`'s own fallback, because that
    would destroy a sibling's uncommitted work in `root`.

    A sibling holding an uncommitted edit to a path this changeset also
    touches yields `Err(ResyncBlocked)` -- a member distinct from
    `ComposeFailed` because the caller owes the operator different advice
    -- and git refuses ATOMICALLY (`Entry '<p>' not uptodate. Cannot
    merge.`), leaving every file byte-for-byte intact rather than
    half-applied.

    CALLER CONTRACT (post-publish, therefore unwindable by nobody): the
    commit is already public and already correct, so an `Err` here is NOT a
    land failure. Report it loudly with the published sha and the operator
    recovery command, never revert, and attempt this exactly once -- a
    retry only races the same sibling that blocked it."""
    result = run_argv(
        ("git", "-C", str(root), "read-tree", "-m", "-u", old_tip, new_tip)
    )
    if result.is_err:
        _log.error(
            "land_compose: resync spawn failed for %s (%s -> %s); root's index "
            "and working tree still describe the OLD tip",
            root,
            old_tip,
            new_tip,
        )
        return Err(LandComposeError.ComposeFailed)
    if result.danger_ok.returncode != 0:
        _log.error(
            "land_compose: resync of %s BLOCKED (%s -> %s) -- a concurrent "
            "uncommitted edit touches a path this changeset also changed, so "
            "git refused atomically and nothing was applied: %s. The commit is "
            "already public; commit or stash that work, then run: "
            "git -C %s read-tree -m -u %s %s",
            root,
            old_tip,
            new_tip,
            excerpt(result.danger_ok.stderr),
            root,
            old_tip,
            new_tip,
        )
        return Err(LandComposeError.ResyncBlocked)
    _log.info(
        "land_compose: resynced %s from %s to the published tip %s",
        root,
        old_tip,
        new_tip,
    )
    return Ok(None)
