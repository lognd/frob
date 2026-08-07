## Done report

Changed:
- src/frob/testing/_collect.py::collect_python_tests -- now unions the
  outer-tree `pytest --collect-only` pass with a separate collect-only
  pass run inside every nested `language = "python"` `[[test.runner]]
  cwd` (own interpreter/deps), node ids rerooted onto that cwd so they
  read as the same root-relative `path::qualname` symref
  `frob:tests` directives and the graph already use.
- src/frob/testing/_collect.py::_run_collect_only (renamed param
  `root` -> `cwd`; now callable against any directory, not just the repo
  root)
- src/frob/testing/_collect.py::_reroot_node_ids (new)
- src/frob/testing/_collect.py::_python_runner_cwds (new)
- src/frob/testing/_collect.py::_is_nested_python_runner (new)
- src/frob/testing/_collect.py::_collect_nested_python (new)
- src/frob/testing/_collect.py::_content_key -- cache key now also hashes
  test files under every nested runner cwd, so a change inside a nested
  project invalidates the cache even when `[graph].exclude` keeps that
  directory out of the outer tree's own test-file walk.

Also fixed (in scope, `tickets.md`): T-0317 and T-0318's `scope:` fields
were each stored as a single YAML list item holding a comma-joined string
(`- src/frob/testing/**,tests/**,docs/**,tickets.md`) instead of one glob
per list item -- `frob.gates._scope_covers` matches each scope entry with
a literal `fnmatch`, so the joined string never matched any real file and
SCOPE001 fired against every file in this very diff. Split both into
proper multi-item lists (discovered as a hard blocker while finishing
this ticket, not a drive-by -- `frob check --delta` could not go clean
without it).

Evidence:
- tests/test_testing.py::TestCollectPythonTestsNestedRunner::test_nested_test_runner_cwd_is_collected_and_rerooted
  (stubs `run_argv`, asserts a `cwd="nested"` `[[test.runner]]` entry gets
  its own `pytest --collect-only` spawn and its node ids come back
  rerooted as `nested/tests/test_inner.py::test_inner`, unioned with the
  outer tree's `tests/test_outer.py::test_outer`)
- tests/test_testing.py::TestCollectPythonTestsNestedRunner::test_missing_nested_runner_dir_degrades_to_empty_not_err
  (a `[[test.runner]] cwd` naming a directory that does not exist degrades
  to empty rather than erroring the whole collection)
- tests/test_testing.py::TestCollectPythonTests::test_parses_node_ids_and_caches_on_content_hash
  (pre-existing test, re-verified green after the `_run_collect_only`
  signature change and `_content_key` rework)
- `uv run pytest tests/test_testing.py -k CollectPythonTests -q` -> 3
  passed
- `uv run pytest tests/test_testing.py tests/test_gates.py -q` (minus 6
  pre-existing `strata_core`/`frob_core`-native-unavailable failures,
  confirmed identical on a `git stash`d baseline of this same worktree)
  -> all remaining green
- `uv run ruff check` / `uv run ruff format --check` clean on
  `src/frob/testing/_collect.py` and `tests/test_testing.py`
- `uv run frob check --delta --ticket T-0317 --json` (after `frob ticket
  sweep T-0317` against the corrected scope) -> `gates: 0/90 new, 0
  errors, 0 warnings, 215 waived`
- `make coverage` fails on this worktree, but identically on a
  `git stash`d baseline of the same worktree (strata_core-native-parsing
  system/integration tests -- T-0133-class environment gap, not caused
  by this change)
- `git diff main --diff-filter=D --stat` empty (deletion-filter clean,
  after re-merging main mid-session -- see below)

Worktree note: `git merge main` at session start reported "Already up to
date" against a stale local `main` ref (tip `a63ab57`); partway through
this ticket, `git diff main --stat` unexpectedly showed unrelated
deletions in `src/frob/gates/__init__.py` and
`tests/system/test_cli_check.py`, which turned out to be T-0314 landing
on `main` (tip `976a618`) after this worktree's initial merge. Re-ran
`git merge main` (via `git stash` / merge / `git stash pop`, auto-merged
clean) before finishing -- per the playbook's deletion-filter land rule.

Filed: none (the scope-field fix above was done in-place under this
ticket's own `tickets.md` scope grant, not filed separately)

Gates: `frob check --delta --ticket T-0317` clean (0 new errors/warnings)
