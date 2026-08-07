## Done report

Changed:
- src/frob/gates/_fmt_directives.py::_read_source_for_format (new)
- src/frob/gates/_fmt_directives.py::_write_formatted (new)
- src/frob/gates/_fmt_directives.py::_relpath_for_change (new)
- src/frob/gates/_fmt_directives.py::_format_one_path (refactored)
- src/frob/natives/_build.py::_resolve_buildable_crate (new)
- src/frob/natives/_build.py::_build_one_crate (refactored + frob:waive ARCH103)

Re-measurement (chunked `frob check --only gates-native --json`, natives
rebuilt, post-merge with main): the 2 findings named in this ticket's
dispatch (`format_paths`/`build_natives`) had already moved, per T-0976's
same-day refactor, into their newly-extracted per-item helpers
`_format_one_path` and `_build_one_crate`. Both resolved:

- `_format_one_path`: extracted the read half
  (`_read_source_for_format`), the write half (`_write_formatted`), and
  the relative-path-display half (`_relpath_for_change`). The remaining
  `_format_one_path` body no longer contains a direct I/O-capability call
  (write delegated) alongside its decision points, so it no longer
  matches ARCH103's I/O+format+2-decisions shape at all -- confirmed
  0 findings for this symbol in a fresh gates-native re-run, no waiver
  needed.
- `_build_one_crate`: extracted the skip-check half
  (`_resolve_buildable_crate`, the non-rust/no-crate-dir silent-skip
  logic). What remains is a single guarded-subprocess run-and-report job
  (spawn maturin, classify pass/fail, log each transition) -- the same
  cohesive shape T-0977 already waived for this module's sibling
  wrappers (`_cargo_env`, `_run_ctest_list`) and `frob.exec`'s `_run_npx`.
  Added a reasoned `frob:waive ARCH103` citing that precedent rather than
  mechanically splitting further (which would just relocate the same
  cohesive concern to a same-shaped new function).

Promotion: NOT executed this round. A fresh, unscoped
`frob check --only gates-native --json` turned up 2 OTHER live unwaived
ARCH103 findings outside this ticket's declared scope --
`src/frob/app/perf_runner.py::_collect_stacks_from_file` and
`src/frob/gates/__init__.py::_open_process_pool` -- not part of T-0977's
original 24-finding hand-off (which only carried the 2 sites this ticket
just resolved), so these appear to be newly-introduced mixed-concern
shapes from other recent changes to those 2 files. Promoting
`[gates.severity] ARCH103 = "error"` with these live would immediately
red `main`, which this ticket's own scope (limited to
`src/frob/gates/_fmt_directives.py`/`src/frob/natives/_build.py`) does
not permit touching. `[gates.severity] ARCH103` stays `"warning"` in
frob.toml, matching the same reasoned non-promotion precedent T-0977 set
for ARCH102.

Evidence: tests/test_gates_fmt_directives.py::TestFormatPaths::test_check_mode_reports_without_writing,
tests/test_gates_fmt_directives.py::TestFormatPaths::test_write_mode_rewrites_file,
tests/unit/test_natives_build.py::TestBuildNatives::test_builds_declared_rust_natives,
tests/unit/test_natives_build.py::TestBuildNatives::test_skips_native_with_no_matching_crate_dir,
tests/unit/test_natives_build.py::TestBuildNatives::test_skips_non_rust_native
(all pass; full module runs of both test files pass clean, 56 tests
total). `frob check --only lint`/`--only static` both 0 errors on the
touched files.

Filed: T-0990 -- "ARCH103: resolve 2 newly-live findings
blocking promotion (perf_runner/_open_process_pool)", scoped to
src/frob/app/perf_runner.py, src/frob/gates/__init__.py, frob.toml
(renumbered to a real T-#### id at land time per repo convention).

Gates: `frob check --only gates-native` clean for both in-scope
symbols (0 unwaived ARCH103 findings in
src/frob/gates/_fmt_directives.py / src/frob/natives/_build.py);
`frob check --only lint` and `--only static` both 0 errors.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates_fmt_directives.py::TestFormatPaths::test_check_mode_reports_without_writing` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestFormatPaths::test_write_mode_rewrites_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestBuildNatives::test_builds_declared_rust_natives` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestBuildNatives::test_skips_native_with_no_matching_crate_dir` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestBuildNatives::test_skips_non_rust_native` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 2 error(s), 4869 warning(s), 307 waived
- error-findings: DRIFT001@src/frob/gates/_fmt_directives.py, PRE001@tickets/T-0979
