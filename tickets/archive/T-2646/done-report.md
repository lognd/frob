## Done report

Changed:
  scripts/branch_stranded_work_analysis.py (new)
  tests/unit/test_branch_stranded_work_analysis.py (new, 23 tests)
  docs/audits/branch-stranded-work-2026-08-25.md (new)

Evidence:
  tests/unit/test_branch_stranded_work_analysis.py::TestClassifyBranch::test_merged_when_ancestor
  tests/unit/test_branch_stranded_work_analysis.py::TestClassifyBranch::test_ticket_done_when_all_ids_terminal
  tests/unit/test_branch_stranded_work_analysis.py::TestClassifyBranch::test_stranded_when_ticket_not_terminal
  tests/unit/test_branch_stranded_work_analysis.py::TestClassifyBranch::test_stranded_when_no_ticket_signal_but_real_diff
  full file: 23/23 pass

Filed:
  T-2915 -- re-run the classification with the real directive
    parser instead of the bare regex (the known false-positive source
    the audit doc documents)
  T-2914 -- T-2645's WIRE001 waiver on _unlanded.py::
    _remove_scratch_file is missing a follow_up attribute (WIRE002),
    discovered while running this ticket's gate check; out of T-2646's
    own scope, filed rather than fixed here

Gates: frob check --ticket T-2646 -- zero errors attributable to the
three new files after fixing (in order discovered): ruff E501s, a
missing WIRE001 follow_up N/A (not ours), a PERF003 nested-loop shape
(refactored to a single group-by pass, plus a waiver for the residual
bounded-size finding), a REF002 single-anchor finding (waived, dated
point-in-time audit snapshot), a DOC009 missing status header (added),
and a DOC011 dangling ticket citation (T-2756 was itself a directive-
regex false positive inside the report text -- removed the citation and
called out the irony explicitly in the doc). Every remaining FAIL in the
tool summary (ruff-check, gate:COV/DOC/LANG/TICK/WIRE) is repo-wide/
pre-existing and unrelated -- confirmed by grep, not assumed.

Scope declared: docs/guides/agent-playbook.md (default), plus
scripts/branch_stranded_work_analysis.py, docs/audits/branch-stranded-
work-2026-08-25.md, tests/unit/test_branch_stranded_work_analysis.py,
and the two draft ticket files filed from this worktree.

Measurement / classification result (1092 local branches scanned
against main, 2026-08-25, ~5m48s wall clock):
  merged:      258
  ticket-done: 646
  stranded:    188 (NEVER auto-deleted; per-branch detail in the audit
               doc, with an explicit, measured false-positive-rate
               caveat on the bare-regex directive signal -- see the
               doc's own "IMPORTANT" section)
  error:         0

No branch was deleted, and no deletion mechanism was built -- per this
ticket's own instruction, this is the analysis step only. The
highest-confidence stranded set (26 branches, zero ticket signal + a
small diff) is listed individually in the audit doc for a human
decision; the majority of the 188 are very likely false positives from
the bare-regex directive scan matching test-fixture strings (measured:
tests/test_gates.py alone carries 389 literal "frob:ticket" occurrences
in its own fixtures) -- T-2915 covers sharpening this with the
real parser.

### Changed
```
 tickets/T-2646/ticket.md           | 40 ++++++++++++++++++++++++++++++-
 tickets/T-2914/ticket.md | 41 ++++++++++++++++++++++++++++++++
 tickets/T-2915/ticket.md | 48 ++++++++++++++++++++++++++++++++++++++
 3 files changed, 128 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_branch_stranded_work_analysis.py::TestClassifyBranch::test_merged_when_ancestor` (pytest node id, verified passing when recorded)
- `tests/unit/test_branch_stranded_work_analysis.py::TestClassifyBranch::test_ticket_done_when_all_ids_terminal` (pytest node id, verified passing when recorded)
- `tests/unit/test_branch_stranded_work_analysis.py::TestClassifyBranch::test_stranded_when_ticket_not_terminal` (pytest node id, verified passing when recorded)
- `tests/unit/test_branch_stranded_work_analysis.py::TestClassifyBranch::test_stranded_when_no_ticket_signal_but_real_diff` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 21 error(s), 441 warning(s), 847 waived
- error-findings: COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC008@docs/commands/check.md, I001@/home/logan/projects/frob/.claude/worktrees/t-2645-series/tests/unit/verify/test_backpressure.py, LANG003@src/frob/lang (facet=capability), LANG003@src/frob/lang (facet=docblock), LANG003@src/frob/lang (facet=dup), TICK004@tickets.md, WIRE002@src/frob/tickets/_unlanded.py
