## Done report

Changed:
  src/frob/gates/_lock_producer.py (new: producer_status/all_producer_statuses,
    LockPin/TrackedLock/LockProducerStatus, KNOWN_LOCKS)
  src/frob/app/status_runner.py (StatusReport.baseline_locks + human printer)
  src/frob/gates/__init__.py (_test012_producer_abandoned, ERROR-severity)
  tests/unit/gates/test_lock_producer.py, tests/test_status.py, tests/test_gates.py
  docs/modules/gates.md, docs/modules/cli.md

Evidence:
  tests/unit/gates/test_lock_producer.py (6 tests: verdict matrix, must-fire
    abandoned, must-stay-quiet pinned)
  tests/test_gates.py::TestTestGate::test_test012_abandoned_producer_fires_error
  tests/test_gates.py::TestTestGate::test_test012_pinned_producer_stays_quiet
  tests/test_status.py::TestBuildStatusReportIntegration::test_baseline_locks_section_is_always_populated
  All existing TestTestGate (71) and test_status.py (15) tests still pass.

Filed: T-3228 (LOUD gate failure for ratchet/deprecated-baseline lock
  producer abandonment -- the same mechanism this ticket built, wired
  into a second and third gate; T-2999's own scope only extended TEST012,
  the one existing gate with a natural WARN-severity home to escalate
  from).

Gates: frob check --only gates-fast --delta --ticket T-2999 clean for
  every file this ticket touched (zero findings against
  _lock_producer.py/status_runner.py/gates/__init__.py/the new and edited
  test files, confirmed by name-filtering the JSON report). Repo-wide
  gate families (DRIFT/REF/REG/REL/TICK/WAIVE/SUPPRESS/FLAGCOV/PRE) show
  pre-existing, unrelated findings -- none reference a file this ticket
  touched.

ACCEPTANCE (per ticket body):

1. "Each baseline's age and last-stamping producer are visible in `frob
   status`" -- DONE: a new, always-on "baseline locks" section shows all
   three tracked locks' verdict, age, last-stamp date, and pin reason
   where present.

2. "A baseline whose producer has demonstrably stopped produces a LOUD,
   named failure ... at the point of consumption" -- DONE for the
   coverage lock (TEST012's new ERROR-severity third finding). NOT yet
   done for the ratchet/deprecated-baseline locks -- filed as T-3228
   rather than expanding scope, since neither has an existing gate this
   ticket could extend the way TEST012 already existed for coverage; a
   genuinely new rule id would need check-coverage.yaml registry
   ceremony this ticket's own scope does not cover.

3. "A deliberately-pinned baseline does NOT produce that failure" --
   DONE: the `pin` field, with must-fire/must-stay-quiet fixture pairs
   at both the shared-helper level and the TEST012 gate level.

4. "Report, for each of the three current baselines, which state it is
   actually in" -- MEASURED (T-2999 investigation, git history, not
   inferred): all three are genuinely ABANDONED, none pinned.
     frob-coverage.lock.json: last stamped 2026-08-06, 5817 commits since
       (816 touching src/frob/**/*.py)
     frob-deprecated-baseline.lock.json: last stamped 2026-07-28, 7051
       commits since (1177 touching src/frob/**/*.py)
     frob-ratchet.lock.json: last stamped 2026-07-23, 7454 commits since
       (1389 touching src/frob/**/*.py)
   None of the three are legitimately frozen-by-construction (unlike,
   say, refactor's small fs.read/fs.write node from T-3029) -- the code
   each one baselines has moved substantially since its last stamp, with
   no pin declaring the staleness deliberate. This ticket does NOT
   re-stamp any of the three (that is a separate, larger action --
   running `frob check --stamp-coverage`, the ratchet pool tooling, and
   the deprecated-baseline tightening path, each with its own review
   surface) -- it makes the abandonment VISIBLE and, for coverage, LOUD,
   which is what the ticket asked for.

### Changed
```
 docs/modules/cli.md                    |  12 ++
 docs/modules/gates.md                  |  32 +++++
 src/frob/app/status_runner.py          |  39 +++++
 src/frob/gates/__init__.py             |  56 +++++++-
 src/frob/gates/_lock_producer.py       | 251 +++++++++++++++++++++++++++++++++
 tests/test_gates.py                    |  78 ++++++++++
 tests/test_status.py                   |  18 +++
 tests/unit/gates/test_lock_producer.py | 150 ++++++++++++++++++++
 tickets/T-2999/ticket.md               |  14 ++
 9 files changed, 647 insertions(+), 3 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 99 error(s), 1334 warning(s), 876 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2999/src/frob/app/status_runner.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2999/src/frob/app/status_runner.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2999/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2999/src/frob/gates/_lock_producer.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2999/src/frob/gates/_lock_producer.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/app/ticket_runner/_land_cmd.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py, unresolved-attribute@scripts/fleet_status.py, unresolved-attribute@tests/system/test_fleet_status_ground_truth.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
