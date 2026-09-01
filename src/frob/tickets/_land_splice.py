import os
import tempfile
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

from typani.result import Err, Ok, Result

from frob.gitio import excerpt, run_argv
from frob.logging import get_logger
from frob.tickets._land_compose import (
    LandComposeError,
)

# frob:ticket T-3629
#: T-3629: `_log` -- `frob refactor split` (T-3596, gaps 3/4) does not
#: carry a moved function's module-level free-variable dependencies, so
#: this module needs its own logger instance rather than inheriting the
#: source module's, matching the `get_logger(__name__)` convention every
#: other module in this package already follows.
_log = get_logger(__name__)


# frob:ticket T-3546
# frob:doc docs/design/land-splice-test-then-impl.md#land-splice-tests-first-then-implementation-t-3546  # noqa: E501
# frob:tests \
# tests/unit/test_land_splice_test_then_impl.py::TestClassifyTestThenImplPaths.test_mix\
# ed_paths_split_into_two_groups
# frob:tests \
# tests/unit/test_land_splice_test_then_impl.py::TestClassifyTestThenImplPaths.test_no_\
# test_paths_returns_none
# frob:tests \
# tests/unit/test_land_splice_test_then_impl.py::TestClassifyTestThenImplPaths.test_no_\
# impl_paths_returns_none
def classify_test_then_impl_paths(
    paths: Sequence[str],
) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
    """T-3546 design (`docs/design/land-splice-test-then-impl.md`): split
    `paths` (a ticket's full changed-path set) into a TEST group and an
    IMPL group using the SAME test-path heuristic `frob.gates.
    _is_test_path` already applies for doc-obligation exemption (under a
    `tests` path segment, or named `test_*`/`*_test.py`), not a second
    independently-invented rule.

    Returns `None` -- the mechanical "no clean split" signal, never a
    fabricated one -- whenever either group would be empty: a ticket that
    touches no test files (docs/chore/pure-refactor) or no non-test files
    (a test-only follow-up) has nothing to split into a tests-then-impl
    pair. Never called from the live land path yet (T-3546's own
    docstring: this ticket lands the design plus this UNWIRED mechanical
    primitive; wiring it into `_fold_publish_and_resync` is a separate,
    owner-gated follow-up ticket, the same "prove it in isolation, wire
    it later" shape T-3088/T-3089 used for `compose_tree_out_of_tree`)."""
    test_paths: list[str] = []
    impl_paths: list[str] = []
    for path in paths:
        parts = PurePosixPath(path).parts
        name = PurePosixPath(path).name
        is_test = (
            "tests" in parts or name.startswith("test_") or name.endswith("_test.py")
        )
        (test_paths if is_test else impl_paths).append(path)
    if not test_paths or not impl_paths:
        return None
    return (tuple(sorted(test_paths)), tuple(sorted(impl_paths)))


def _apply_pathset_diff_to_scratch_index(
    repo: Path,
    diff_base: str,
    patch_source: str,
    pathset: Sequence[str],
    scratch: str,
    env: dict[str, str],
) -> Result[None, LandComposeError]:
    """Diff `diff_base` against `patch_source`, restricted to `pathset`,
    and `git apply --cached` the result into the scratch index
    `env["GIT_INDEX_FILE"]` names -- private split-out of
    `_compose_pathset_commit` (T-2214 length budget), the pathset-scoped
    twin of `_land_compose.py`'s own `_apply_diff_to_scratch_index`
    (duplicated in miniature rather than imported -- see
    `_compose_pathset_commit`'s own docstring for why)."""
    diffed = run_argv(
        ("git", "-C", str(repo), "diff", diff_base, patch_source, "--", *pathset)
    )
    if diffed.is_err:
        _log.warning(
            "land_splice: diff %s..%s (pathset) failed", diff_base, patch_source
        )
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
            "land_splice: apply --cached (pathset) failed: %s",
            excerpt(applied.danger_ok.stderr) if applied.is_ok else applied.danger_err,
        )
        return Err(LandComposeError.ComposeFailed)
    return Ok(None)


def _write_and_commit_pathset_index(
    repo: Path, parent_commit: str, message: str, env: dict[str, str]
) -> Result[str, LandComposeError]:
    """`git write-tree` + `git commit-tree` against the scratch index
    `env["GIT_INDEX_FILE"]` names, parented on `parent_commit` -- private
    split-out of `_compose_pathset_commit` (T-2214 length budget)."""
    written = run_argv(("git", "-C", str(repo), "write-tree"), env=env)
    if written.is_err or written.danger_ok.returncode != 0:
        _log.warning("land_splice: write-tree failed for pathset commit")
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
            parent_commit,
            "-m",
            message,
        )
    )
    if committed.is_err or committed.danger_ok.returncode != 0:
        _log.warning("land_splice: commit-tree failed for tree %s", tree_sha)
        return Err(LandComposeError.ComposeFailed)
    return Ok(committed.danger_ok.stdout.strip())


