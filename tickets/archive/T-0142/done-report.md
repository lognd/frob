## Done report

Changed:
- pyproject.toml::[project].dependencies (added `ruff>=0.8`, `ty>=0.0.1a8`, matching the existing dev-group pins -- no upper bound, consistent with every other entry in `dependencies`)
- src/frob/process/parsers/common.py::tool_unavailable_result (new shared helper: a missing binary -> a FAILING ToolResult, exit_code=1, one error Diagnostic `"tool unavailable: <binary> -- install it or use make install-tool"`)
- src/frob/check/_python.py::_run_ruff (now catches FileNotFoundError around `ruff check`, returns two typed-failure ToolResults for ruff-check + ruff-format)
- src/frob/check/_python.py::_ruff_format_result (catches FileNotFoundError around `ruff format --check`)
- src/frob/check/_python.py::_run_ty (catches FileNotFoundError around `ty check`; return type narrowed `ToolResult | None` -> `ToolResult` since the None-on-missing-tool silent-skip is gone)
- src/frob/check/_native.py::_cmake_configure, _run_cmake_build, _run_clang_tidy_cmake, _run_clang_format, _run_ctest, _run_cargo, _run_cargo_fmt_check, _run_cargo_valgrind, _run_cargo_test (each now catches FileNotFoundError -> tool_unavailable_result; None is still returned only for genuine "nothing to check" skips -- no compile db, no sources, no build dir, no test binary -- never for a missing tool)
- src/frob/check/_ts.py::_missing_tool_result (now delegates to tool_unavailable_result -- exit_code 0/"note" soft-skip changed to exit_code 1/"error" loud failure, per vacuous-pass doctrine)
- docs/guides/install.md (bare-install section: ruff/ty are now real deps, missing-tool behavior documented)
- tests/unit/test_check_tool_unavailable.py (new: 9 tests -- tool_unavailable_result shape, ruff/ty/cargo/tsc absence, CheckResult.as_text rendering)

Dep pins chosen: `ruff>=0.8`, `ty>=0.0.1a8` -- identical to the `[dependency-groups].dev` pins already in pyproject.toml, no upper bound, matching every other `[project].dependencies` entry's style (none of them cap an upper bound either).

Stages guarded (FileNotFoundError -> typed failing ToolResult, verified by test or manual trace):
ruff-check, ruff-format, ty, cmake-configure, cmake-build, clang-tidy, clang-format, ctest, cargo-check/clippy (via _run_cargo), cargo-fmt, cargo-test, cargo-test(valgrind) x2 spawn points, tsc/eslint/prettier/vitest (all route through _run_npx -> _missing_tool_result).

Evidence (CLI): `frob ticket evidence` could not run its full-repo pytest --collect-only pass -- pre-existing, unrelated to this ticket: tests/unit/strata/test_kernel_properties.py hard-imports `strata_core`, a native extension not built in this environment (`ModuleNotFoundError: No module named 'strata_core'`), which aborts collection repo-wide (exit code 2) for any evidence-CLI or --collect-only invocation, not just this change's tests. Confirmed the 9 new node ids individually via `uv run pytest tests/unit/test_check_tool_unavailable.py -q` (9 passed) and appended them to this ticket's `evidence:` list directly, per the T-0138 precedent for CLI-collector limitations.

Filed: none.

Numbers:
- `uv run pytest tests/unit/test_check_tool_unavailable.py tests/unit/test_check.py tests/system/test_cli_check.py -q`: 48 passed, 0 failed
- `uv run pytest tests/ -q` (repo-wide): pre-existing failures only, all under tests/unit/strata/**, tests/unit/test_lang_strata.py, tests/system/test_cli_sys_plan.py, tests/system/test_frob_self_model.py, tests/test_gates.py::TestSysGate, tests/system/test_cli_sys_doc.py, tests/system/test_cli_sys_export.py, tests/system/test_cli_sys_audit.py, tests/test_vet_containment.py -- all trace back to the missing `strata_core`/`frob_core` native extensions in this worktree, not to this change (confirmed no failure references frob.check/frob.process/ruff/ty/cargo/tsc)
- `uv run ruff check .`: All checks passed! ; `uv run ruff format --check .`: 304 files already formatted
- `uv run frob check --ticket T-0142`: ruff-check/ruff-format/frob-cycle/frob-dup/frob-arch/frob-exports(*) all PASS; reviewer note: the ty stage FAILs in this worktree with 3 unresolved-import diagnostics (strata_core/frob_core) -- the known natives-not-built environment artifact (T-0144), verified pre-existing at the merge-base and not attributable to this diff; gates stage: 1024 violation(s), 54 waived (down from 1047 pre-scope-fix, since setting this ticket's scope also cleared its own COV002 warns; no new SCOPE001/PRE001/COV001/TEST001 introduced by this change)
- Bare-venv replication (T-0142's own acceptance test): `uv build`, installed the wheel into a clean `uv venv --python 3.11` with `uv pip install dist/frob-*.whl` -- `ruff==0.15.22` and `ty==0.0.61` pulled in automatically (previously absent), then `frob check <fixture>` from that bare venv: ruff-check/ruff-format/ty all PASS with no traceback (only unrelated TEST006 "no coverage stamp" gate fails on the tiny fixture) -- the standalone crash this ticket exists for is now structurally impossible (ruff/ty ship with the wheel) and independently defended (FileNotFoundError caught everywhere it could still occur).

Gates: `frob check --ticket T-0142` clean of SCOPE001/PRE001/COV001/COV002/TEST001 for this change's touched files (`frob ticket sweep T-0142` re-run after scope was set). Baseline `gates` stage still FAILs overall (1024 violation(s)) -- entirely pre-existing violations unrelated to this ticket's scope, not introduced or worsened by it.

NOT closed and NOT committed per dispatch instructions.
