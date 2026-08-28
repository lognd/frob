## Done report

No ticket body/scope existed (empty on file). Investigated directly:
frob's global -v/--verbose (top-level parser) sets FROB_VERBOSE=1 via
_apply_verbose_env_override (frob.__main__) BEFORE dispatch, regardless
of where -v appears in argv. `frob ticket` ALSO registers its own LOCAL
-v (dest=ticket_verbose, on the `ticket` subparser, between `ticket` and
its leaf subcommand -- `frob ticket -v show T-1`) that skips
_diagnostic_log_ctx's WARNING clamp on the `frob` logger tree during
ticket dispatch.

Reproduced directly:
  frob ticket -v show T-1          -> verbose (gitio DEBUG lines shown)
  frob -v ticket show T-1          -> NOT verbose -- WARNING-clamped,
                                       even though FROB_VERBOSE=1 was
                                       already set for this process
  frob ticket show T-1 -v          -> hard argparse error (both -v
                                       registrations are out of scope
                                       for a nested subparser)

So the global flag is exactly "silently accepted and ignored": argparse
accepts it happily at the top level (no error), _apply_verbose_env_override
sets FROB_VERBOSE=1, but _diagnostic_log_ctx checked ONLY
cfg.ticket_verbose (populated exclusively by ticket's own local -v) and
re-clamped the frob logger tree to WARNING regardless, discarding the
global flag's effect for the whole ticket dispatch. Only the local,
between-ticket-and-leaf position worked, matching the ticket title.

Fix: _diagnostic_log_ctx now also checks FROB_VERBOSE=1 / FROB_LOG_LEVEL
(the same escape hatch frob.logging.quiet.quiet_query_stdout (T-2582)
already honors) and skips the clamp when either is set -- so the GLOBAL
flag now works from the top-level position too, chosen over refusing it
since making it actually work is strictly better for a flag that was
already syntactically valid there.

Verified live end-to-end (not just unit tests): `frob -v ticket show
T-3000` now prints the full gitio/tickets DEBUG chatter, matching `frob
ticket -v show T-3000`'s existing behavior.

Added 2 new regression unit tests (FROB_VERBOSE and FROB_LOG_LEVEL paths)
plus a must-stay-quiet twin confirming the clamp still applies with
neither ticket_verbose nor either env var set. Confirmed the two new
tests FAIL at the parent commit (fix reverted via patch/checkout
roundtrip, ticket_runner/__init__.py alone) with the exact "still
WARNING-clamped" assertion failure, then pass with the fix.

Gates: ty check and ruff format --check clean on both touched files.
All 5 tests in tests/test_ticket_runner_quiet.py pass.

### Changed
```
 src/frob/app/ticket_runner/__init__.py | 23 +++++++++++++--
 tests/test_ticket_runner_quiet.py      | 51 ++++++++++++++++++++++++++++++++++
 2 files changed, 72 insertions(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 91 error(s), 701 warning(s), 877 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/app/ticket_runner/_land_cmd.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SUPPRESS001@src/frob/app/_config_external.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py, unresolved-attribute@scripts/fleet_status.py, unresolved-attribute@tests/system/test_fleet_status_ground_truth.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
