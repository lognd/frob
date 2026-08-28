## Done report

Measured against main directly, not inferred from the ticket text.
All 20 (rule, file) identities the sweep filed were checked individually
against a fresh `frob check --json` run:

- AFFECT001 src/frob/app/mutate_runner.py -- NOT FOUND
- AFFECT001 src/frob/testing/_collect.py -- NOT FOUND
- AFFECT001 src/frob/testing/_coverage_refresh.py -- NOT FOUND
- COV002 tests/unit/test_pytest_spawn_env_wiring.py -- NOT FOUND
- I001 tests/unit/verify/test_quarantine.py -- NOT FOUND (ruff-check itself
  is clean: 0 diagnostics)
- SUPPRESS001 src/frob/app/ticket_runner/_new.py -- NOT FOUND
- SUPPRESS001 tests/test_ci_report.py -- NOT FOUND
- SUPPRESS001 tests/test_tickets.py -- NOT FOUND
- SUPPRESS001 tests/test_tickets_acceptance.py -- NOT FOUND
- SUPPRESS001 tests/test_tickets_brief.py -- NOT FOUND
- SUPPRESS001 tests/test_tickets_velocity.py -- NOT FOUND
- SUPPRESS001 tests/unit/verify/test_backpressure.py -- NOT FOUND
- invalid-argument-type src/frob/__main__.py -- NOT FOUND
- invalid-argument-type src/frob/app/_config_external.py -- NOT FOUND
- invalid-argument-type tests/unit/test_app_runners_batch6.py -- NOT FOUND
- invalid-assignment tests/test_ci_report.py -- NOT FOUND
- invalid-assignment tests/test_tickets_velocity.py -- NOT FOUND
- invalid-assignment tests/test_vet.py -- NOT FOUND
- invalid-assignment tests/unit/verify/test_backpressure.py -- NOT FOUND
- unresolved-attribute tests/unit/test_main_entry.py -- NOT FOUND

0 of 20 reproduce. `ty`'s current diagnostic set on main (11 findings)
carries only `unused-ignore-comment` and `unknown-argument` codes --
none of `invalid-argument-type`/`invalid-assignment`/`unresolved-attribute`
appear anywhere in it. `ruff-check` is fully clean (0 diagnostics), so
I001 (an isort/import-order rule) cannot be firing either. SUPPRESS001
fires exactly once on main right now, on a DIFFERENT file
(src/frob/app/_config_external.py, for an unrelated unused-ignore-comment
mismatch) than any of the 6 files this ticket named. AFFECT001/COV002
do not appear on any of the named files at all.

The sweep's own attribution engine recorded all 20 as UNATTRIBUTED. That
is consistent here: many other tickets landed between T-3107's commit
(1ee8d593fdfb) and now, and the tool/rule surface plainly moved (this
session independently fixed ty's missing-argument finding in T-3160
just before this ticket, for example) -- these findings most likely
describe an intermediate, transient state of the tree between T-3107
and one of the many subsequent lands, not a durable regression the
current tree carries.

Stated explicitly per the ticket's own disposition instructions: closed
as pre-existing/transient residue the rolling baseline had recorded and
already self-resolved, not fixed -- there is nothing on the current
tree to fix. Verified via a scripted re-check
(python3 /tmp/verify_t3112.py, recorded as evidence) that re-runs
`frob check --json` fresh and re-tests all 20 identities programmatically,
not by eyeballing counts.

Filed: none.

### Changed
```
 tickets/T-3112/ticket.md | 13 ++++++++++++-
 1 file changed, 12 insertions(+), 1 deletion(-)
```

### Evidence
- `cmd:python3 /tmp/verify_t3112.py exit=0 sha256=6cfa164dbb1b` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 77 error(s), 2106 warning(s), 875 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3112, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/conftest.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
