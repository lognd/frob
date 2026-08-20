## Done report

### Changed
- src/frob/tickets/_reporting.py::disclosure_shaped_language -- signal 1 (the `_DISCLOSURE_PHRASES` scan) now scans `_done_report_section(text)` instead of the whole `text`, matching signal 2's existing scope. Docstring updated to record the T-2726 reasoning: a ticket's description legitimately discusses its own subject matter; the Done report is where a hedged completion claim actually matters.

### Evidence
- tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage::test_phrase_in_description_before_done_report_is_not_flagged (new positive control mirroring T-2718's own incident: a description quoting a disclosure phrase does not block a clean Done report)
- tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage::test_phrase_in_done_report_still_fires (new positive control: a genuine hedged phrase inside the Done report still fires)
- tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage::test_detects_known_phrase and test_case_insensitive updated to scope the phrase under a Done report heading
- tests/unit/test_close_t1648_remainder.py: TestRemainderDisclosureGuard suite re-run clean end to end
- Full existing suite in both files re-run clean (21 passed), including the T-2638 Tier-A heading exemption tests, unchanged
- frob check --ticket T-2726 --no-cache: SCOPE001/PRE001 clean
- frob test --base main: PASS exit=0

Filed: none

### Changed
```
 tickets/T-2726/done-report.md | 34 ++++++++++++++++++++++++++++++++++
 tickets/T-2726/ticket.md      | 26 ++++++++++++++++++++++++--
 2 files changed, 58 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage::test_phrase_in_description_before_done_report_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage::test_phrase_in_done_report_still_fires` (pytest node id, verified passing when recorded)
- `tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage::test_detects_known_phrase` (pytest node id, verified passing when recorded)
- `tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage::test_case_insensitive` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_t1648_remainder.py::TestRemainderDisclosureGuard::test_clean_narrative_is_unaffected` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_t1648_remainder.py::TestRemainderDisclosureGuard::test_refuses_when_disclosure_language_has_no_filed_ticket` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 44 error(s), 914 warning(s), 678 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
