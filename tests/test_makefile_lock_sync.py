"""T-0789: `make upload`'s version bump must re-lock and commit `uv.lock`.

Without this, a version bump lands with `pyproject.toml` changed but
`uv.lock` left stale (still recording the PREVIOUS frob version). Every
`uv run` invocation in every worktree cut from that commit then tries to
reconcile the two, leaving a silent working-tree `uv.lock` diff no agent
hand-edited -- SCOPE001 fires on it unless someone remembers to
`git checkout -- uv.lock` first (the recurring coordinator-land friction
this ticket exists to remove).

T-3140: the `upload:` Makefile recipe was rewritten to a single
`uv run frob release publish` call (T-2242) -- no more `bump_version.py`/
`frob release sync`/hand-rolled `git add` text in the recipe itself for
these tests to statically parse. MEASURED (src/frob/release/_publish.py,
T-3140 triage): the T-0789 property is still true, just fully inlined --
`publish()` runs `bump_patch_version` -> `stamp` -> `_sync_derived_
artifacts` (which runs `uv lock` after rewriting the version) -> `git add
<_COMMIT_FILES>` (which includes both `pyproject.toml` and `uv.lock`) ->
`git commit`, in that order. These tests now assert that shape directly
against `_publish.py`'s own module rather than parsing Makefile text that
no longer contains it.
"""

from __future__ import annotations

import inspect

from frob.release import _publish


def test_upload_relocks_after_version_bump():
    # frob:tests tests/test_makefile_lock_sync.py::test_upload_relocks_after_version_bump kind="unit"  # noqa: E501
    # T-3140: `frob release publish` (src/frob/release/_publish.py)
    # supersedes the old recipe's bare `uv lock` step -- assert its own
    # `_sync_derived_artifacts` (the step that runs `uv lock`) is composed
    # AFTER the version bump in `publish`'s own source order.
    source = inspect.getsource(_publish.publish)
    bump_idx = source.index("bump_patch_version")
    sync_idx = source.index("_sync_derived_artifacts")
    assert bump_idx < sync_idx, (
        "_sync_derived_artifacts (which relocks uv.lock via `uv lock`) must "
        "be called AFTER bump_patch_version, not before"
    )
    sync_source = inspect.getsource(_publish._sync_derived_artifacts)
    assert '"uv", "lock"' in sync_source, (
        "_sync_derived_artifacts no longer re-locks uv.lock -- the T-0789 "
        "property this ticket exists to hold has regressed"
    )


def test_upload_commits_uv_lock_with_pyproject():
    # frob:tests tests/test_makefile_lock_sync.py::test_upload_commits_uv_lock_with_pyproject kind="unit"  # noqa: E501
    assert "pyproject.toml" in _publish._COMMIT_FILES
    assert "uv.lock" in _publish._COMMIT_FILES
