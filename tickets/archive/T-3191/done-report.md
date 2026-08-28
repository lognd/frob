## Done report

STRUCTURAL FIX (not four site edits):
1. frob.check._python._run_ty now runs ty check --python-platform <p>
   once per platform in frob.toml's [ty] target_platforms (default
   linux/win32/darwin -- this project's own CI OS matrix, declared not
   hardcoded) and unions the results into one tool="ty" ToolResult,
   each diagnostic tagged [platform=<name>]. This is what makes a
   Windows-only diagnostic reachable from a Linux host at all.
2. POLICY for the two matched-opposite-error sites: removed the need for
   any static suppression, in both directions. _reap.py's os.sysconf and
   _pid_liveness.py's ctypes.windll.kernel32 are now behind explicit
   if sys.platform == "win32": guards, which ty narrows per
   --python-platform target the same way typeshed's own conditional
   stubs do (mirrors the T-2981 _socketd.py precedent). No ty: ignore
   remains at either site, on any target.
3. All 4 diagnostics from CI run 33135896391 resolved under that policy
   -- confirmed by running the actual multi-platform check locally, not
   by pushing and watching CI.

DEMONSTRATION (Linux host, before any push):
  ty check src --extra-search-path src --python .venv --python-platform win32
  -> the os.sysconf/ctypes.windll sites report ZERO diagnostics; the exact
     4-diagnostic set from CI run 33135896391 was reproduced BEFORE the
     fix and confirmed resolved AFTER (only two pre-existing,
     platform-independent unused-ignore warnings in unrelated files
     remain, present on every platform target including Linux).

MUST-FIRE fixtures: tests/unit/test_check.py::TestRunTyMultiPlatform::test_windows_only_diagnostic_is_reported_from_linux_host;
tests/unit/test_process_reap.py::TestReadUptimeAndClkTck::test_win32_skips_sysconf_and_uses_fallback;
tests/unit/test_process_pid_liveness.py::TestKernel32PlatformGuard::test_win32_resolves_kernel32
(direct guard-level fixtures via importlib.reload under a faked sys.platform).

MUST-STAY-QUIET fixtures: tests/unit/test_check.py::TestRunTyMultiPlatform::test_ordinary_cross_platform_code_stays_quiet;
test_non_win32_still_reads_sysconf; test_non_win32_leaves_kernel32_none.

COST (measured): ~1.2s per ty check invocation on this repo (Rust-native).
Three platforms cost ~2.5s of added wall-clock over the prior single-platform
baseline -- negligible against frob check's other stages (dup/arch routinely
20-45s) -- so it runs on every frob check, not deferred to a
land-time/CI-parity-only gate. Documented in code and docs/commands/check.md.

Evidence:
- tests/unit/test_check.py::TestRunTyMultiPlatform (5 tests, pass)
- tests/unit/test_check_tool_unavailable.py::TestTyHermeticRootResolution (updated for 3x-per-platform invocation, both pass)
- tests/unit/test_process_reap.py::TestReadUptimeAndClkTck (2 tests, pass)
- tests/unit/test_process_pid_liveness.py::TestKernel32PlatformGuard (2 tests, pass)
- Full test_process_reap.py + test_process_pid_liveness.py + test_check.py + test_check_tool_unavailable.py suites: 219 tests, 0 failed
- ruff check / ruff format --check clean on every touched file
- Direct ty check --python-platform win32/darwin/linux runs from this Linux host, reproducing then resolving CI run 33135896391's 4 diagnostics

Filed: T-3211 (Burn down platform-unsafe code surfaced by multi-platform ty) -- also, a schema known-keys
validator for frob.toml's new [ty] table is noted as intentionally
deferred in frob.toml's own comment -- config-schema-validator
completeness, not platform reachability, which is this ticket's scope)

Gates: frob check --ticket T-3191 -- gate:SCOPE 0 errors, gate:PREWORK
clean, no COV002/TODO001 diagnostics in the diff-driven scope. Every
other gate family's counts in that run are REPO-WIDE per its own
gate:scope-note and pre-exist this ticket's diff (confirmed: none
reference _reap.py/_pid_liveness.py/_run_ty's new code; the sole
gate:SUPPRESS finding is _config_external.py:786, an out-of-scope
pre-existing site unrelated to this ticket).

### Changed
```
 docs/commands/check.md                    |  33 +++++++
 docs/modules/process.md                   |  17 ++++
 frob.toml                                 |  19 ++++
 src/frob/check/_python.py                 | 140 +++++++++++++++++++++++++++---
 src/frob/process/_pid_liveness.py         |  26 ++++--
 src/frob/process/_reap.py                 |  28 ++++--
 tests/unit/test_check.py                  | 116 +++++++++++++++++++++++++
 tests/unit/test_check_tool_unavailable.py |  25 +++---
 tests/unit/test_process_pid_liveness.py   |  49 +++++++++++
 tests/unit/test_process_reap.py           |  58 ++++++++++---
 tickets/T-3191/done-report.md             |  87 +++++++++++++++++++
 tickets/T-3191/ticket.md                  |  14 ++-
 tickets/T-3211/ticket.md        |  72 +++++++++++++++
 13 files changed, 638 insertions(+), 46 deletions(-)
```

### Evidence
- `tests/unit/test_check.py::TestRunTyMultiPlatform::test_default_platforms_all_run` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunTyMultiPlatform::test_windows_only_diagnostic_is_reported_from_linux_host` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunTyMultiPlatform::test_ordinary_cross_platform_code_stays_quiet` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunTyMultiPlatform::test_configured_target_platforms_override_default` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunTyMultiPlatform::test_one_failing_platform_fails_the_merged_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_tool_unavailable.py::TestTyHermeticRootResolution::test_extra_search_path_and_python_pin_to_root` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_tool_unavailable.py::TestTyHermeticRootResolution::test_no_src_or_venv_omits_the_pinning_flags` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestReadUptimeAndClkTck::test_win32_skips_sysconf_and_uses_fallback` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestReadUptimeAndClkTck::test_non_win32_still_reads_sysconf` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_pid_liveness.py::TestKernel32PlatformGuard::test_win32_resolves_kernel32` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_pid_liveness.py::TestKernel32PlatformGuard::test_non_win32_leaves_kernel32_none` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 93 error(s), 758 warning(s), 877 waived
- error-findings: ARCH001@src/frob/check/_python.py, ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@.claude/hooks/frob-suggest.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_narrative_migrate.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py, unresolved-attribute@scripts/fleet_status.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
