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
from pathlib import Path

from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.gitio import excerpt, run_argv
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:ticket T-3088
# frob:doc \
# docs/modules/tickets-landing.md#frobticketslandcompose----out-of-tree-compose--cas-pu\
# blish-primitive-t-3088
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
        "the target ref moved since expected_old_sha was captured "
        "(CAS lost the race)"
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
# docs/modules/tickets-landing.md#frobticketslandcompose----out-of-tree-compose--cas-pu\
# blish-primitive-t-3088
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
# docs/modules/tickets-landing.md#frobticketslandcompose----out-of-tree-compose--cas-pu\
# blish-primitive-t-3088
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
