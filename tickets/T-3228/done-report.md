## Done report

DEPR006 (src/frob/gates/_debt_deprecated.py::_depr006_producer_abandoned,
joined into deprecated_gate) and WAIVE011
(src/frob/gates/_waive.py::waive011_violations, joined into
_assemble_gate_report's WAIVE00* self-check block) reuse
frob.gates._lock_producer.producer_status/KNOWN_LOCKS verbatim (T-2999's
shared computation frob status already reads), matching TEST012's own
coverage-lock producer check exactly: ERROR when the verdict is
ABANDONED, silent when PINNED, both keyed off the same
ABANDONED_CODE_COMMIT_THRESHOLD.

Design decision: neither lock had an existing WARN check to extend
(unlike TEST012 which extended _test012_lock's content-drift check).
DEPR006 joins the DEPR family since the deprecated-baseline lock is
literally that family's own DEPR005 mechanism (same module,
frob.gates._deprecated_baseline). WAIVE011 joins the WAIVE family
rather than inventing a fourth gate family: a stale ratchet pool
(frob-ratchet.lock.json, T-0569) is functionally the same failure mode
WAIVE009/WAIVE010 already police for one inline frob:waive comment --
a frozen exemption nobody is re-verifying -- just applied to the
bulk-pool mechanism instead. Both new rule ids registered in
docs/design/registry/check-coverage.yaml (CHK-GATE-DEPR006/WAIVE011)
and src/frob/gates/_waive.py's `_KNOWN_GATE_RULES`/`frob:enumerates`
directive in docs/modules/gates.md, matching every other live rule.

Confirmed against this repo's own real history (not synthetic): both
new checks currently FIRE for real -- DEPR006 measured
frob-deprecated-baseline.lock.json ABANDONED (1191+ commits touching
src/frob/**/*.py since last stamp, unpinned) at time of writing. This
is the expected, correct behavior this ticket asked for (the acceptance
criterion is that an ABANDONED verdict produces a loud finding) --
actually re-stamping/pinning either lock is a separate concern, out of
this ticket's scope (T-3228 is the gate wiring, not the lock refresh).

Gates: frob check --ticket T-3228 clean on the ticket-scoped subset
(gate:SCOPE 0 genuine new errors -- the one SCOPE001 hit is a stray
tickets/T-3242/ticket.md that entered this worktree's HEAD
via an unrelated auto-sync merge from main, not this diff; gate:AFFECT
0 errors after the docs/modules/gates.md update; gate:FMT clean).
ruff-check 0 errors on touched files. ty: no new findings on touched
files. Repo-wide gate families (including the now-nonzero gate:DEPR
and unchanged gate:WAIVE counts) are baseline/expected per the
--ticket scope-note, not evidence of a defect in this diff -- gate:DEPR
going from 0 to 1 IS this ticket's intended effect (a real, currently
abandoned lock made loud).

### Changed
```
 docs/design/registry/check-coverage.yaml     | 10 ++++
 docs/modules/gates.md                        | 21 ++++++-
 src/frob/gates/__init__.py                   |  6 ++
 src/frob/gates/_debt_deprecated.py           | 62 +++++++++++++++++---
 src/frob/gates/_waive.py                     | 66 +++++++++++++++++++++
 tests/test_waive_gate.py                     | 82 ++++++++++++++++++++++++++
 tests/unit/gates/test_deprecated_baseline.py | 86 ++++++++++++++++++++++++++++
 tickets/T-3228/ticket.md                     | 75 +++++++++++++++++++++++-
 tickets/T-3242/ticket.md           | 34 +++++++++++
 9 files changed, 432 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/gates/test_deprecated_baseline.py::TestDepr006ProducerAbandoned::test_abandoned_producer_fires_error` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_deprecated_baseline.py::TestDepr006ProducerAbandoned::test_pinned_producer_stays_quiet` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive011ProducerAbandoned::test_abandoned_producer_fires_error` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive011ProducerAbandoned::test_pinned_producer_stays_quiet` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 101 error(s), 3351 warning(s), 879 waived
- error-findings: ARCH102@src/frob/gates/_waive.py, ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@src/frob/gates/_waive.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV003@tickets/T-3223, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/clean/_core.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@src/frob/app/ticket_runner/_land_cmd.py, OPAQUE001@tests/test_vet_capability.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3228, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py, unresolved-attribute@scripts/fleet_status.py, unresolved-attribute@tests/system/test_fleet_status_ground_truth.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
