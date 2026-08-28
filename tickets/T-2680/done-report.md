## Done report

Premise check: the code-level gap (direct land()/new_ticket() calls outside
tests/system/** inheriting ambient FROB_WORKTREE/FROB_AGENT) is ALREADY
CLOSED on main by T-3145's tests/conftest.py autouse fixture, which pops
both vars at setup for every test under tests/, not just tests/system/**.
Confirmed directly: TestSigkillMidStaging passes 5/5 under an ambient
lease env (FROB_WORKTREE=/tmp/nonexistent-lease-path FROB_AGENT=fake-agent)
on current main.

What remained was a STALE DOC CLAIM: docs/guides/agent-playbook-appendix.md's
section 5b (the T-0880 fix, relocated there by T-2909's playbook split --
the ticket's declared scope named agent-playbook.md, which no longer holds
this content) still asserted the narrower tests/system/**-only guarantee
without acknowledging T-3145 broadened it repo-wide. Added scope for the
appendix file (--reason recorded, mirrored to primary) and corrected the
doc with a T-2680 CORRECTION paragraph.

Evidence: TestSigkillMidStaging's 5 node ids (tests/test_ticket_land.py),
all confirmed passing under an ambient lease env, demonstrating T-3145's
fixture covers this file's guarantee.

Filed: none.

Gates: frob check --ticket T-2680 clean on gate:SCOPE and gate:PREWORK
(the gates this ticket's scope actually governs). All other FAIL families
observed in the full --only gates-fast run are pre-existing repo-wide
baseline per the run's own NOTE line, not introduced by this change.

### Changed
```
 docs/guides/agent-playbook-appendix.md | 17 +++++++++++++++++
 tickets/T-2680/ticket.md               | 14 ++++++++++++++
 2 files changed, 31 insertions(+)
```

### Evidence
- `tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSigkillMidStaging::test_unrelated_land_does_not_absorb_a_killed_lands_staged_content` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_during_finalize_close_leaves_ticket_recoverable_not_a_silent_lie` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSigkillMidStaging::test_normal_land_reaches_done_exactly_once_no_extra_transition` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_during_post_squash_reverification_leaves_ticket_recoverable` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 78 error(s), 686 warning(s), 875 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-3180/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2680, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
