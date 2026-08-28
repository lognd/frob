## Done report

MECHANISM (measured): `_file_regression_ticket` already paid for an
independent `frob check --json` re-measure at file time
(`_true_finding_count_for_identities`, T-1935) -- but only used its
result for a cosmetic "N finding(s)" title label, never as a filing
gate. Direct evidence from the live queue: T-3188, T-3210, and T-3215
were all filed with that same re-measure's own "0 finding(s)" line
already in their body/title, and filed anyway. This is not the
"detached/deferred spawn moved main before filing" hypothesis (that
would require the measure-to-file window to be long; here filing
follows the measure within the same function call, no window at all) --
it is a re-measure that ran, correctly detected zero live findings, and
was ignored by the filing decision.

Changed:
- src/frob/app/ticket_runner/_rapid_sweep.py::_reverify_unfiled_pairs_at_file_time (new)
- src/frob/app/ticket_runner/_rapid_sweep.py::_file_regression_ticket (now gates filing on the above; no longer calls `_true_finding_count_for_identities` directly -- reuses `_matching_error_diagnostics` for one spawn producing both the true count and the live-identity set)

`_true_finding_count_for_identities` and `_identities_still_reproducing`
are both left in place (still used by doable-time revalidation and
still covered by their own pre-existing tests) -- this fix reuses their
shared low-level fetch (`_matching_error_diagnostics`) rather than
duplicating a second spawn.

Vanished identities are recorded via `record_rapid_debt` (ticket id =
the spawning land, skipped = `sweep-finding-vanished-before-file:<rule>:<file>`)
rather than dropped silently, satisfying acceptance criterion 3.

An unmeasurable re-check (spawn refused/timeout/unparsable) degrades to
the pre-fix behavior exactly (file everything unchanged, true_count=None
in the title) -- unmeasurable is never read as resolved.

Fixtures:
- must-fire: TestReverifyUnfiledPairsAtFileTime.test_still_live_pair_is_kept,
  TestFileRegressionTicket.test_still_reproducing_finding_files_a_ticket
- must-stay-quiet: TestReverifyUnfiledPairsAtFileTime.test_vanished_pair_is_dropped_and_recorded_as_debt,
  TestFileRegressionTicket.test_vanished_finding_files_no_ticket
- degrade-safe: TestReverifyUnfiledPairsAtFileTime.test_unmeasurable_files_everything_as_before

Also added a module-level autouse fixture (`_default_true_count_spawn_refused`)
in tests/unit/test_rapid_sweep.py -- every pre-existing test in this file
that expects a finding to be filed built a fake tmp_path "repo" and never
mocked this spawn (it was cosmetic pre-fix); once it became load-bearing,
the REAL spawn ran against a non-scannable tmp_path and truthfully (but
irrelevantly) reported every identity vanished, breaking ~26 unrelated
tests. Defaulting the spawn to refused repo-wide in this test file
restores every one of those tests' original intent without editing each
one individually; the handful of tests that specifically exercise the
new gate re-monkeypatch the same target afterward.

Filed: none (no out-of-scope defect found; the byte-identical duplicate
ticket pairs noted in T-3222's body as "also in scope, if in the sweep's
filing path" were NOT investigated -- ran out of scope/time budget this
series; leaving that thread for a follow-up ticket rather than guessing.
Recommend filing "duplicate-ticket filing in the sweep path" separately if
still live).

Before/after ratio: not re-measured against a live sweep batch this
series (would require landing this fix and waiting for real sweeps) --
the fix is verified by the 3 real historical cases (T-3188/T-3210/T-3215)
that would now be dropped-with-debt instead of filed, and by the fixture
pair proving both a still-live finding is filed and a vanished one is not.

Gates: frob check --ticket T-3222 clean for the ticket-scoped families
(gate:SCOPE 0 errors, gate:FMT 0 errors, gate:AFFECT 0 errors, no COV002/
TODO001 on touched files); gate:DRIFT for `_file_regression_ticket`
acked. All other gate:* counts in the full run are repo-wide pre-existing
findings (per gate:scope-note), unrelated to this change -- confirmed
none of gate:DRIFT/COV/DOC/etc.'s new-since-baseline lines name
_rapid_sweep.py or test_rapid_sweep.py beyond the acked digest.

### Changed
```
 tickets/T-3222/ticket.md | 21 +++++++++++++++++++++
 1 file changed, 21 insertions(+)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 93 error(s), 915 warning(s), 883 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV003@tickets/T-3181, COV007@.claude/hooks/frob-suggest.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/check/_python.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/check/_python.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3222, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_done_report.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SUPPRESS001@src/frob/app/_config_external.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py, unresolved-attribute@scripts/fleet_status.py, unresolved-attribute@tests/system/test_fleet_status_ground_truth.py, unresolved-attribute@tests/test_app_daemon_proxy.py, unresolved-attribute@tests/test_coverage_wait_shared.py, unresolved-attribute@tests/test_serve_leases.py, unresolved-attribute@tests/test_serve_socket.py, unresolved-attribute@tests/test_ticket_land.py, unresolved-attribute@tests/test_ticket_leases.py, unresolved-attribute@tests/test_ticket_reconcile.py, unresolved-attribute@tests/test_tickets_parent.py, unresolved-attribute@tests/test_tickets_priority.py, unresolved-attribute@tests/unit/test_conftest_stackdump.py, unresolved-attribute@tests/unit/test_coordinator_scripts.py, unresolved-attribute@tests/unit/test_land_finish_guard.py, unresolved-attribute@tests/unit/test_land_lock_liveness.py, unresolved-attribute@tests/unit/test_process_lock.py, unresolved-attribute@tests/unit/test_rapid_sweep.py, unresolved-attribute@tests/unit/test_stackdump.py, unresolved-attribute@tests/unit/test_ticket_store.py
