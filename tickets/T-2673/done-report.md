## Done report

Changed:
- src/frob/gates/_docenum.py::_ID_TOKEN_RE

Evidence:
- tests/test_docenum_gate.py::TestDocenum001HyphenatedLetterSuffixIds::test_hyphenated_letter_suffix_id_with_doc_row_does_not_fire (designated repro, FAILED_AT_PARENT at ff8311f48)
- tests/test_docenum_gate.py::TestDocenum001HyphenatedLetterSuffixIds::test_hyphenated_letter_suffix_id_with_no_doc_row_still_fires (reverse control)

Control results (re-verified after merging main, which brought in T-2670's 78
new gates.md doc rows and T-2668's gate-summary parser fix):
- Before fix: PORT001-IDENT/PORT001-PATH neither matched the old
  _ID_TOKEN_RE (verified directly against the old pattern) -- DOCENUM001's
  undocumented-member warning for docs/modules/gates.md:13 listed exactly
  these two ids.
- After fix (post-merge tree, T-2670's real rows present): both ids match;
  `_documented_ids(gates.md text)` contains both; `frob check --only
  docstatus` runs gate:DOCENUM clean, 0 errors.
- Reverse control: removing the PORT001-IDENT doc row from gates.md makes
  PORT001-IDENT reappear as undocumented while PORT001-PATH (row untouched)
  still counts -- proves the rows are load-bearing, not that the pattern
  just got looser overall.
- Over-widening check: compared old vs new regex against a batch of plain-
  prose hyphenated tokens (SOME-WORD, ABOUT-THIS, THE-QUICK-BROWN,
  FOO-BAR-BAZ, etc.) -- identical matches both before and after; the only
  newly-admitted tokens are digit-ending-prefix + letter-starting-suffix
  shapes (PORT001-IDENT, PORT001-PATH, SEC001-CVE, A1-B), exactly the
  RULEID-SUFFIX class this ticket targets.

Filed: none (no out-of-scope work found)

Gates: frob check --ticket T-2673 and frob check --only docstatus both
clean re gate:DOCENUM (0 errors, 7 pre-existing repo-wide warnings
unrelated to this change). Other FAIL lines in the ticket-scoped run
(DRIFT, PERF, etc.) are pre-existing repo-wide baseline findings unrelated
to _docenum.py, confirmed via gate:scope-note disclosure.

### Changed
```
 src/frob/gates/_docenum.py    | 14 +++++++++-
 tests/test_docenum_gate.py    | 59 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2673/done-report.md | 35 +++++++++++++++++++++++++
 tickets/T-2673/ticket.md      |  9 +++++--
 4 files changed, 114 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_docenum_gate.py::TestDocenum001HyphenatedLetterSuffixIds::test_hyphenated_letter_suffix_id_with_doc_row_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_docenum_gate.py::TestDocenum001HyphenatedLetterSuffixIds::test_hyphenated_letter_suffix_id_with_no_doc_row_still_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 44 error(s), 734 warning(s), 697 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
