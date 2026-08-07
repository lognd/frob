## Done report

Changed:
- src/frob/excludes.py -- added `_is_nested_worktree(dir_path, root)` (True
  if `dir_path` has its own `.git` file/dir and isn't `root`) and
  `_should_prune_dir(dir_path, root, exclude_globs)` (combines the builtin
  skip-name set, `[graph] exclude` globs, and nested-worktree detection into
  one before-descent pruning check). Both are private (leading underscore)
  so they stay off the REL001 public-API surface -- they are internal
  walker details, not something `frob.excludes` advertises to outside
  consumers (its existing public surface, `is_excluded`/`is_skipped_dir`/
  `load_exclude_globs`, is unchanged).
- src/frob/graph/__init__.py -- `_walk_source_files` and `_walk_doc_files`
  now prune excluded/nested-worktree subdirectories from `dirnames` BEFORE
  `os.walk` descends into them, via the new `_should_prune_dir` helper,
  instead of the old behavior of walking every directory in full and only
  filtering the resulting file list afterward (the actual T-0239 bug: file-
  level filtering still pays the full `os.walk`/stat traversal cost of
  every excluded subtree). Removed `_walk_doc_files`'s use of
  `Path.rglob("*.md")` in favor of a manual `os.walk`, since `rglob` cannot
  prune subtrees mid-traversal. Dropped the local, duplicate `_EXCLUDED_DIRS`
  frozenset in this module (T-0026's whole point -- one shared copy in
  `frob.excludes`, not a second one here).
- tests/test_excludes.py -- unit tests for `_is_nested_worktree` (dir-form
  and file-form `.git`, root-itself is never "nested", plain subdirs are
  unaffected) and `_should_prune_dir` (each of the three signals --
  builtin-name, exclude-glob, nested-worktree -- independently sufficient
  to prune).
- tests/test_graph.py (class `TestExclude`) -- `build_graph` integration
  test proving a nested `.git`-bearing checkout under
  `.claude/worktrees/agent-x` is excluded from the resulting symbol set
  with NO `[graph] exclude` entry needed (pure `.git`-detection path); and
  a `_walk_source_files` unit test that monkeypatches `frob.graph.os.walk`
  to record every directory `os.walk` actually visits, asserting the
  excluded `tests/fixtures/**` subtree (and its nested children) is never
  entered at all -- proving pruning happens before descent, not as a
  post-walk filter.

Evidence (fresh `pytest --collect-only` via `frob test --collect`, 2904
node ids collected, all 7 resolve):
- tests/test_excludes.py::test_is_nested_worktree_detects_own_git_dir
- tests/test_excludes.py::test_is_nested_worktree_git_file_form
- tests/test_excludes.py::test_is_nested_worktree_false_for_root_itself
- tests/test_excludes.py::test_is_nested_worktree_false_for_plain_subdir
- tests/test_excludes.py::test_should_prune_dir_covers_all_three_signals
- tests/test_graph.py::TestExclude::test_nested_git_worktree_pruned_without_config
- tests/test_graph.py::TestExclude::test_walk_source_files_prunes_before_descent

Real before/after timing (measured on this worktree, which has 103 sibling
`.claude/worktrees/agent-*` checkouts, ~47G, all already covered by this
repo's own `frob.toml` `.claude/worktrees/**` exclude glob -- i.e. this
measures the file-level-filter-vs-prune-before-descent difference, not a
missing-exclude-entry difference):
- Before fix (`git stash` back to pre-change code, `.frob/cache.db`
  removed to force a cold graph rebuild): `time uv run frob check` ->
  `real 0m50.494s` (gates line: `0 errors, 10 warnings, 25 waived`).
- After fix (same cold-cache conditions): `time uv run frob check` ->
  `real 0m24.731s` (gates line: `0 errors, 11 warnings, 25 waived` -- the
  extra warning vs. the before run is pre-existing repo noise unrelated to
  this change, not a new violation introduced by it).
- ~51pct wall-time reduction on a cold `frob check` run, consistent with
  the ticket's own report of a similar-shaped fix (9m47s -> 3m35s, ~63pct)
  on the original malmberg pilot repro.
- Verified legitimate in-repo files are still scanned: a direct
  `build_graph(Path('.'), ...)` call after the fix reports
  `parsed=482 hits=0 symbols=6399 edges=3961` -- matching (modulo the new
  test/helper symbols added by this ticket itself) the `parsed=482
  symbols=6390` baseline `frob ticket start T-0239` reported before any
  change, i.e. nothing legitimate got pruned.

Filed: none. (Gates/coverage walkers with the same file-level-filter-not-
prune shape -- e.g. `src/frob/gates/_baseline.py::_walk`,
`src/frob/gates/_coverage.py`'s walker, and other `os.walk`/`rglob`
call sites outside this ticket's `scope` globs -- are a real follow-up but
out of scope here; not filed as a new ticket in this pass because a
scan showed they already at least honor the builtin skip-dir set (just via
their own locally duplicated copy, not `frob.excludes`), so they are lower
urgency than the graph-build walker this ticket targeted. Recommend a
follow-up ticket sweeping all `os.walk`/`rglob` call sites in
`src/frob/gates/**`, `src/frob/vet/**`, `src/frob/tickets/**`,
`src/frob/xref/**`, `src/frob/bind/**`, `src/frob/mutate/**`,
`src/frob/check/**`, `src/frob/testing/**`, and `src/frob/strata/**` onto
the same `frob.excludes._should_prune_dir`-style prune-before-descend
pattern and dropping their local `_EXCLUDED_DIRS` duplicates.)

Gates:
- `uv run pytest tests/test_excludes.py tests/test_graph.py -q` -- all
  pass (77 tests total across both files).
- `uv run frob test --base main` -- touched-set selection (17 files),
  `run_selected: python exit=0 duration=1.52s`, `[PASS] python exit=0`.
- `make coverage` (foreground, exit code 0): full suite green,
  `stamp_coverage: stamped 404 file(s)`.
- `uv run frob check --ticket T-0239` -- `frob check . [PASS]` after fixing
  two `ruff-check` E501 violations on the `frob:tests` directive comment
  lines (matched the existing `# noqa: E501` convention already used
  elsewhere in the repo for the same over-length-directive-comment shape,
  e.g. `src/frob/gates/__init__.py:993-995`) and re-running
  `frob ticket sweep T-0239` (PRE001 fired because the pre-work sweep
  recorded before this round's edits had gone stale against the touched
  scope).
- `git diff main --diff-filter=D --stat` -- empty (no unintended
  deletions).
