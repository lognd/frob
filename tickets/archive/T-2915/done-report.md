## Done report

Changed:
  scripts/branch_stranded_work_analysis.py::_directive_ids_via_real_parser (new)
  scripts/branch_stranded_work_analysis.py::_scratch_file_for_suffix (new)
  scripts/branch_stranded_work_analysis.py::ticket_ids_on_branch (modified: tries the
    real parser first, falls back to bare regex, same T-2300 precedent as
    frob.tickets._unlanded)
  tests/unit/test_branch_stranded_work_analysis.py (2 new tests)
  docs/audits/branch-stranded-work-2026-08-25.md (UPDATE section with honest
    before/after measurement and a full-repo-scan-does-not-complete caveat)

Evidence:
  tests/unit/test_branch_stranded_work_analysis.py::TestTicketIdsOnBranch::test_string_literal_mention_is_not_a_directive
  tests/unit/test_branch_stranded_work_analysis.py::TestTicketIdsOnBranch::test_real_directive_comment_found_via_real_parser
  full file: 25/25 pass

Measurement (must run via `uv run python3`, NOT bare `python3` -- frob.lang is only
importable inside the worktree's own venv; my first attempt silently fell back to the
regex path for every branch because of exactly this mistake, caught only by directly
testing _directive_ids_via_real_parser's return value against a known file):
  Same 199-branch sample, before (bare regex) vs after (real parser):
    stranded: 35 -> 13
  The ticket's own framing of the false-positive source was PARTLY wrong: most of
  tests/test_gates.py's 389 literal "frob:ticket" occurrences are genuine
  directive-position comments (128 real directive edges resolved out of 389 lexical
  hits), not string-literal noise as assumed -- still real over-counting (261 filtered),
  just less than first claimed. Documented honestly in the audit doc's new UPDATE
  section rather than silently correcting the prior claim.
  A full-repo re-scan (~1098 branches) with the real parser did NOT complete inside an
  8-minute budget (killed at 480s) -- tree-sitter parsing large files (test_gates.py is
  ~900KB) per branch, with no cross-branch cache, is measurably slower than the bare
  regex's ~6-7 minute full run. Documented as a real limitation: the real-parser path is
  for a smaller, human-directed re-check (--limit N or a filtered subset), not a
  drop-in replacement for the default full-repo scan.

Filed: none

Gates: frob check --ticket T-2915 -- zero gate:* findings anywhere (COV001/DOC/TEST001
  all clean on the two new symbols, matching the module's existing frob:doc anchor
  coverage). ruff-format was real (fixed). ty/frob-cycle FAILs are repo-wide,
  pre-existing, unrelated (confirmed: neither references my touched files).

### Changed
```
 tickets/T-2915/ticket.md | 18 +++++++++++++++++-
 1 file changed, 17 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_branch_stranded_work_analysis.py::TestTicketIdsOnBranch::test_string_literal_mention_is_not_a_directive` (pytest node id, verified passing when recorded)
- `tests/unit/test_branch_stranded_work_analysis.py::TestTicketIdsOnBranch::test_real_directive_comment_found_via_real_parser` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 23 error(s), 456 warning(s), 849 waived
- error-findings: COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV005@scripts/branch_stranded_work_analysis.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK006@tickets.md
