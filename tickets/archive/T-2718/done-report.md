## Done report

decided option (b): the fixed Tier-A generated headings (Changed/Evidence/Captured claims/Acceptance amendments) are now an exact-title allowlist exempt from the structural disclosure signal in disclosure_shaped_language; renaming any of the four, or adding any other subsection, still fires exactly as it did before this change. The phrase-match signal is completely unaffected.

### Changed
```
 docs/modules/tickets-data-storage.md         | 21 +++++++
 docs/modules/tickets-landing.md              | 42 ++++++++++++++
 src/frob/tickets/_land.py                    | 64 +++++++++++++++++++-
 src/frob/tickets/_reporting.py               | 60 ++++++++++++++++---
 tests/unit/test_land_already_landed.py       | 87 ++++++++++++++++++++++++++++
 tests/unit/test_reporting_t1648_remainder.py | 64 ++++++++++++++++++++
 tickets/T-2711/done-report.md                | 21 +++++++
 tickets/T-2711/ticket.md                     | 23 +++++++-
 tickets/T-2718/done-report.md                | 29 ++++++++++
 tickets/T-2718/ticket.md                     | 26 ++++++++-
 tickets/T-2726/ticket.md           | 53 +++++++++++++++++
 11 files changed, 476 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage::test_tier_a_generated_report_with_no_real_followup_closes_clean` (pytest node id, verified passing when recorded)
- `tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage::test_tier_a_generated_report_with_captured_claims_and_amendments_closes_clean` (pytest node id, verified passing when recorded)
- `tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage::test_genuine_hand_typed_subheading_alongside_generated_ones_still_fires` (pytest node id, verified passing when recorded)
- `tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage::test_renaming_a_generated_heading_still_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 44 error(s), 909 warning(s), 679 waived
- error-findings: ARCH001@src/frob/tickets/_land.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2718, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
