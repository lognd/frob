## Done report

Changed:
- src/frob/app/sys_runner.py::_resolve_design_root (new)
- src/frob/app/sys_runner.py::_repo_root_for (new)
- src/frob/app/sys_runner.py::_run_plan (uses _resolve_design_root)
- src/frob/app/sys_runner.py::_run_doc (uses _resolve_design_root)
- src/frob/app/sys_runner.py::_run_audit (uses _resolve_design_root)

Repro: `uv run frob sys audit design/frob.strata` silently joined
`design_dir` onto the *file* path, producing a nonexistent
`<file>/design`, finding zero models, and exiting 0 with "no design
models under .../design/frob.strata/design" -- a vacuous PASS. Fixed
by validating `cfg.sys_path` up front in `plan`/`doc`/`audit` (all three
shared the identical bug via the same `root = (cfg.sys_path or
Path(".")).resolve()` line): a file argument now exits 1 with
`sys <cmd>: <path> is a file; pass the repo root directory instead
(design files live under its [strata].design_dir, e.g. \`frob sys
<cmd> <repo-root>\`)`, matching the sys-path convention documented in
T-0167 (plan/doc/audit take the repo root; export takes a single
.strata file).

Evidence:
- tests/system/test_cli_sys_audit.py::TestSysAuditCli::test_file_arg_fails (new regression test, T-0163)
- tests/system/test_cli_sys_audit.py::TestSysAuditCli::test_clean_model_exits_zero
- tests/system/test_cli_sys_audit.py::TestSysAuditCli::test_undischarged_capability_exits_nonzero_with_named_gap
- tests/system/test_cli_sys_audit.py::TestSysAuditCli::test_no_design_dir_is_a_noop

Filed: none

Gates: `uv run frob check --ticket T-0163` -- 0 errors, 262 warnings
(WARN, not FAIL). One pre-existing warning remains and is out of
T-0163's scope: TEST006 "no coverage stamp found" -- this worktree has
never run `make coverage`/produced `coverage.xml`; unrelated to this
fix. `uv run frob test --base main` -- PASS, exit=0 (5 selected
tests including the new regression test). `uv run pytest
tests/system/test_cli_sys_audit.py -v` -- 4 passed.
