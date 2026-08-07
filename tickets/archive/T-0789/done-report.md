## Done report

## Done report

Changed:
  Makefile::upload (recipe only -- `uv lock` now runs after the version
  bump and `uv.lock` is committed alongside `pyproject.toml`)
  tests/test_makefile_lock_sync.py::test_upload_relocks_after_version_bump (new)
  tests/test_makefile_lock_sync.py::test_upload_commits_uv_lock_with_pyproject (new)

Evidence:
  tests/test_makefile_lock_sync.py::test_upload_relocks_after_version_bump
  tests/test_makefile_lock_sync.py::test_upload_commits_uv_lock_with_pyproject
  (both bound via `frob ticket evidence T-0789 ...`)
  Direct run: `uv run --frozen pytest tests/test_makefile_lock_sync.py -q -p no:cacheprovider` -> 2 passed

Filed: none

Gates: `uv run frob check --ticket T-0789` clean (0 errors; gate:PRE cleared
by re-running `frob ticket sweep T-0789` after the scope expansion for the
new test file). `uv run frob test --base main` showed pre-existing
unrelated failures (native-extension/env-fragile tests: test_doctor
natives cases, test_cli_native_missing, test_export_golden,
test_selfconform, sys_audit, gitless git-ls-files edge case) -- none touch
Makefile/pyproject.toml/uv.lock/tests/test_makefile_lock_sync.py and match
the playbook's documented worktree-natives-artifact class, not a
regression from this change.

Root cause and fix: `make upload` bumped `pyproject.toml`'s version line
via `scripts/bump_version.py` but never re-ran `uv lock`, so the commit it
produced always shipped with `uv.lock`'s own recorded frob version one
step behind. Every worktree cut from that commit then had `uv run` try to
reconcile the two on invocation, producing a working-tree `uv.lock` diff
no agent hand-edited, tripping SCOPE001 unless manually `git checkout --
uv.lock`ed first. Running `uv lock` immediately after the bump and
`git add`ing `uv.lock` into the same commit (option (c) from the ticket
body) closes the gap at the source -- a worktree cut from a post-fix
version-bump commit starts with an already-synced lock. (T-0793, landed
separately, already covers the analogous case inside `frob ticket land`'s
own release-bump step; this ticket was the `make upload` manual-release
counterpart.)

### Changed
(no changed files detected)

### Evidence
- `tests/test_makefile_lock_sync.py::test_upload_relocks_after_version_bump` (pytest node id, verified passing when recorded)
- `tests/test_makefile_lock_sync.py::test_upload_commits_uv_lock_with_pyproject` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 1012 warning(s), 220 waived
- error-findings: none (measured, zero errors)
