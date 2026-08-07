## Done report

Root cause confirmed as above by direct reproduction: wrote a tmp
workspace root `Cargo.toml` ([workspace] only) plus two member crates and
called `_find_crates` directly -- pre-fix it returned `[root]` only;
post-fix it returns the two member dirs and not the root.

Fix (`src/frob/testing/_collect.py`):
1. `_classify_manifest(path)` parses a `Cargo.toml` with `tomllib`,
   returning `(has_package, has_workspace)`, or `None` if the file cannot
   be read/parsed.
2. `_find_crates` now, per directory holding a `Cargo.toml`: appends the
   dir iff `has_package`; keeps descending (does not clear `dirnames`)
   iff `has_workspace`; a manifest with neither table, or one that fails
   to parse, falls back to the OLD behavior (append + prune) with a
   logged warning, so degenerate cases do not regress. `_EXCLUDED_DIRS`
   pruning is unchanged. Docstring updated to state the workspace rule
   (previously claimed "no nested-manifest workspaces here").
3. Integration-test collection: refactored `_run_cargo_list` into a
   shared `_run_cargo_test_list(crate_dir, target_argv)` (same env
   overlay/timeout/error handling, argv is the only difference); added
   `_find_integration_test_files(crate_dir)` (sorted `tests/*.rs` under
   one crate) and `_integration_module_path_to_symref(root, crate_dir,
   test_file, module_path)` (symref anchored at `tests/<stem>.rs`, whole
   module path as qualname for the flat case -- documented as a known
   approximation for a `tests/<stem>/mod.rs`-style submodule tree, which
   is not resolved file-by-file the way `src/` is).
   `_collect_rust_uncached` now also runs `cargo test --test <stem> --
   --list` for each crate's integration binaries and folds their node
   ids in. A crate with no `tests/` dir skips cleanly (empty list).
4. `_rust_content_key` needed no change: it already `rglob("*.rs")`s each
   crate dir, which includes `tests/*.rs`; re-verified it still
   invalidates correctly with the new `_find_crates` (workspace member
   discovery feeds the same function).

Tests added (`tests/test_testing.py`):
- `TestFindCrates`: `test_virtual_workspace_root_descends_to_members`
  (root not returned, both members are), `test_root_package_with_nested_workspace_members`
  (root has both tables -> root AND member both returned),
  `test_plain_single_crate_unchanged` (single crate at root, unaffected),
  `test_unparseable_manifest_keeps_old_behavior_and_warns` (garbage TOML
  at root -> old append+prune behavior, warning logged, asserted via
  `caplog`).
- `TestIntegrationTestCollection`: `test_integration_module_path_to_symref_flat_case`
  (direct symref check against a fake `tests/foo.rs`),
  `test_find_integration_test_files_lists_and_skips_missing_dir` (glob
  + empty-dir case).

All 6 new tests pass; full repo suite `uv run pytest tests/ -q -n auto`
green (no failures) after the change. One incidental `ruff-format` diff
in `tests/test_testing.py` (line-wrap only) was applied via
`uv run ruff format`.

Gate: `uv run frob check` (foreground, full run) -- **0 errors, 12
warnings, 214 waived**; `ruff-format` now `pass` (was the only FAIL
before the format fix); no new TEST001/TEST002/TEST003 introduced by
this change (the module's own two public functions,
`collect_python_tests` and `collect_rust_tests`, already carry
`frob:doc`/`frob:tests` edges, unchanged by this diff's scope).

Scope discipline: touched only `src/frob/testing/_collect.py` and
`tests/test_testing.py`, both inside the ticket's declared scope.
`git diff main --diff-filter=D --stat` is empty. Two unrelated
`Cargo.lock` version-bump diffs (0.1.0 -> 0.2.0, produced by running
`cargo test` during the gate's own rust-collection pass) surfaced in
`git status` and were reverted (`git checkout -- frob-core/Cargo.lock
strata-core/Cargo.lock`) as out of scope, not part of this fix.

Verification against the real bug repo (lithos, READ-ONLY, after `uv
tool upgrade frob`): see the coordinator-facing final report for the
before/after TEST001 counts and sample crate-prefixed node ids from
`.frob/cargo-collect.json`.
