## Done report

Reproduced directly before fixing: _wire_reach_patterns's wrapper_pattern
matched only BARE marker names immediately before "(" (the negative
lookbehind (?<![A-Za-z0-9_.]) explicitly excludes a dot-preceded match),
so atexit.register(_remove_scratch_file, path) (T-2645) could never
match -- confirmed with wrapper_pattern.search() against that exact
literal returning None pre-fix.

Read the existing by-reference mechanism first, per instruction: T-1502's
_WRAPPER_MARKER_NAMES (bare markers), T-1684's dict-table value
alternative, T-2778's keyword-argument-value alternative -- all extend
ONE wrapper_pattern regex built in _wire_reach_patterns, gated to
kind == SymbolKind.FUNCTION where a CLASS anchor (T-1831) must keep
firing. Extended that same mechanism rather than writing a separate
predicate: added _DOTTED_WRAPPER_MARKERS (module, attr) pairs and a new
dotted-wrapper alternative in wrapper_pattern's construction (kept
separate from the bare _WRAPPER_MARKER_NAMES set specifically because a
loosened bare-name lookbehind would risk matching an unrelated object's
same-named .register() method -- each dotted pair builds an exact
module\.attr\( alternative instead).

Checked T-1820 (the dead-by-design WIRE001 anchor named in the brief)
before touching anything: unrelated shape (argparse dests bypassed by
dispatch before AppConfig construction, no atexit involvement at all) --
the new dotted-wrapper alternative cannot touch it.

Fixtures (tests/unit/test_wire001_atexit_register.py, following this
repo's existing test_wire001_callback_keyword_argument.py precedent of
one file per WIRE001 fix):
- must-stay-quiet: a FUNCTION whose only reference anywhere is
  atexit.register(_target, ...) is not flagged
- must-fire (positive control): a FUNCTION with no caller anywhere still
  fires WIRE001
- anti-abuse control: a CLASS registered via atexit.register the
  identical way still fires (gated to FUNCTION only, matching T-1831's
  own CLASS-must-still-fire precedent)

Removed the now-redundant per-site frob:waive WIRE001
follow_up="T-2931" on _remove_scratch_file (src/frob/tickets/
_unlanded.py) in this same change -- verified directly with wire_gate()
that the symbol stays unflagged without the waiver. Filed T-draft-
56527a0d for this cleanup first, then dropped it once done directly here
instead of leaving a stale successor open.

Gates: frob check --ticket T-2931 clean for the ticket-scoped families
(gate:SCOPE 0 errors after adding tests/unit/test_wire001_atexit_
register.py and src/frob/tickets/_unlanded.py to scope; COV002/TODO001
diff-driven checks show no new hits -- the one TODO001 line reported is
pre-existing prose on main, shifted by this diff's insertion, not
introduced by it; gate:FMT 0 errors). Other gate families in the output
are repo-wide per the tool's own scope-note.

### Changed
```
 src/frob/gates/_wire.py                    |  50 ++++++++-
 src/frob/tickets/_unlanded.py              |   5 -
 tests/unit/test_wire001_atexit_register.py | 160 +++++++++++++++++++++++++++++
 tickets/T-2931/done-report.md              |  67 ++++++++++++
 tickets/T-2931/ticket.md                   |  30 +++++-
 tickets/T-3240/ticket.md         |  33 ++++++
 6 files changed, 333 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/unit/test_wire001_atexit_register.py::TestWire001AtexitRegister::test_function_registered_via_atexit_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_wire001_atexit_register.py::TestWire001AtexitRegister::test_function_with_no_caller_anywhere_still_flagged_positive_control` (pytest node id, verified passing when recorded)
- `tests/unit/test_wire001_atexit_register.py::TestWire001AtexitRegister::test_class_registered_via_atexit_still_flagged_anchor_control` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 96 error(s), 830 warning(s), 876 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, DUP001@tests/unit/test_wire001_atexit_register.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/app/ticket_runner/_land_cmd.py, OPAQUE001@tests/test_vet_capability.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2931, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py, unresolved-attribute@scripts/fleet_status.py, unresolved-attribute@tests/system/test_fleet_status_ground_truth.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
