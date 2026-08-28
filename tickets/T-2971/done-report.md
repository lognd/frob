## Done report

Re-measured macOS CI (run 33135896391, job 98735671710) via
`gh run view --job 98735671710 --log-failed`, grepping
SUITE-RESULT-FAILED and the pytest short summary for the authoritative
`SUITE-RESULT: ... failed=N` line, per this ticket's own acceptance
criterion.

RESULT: 68 failures (down from the pre-T-2943 156-failure baseline),
both Lint and Typecheck passing on macOS -- only Test failed.

Determined the genuine-findings-vs-platform-difference split by MEASURING
each cluster's shape and reading the relevant scanner source, not by
inferring a single blanket answer for all 68:

- ~10 are genuine, platform-invariant repo findings: the self-
  conformance/registry family (SYS100/SYS003/DOC004/DOC006/REG008/
  WAIVE006/coverage-registry). check_self_conformance's own docstring
  confirms the underlying scanner is a language-generic pattern matcher
  over checked-in source text, not Python-AST or platform-specific --
  its output cannot differ by OS. These are real design/frob.strata
  drift, newly visible now that a macOS run actually completes, not a
  macOS-caused finding.
- ~15 are very likely a macOS-specific bug in frob's OWN gate/land
  machinery, not real repo findings: 9 identically-shaped
  test_tickets_live_tracker.py failures ("assert 0 == N" citation hits)
  plus 6 identically-shaped live-process-detection failures across
  test_land_finish_guard.py/test_ticket_leases.py/test_worktree_guard.py
  ("removed" vs "kept:live"). Read the live-tracker citation scanner's
  source (it shells out to `git grep`, a plausible macOS-git-config
  culprit) and flagged the liveness cluster's shared "false on macOS"
  signature as resembling T-3191's own POSIX-assumption bug shape
  (unconfirmed without macOS hardware -- stated as a hypothesis for
  follow-up triage, not claimed as proven).
- ~43 remain mixed/uncharacterized (native-extension edge cases, golden-
  file byte diffs, JSON round-trips, CRLF handling, singletons) --
  explicitly left to T-2992's own per-failure triage queue, which is
  this ticket's stated boundary (RE-MEASURE and report, not resolve the
  backlog).

Filed nothing new: this ticket's own instruction is to update T-2971
with the fresh measurement rather than file a duplicate ticket, and the
per-failure triage destination (T-2992) already exists and is queued.

Evidence: docs-kind investigation ticket -- the evidence IS the
measurement recorded in the ticket body above (the `gh run view`
command, its exact output counts, and the source-reading that grounds
the genuine-vs-platform classification), not a pytest node id. No code
changed.

### Changed
```
 tickets/T-2971/done-report.md |  63 +++++++++++++++++++++++
 tickets/T-2971/ticket.md      | 116 +++++++++++++++++++++++++++++++++++++++++-
 2 files changed, 178 insertions(+), 1 deletion(-)
```

### Evidence
- `cmd:/tmp/claude-1000/-home-logan-projects-frob/79c6402d-b401-4652-bea7-f81df1be9322/scratchpad/t2971_evidence_check.sh exit=0 sha256=5c545b9f4724` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 95 error(s), 703 warning(s), 882 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@.claude/hooks/frob-suggest.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@src/frob/check/_python.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_narrative_migrate.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py, unresolved-attribute@scripts/fleet_status.py, unresolved-attribute@tests/system/test_fleet_status_ground_truth.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
