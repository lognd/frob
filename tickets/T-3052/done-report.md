## Done report

Changed:
- src/frob/verify/_worker.py::_resolve_verification_outcome

Fix: the rolling baseline write moved from one unconditional call right
after the read to per-branch writes matching what each branch actually
decided. baseline-established, green, and red-with-owner all still write
`fresh` as the new comparison point (unchanged from before). The
unfiled-red branch (T-2324's own "never silently certify" case) no
longer writes at all -- the prior baseline is left untouched, so an
unfilable finding keeps reproducing as NEW on every subsequent wake
instead of being silently absorbed into "known state" after one round.

Must-fire fixture: test_unfilable_finding_still_pins_the_watermark_on_the_next_wake
runs run_coalesced_verification twice against an unchanged tree with
_file_regression_ticket always refusing -- asserts wake 2 is STILL red
and STILL does not advance the watermark (before this fix, wake 2 would
read fresh == baseline and go green). The existing T-2324 positive/
negative controls (test_new_findings_filed_to_a_real_ticket_still_advance,
test_new_findings_that_cannot_be_filed_still_do_not_advance) also
re-verified clean, confirming the single-wake behavior this fix must not
change.

Evidence: tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_unfilable_finding_still_pins_the_watermark_on_the_next_wake, tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_new_findings_that_cannot_be_filed_still_do_not_advance, tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_new_findings_filed_to_a_real_ticket_still_advance -- all PASS (pytest -q, 9/9 collected/passed in TestRunCoalescedVerification).

Filed: none -- the H5 fix is scoped exactly to
_resolve_verification_outcome's baseline-write ordering; no out-of-scope
work found.

Gates: `frob check --only gates-fast --ticket T-3052` shows zero new
COV002/gate:SCOPE/gate:AFFECT findings against src/frob/verify/_worker.py
or tests/unit/verify/test_worker.py from this diff. Remaining
gate:COV/DOC/DRIFT/REF/REG/TICK/WAIVE failures are pre-existing
repo-wide debt, unchanged in count by this diff (verified via targeted
grep of the gate output for _worker.py -- only WALK001 pre-existing
waived hits and unrelated module lines appear).

### Changed
```
 src/frob/verify/_worker.py       | 50 ++++++++++++++++++++++++++++-------
 tests/unit/verify/test_worker.py | 56 ++++++++++++++++++++++++++++++++++++++++
 tickets/T-3052/ticket.md         | 26 ++++++++++++++++++-
 3 files changed, 121 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_unfilable_finding_still_pins_the_watermark_on_the_next_wake` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_new_findings_that_cannot_be_filed_still_do_not_advance` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_new_findings_filed_to_a_real_ticket_still_advance` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 62 error(s), 735 warning(s), 856 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/entity_architecture.md, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3063/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOCENUM001@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, E501@/home/logan/projects/frob/.claude/worktrees/t-3052-series/src/frob/app/ticket_runner/_rapid_sweep.py, I001@/home/logan/projects/frob/.claude/worktrees/t-3052-series/src/frob/app/ticket_runner/_rapid_sweep.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF001@docs/strata/entity_architecture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@tests/unit/strata/entity_arch/storage_cheap.strata, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py