def _compose_pathset_commit(
    repo: Path,
    diff_base: str,
    patch_source: str,
    pathset: Sequence[str],
    index_base: str,
    parent_commit: str,
    message: str,
) -> Result[str, LandComposeError]:
    """One out-of-tree compose step, private to
    `compose_test_then_impl_commits` (T-3546): seed a scratch index from
    `index_base`'s tree, `git apply --cached` the portion of `git diff
    diff_base patch_source` touching only `pathset`
    (`_apply_pathset_diff_to_scratch_index`), then `write-tree` +
    `commit-tree` parented on `parent_commit`
    (`_write_and_commit_pathset_index`). Same `GIT_INDEX_FILE`-scoped,
    worktree-untouched mechanism `_land_compose.py`'s
    `_apply_diff_to_scratch_index`/`compose_tree_out_of_tree` already use
    -- duplicated in miniature here (rather than imported) because those
    are restricted-scope for T-3546 (out of `src/frob/tickets/_land_
    compose.py`'s declared scope for this ticket; see the design doc's
    Rollout plan for why wiring, including any real code-sharing pass,
    stays a follow-up ticket's concern)."""
    with tempfile.TemporaryDirectory(prefix="frob-land-splice-") as scratch:
        index_file = Path(scratch) / "index"
        env = dict(os.environ)
        env["GIT_INDEX_FILE"] = str(index_file)

        read_tree = run_argv(("git", "-C", str(repo), "read-tree", index_base), env=env)
        if read_tree.is_err or read_tree.danger_ok.returncode != 0:
            _log.warning("land_splice: read-tree %s failed", index_base)
            return Err(LandComposeError.ComposeFailed)

        applied = _apply_pathset_diff_to_scratch_index(
            repo, diff_base, patch_source, pathset, scratch, env
        )
        if applied.is_err:
            return Err(applied.danger_err)

        return _write_and_commit_pathset_index(repo, parent_commit, message, env)


# frob:ticket T-3546
# frob:doc docs/design/land-splice-test-then-impl.md#land-splice-tests-first-then-implementation-t-3546  # noqa: E501
# frob:tests \
# tests/unit/test_land_splice_test_then_impl.py::TestComposeTestThenImplCommits.test_tw\
# o_commits_chain_correctly
# frob:tests \
# tests/unit/test_land_splice_test_then_impl.py::TestComposeTestThenImplCommits.test_fi\
# nal_tree_matches_full_squash
def compose_test_then_impl_commits(
    repo: Path,
    pre_land_tip: str,
    patch_source: str,
    test_paths: Sequence[str],
    impl_paths: Sequence[str],
    test_message: str,
    impl_message: str,
) -> Result[tuple[str, str], LandComposeError]:
    """T-3546 design (`docs/design/land-splice-test-then-impl.md`,
    "The split algorithm"): compose TWO commits out-of-tree instead of
    `compose_tree_out_of_tree`'s one -- a `test_paths`-only commit
    parented on `pre_land_tip`, then an `impl_paths`-only commit parented
    on THAT commit's own sha, never on `pre_land_tip` again. Neither
    compose step touches `repo`'s checked-out working tree or `HEAD`
    (same `GIT_INDEX_FILE`-scoped mechanism as
    `compose_tree_out_of_tree`); publishing (a single `publish_ref_cas`
    straight from `pre_land_tip` to the SECOND commit's sha) is this
    function's caller's job, not this function's -- exactly like
    `compose_tree_out_of_tree`/`publish_ref_cas` stay two separate calls
    today. UNWIRED: no caller in the live land path yet (see this
    ticket's own Done report / the design doc's Rollout plan)."""
    test_result = _compose_pathset_commit(
        repo,
        pre_land_tip,
        patch_source,
        test_paths,
        pre_land_tip,
        pre_land_tip,
        test_message,
    )
    if test_result.is_err:
        return Err(test_result.danger_err)
    test_sha = test_result.danger_ok

    impl_result = _compose_pathset_commit(
        repo,
        pre_land_tip,
        patch_source,
        impl_paths,
        test_sha,
        test_sha,
        impl_message,
    )
    if impl_result.is_err:
        return Err(impl_result.danger_err)
    impl_sha = impl_result.danger_ok

    _log.info(
        "land_splice: composed test-then-impl pair %s -> %s (base=%s "
        "patch_source=%s) without touching the worktree",
        test_sha,
        impl_sha,
        pre_land_tip,
        patch_source,
    )
    return Ok((test_sha, impl_sha))
