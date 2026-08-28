## Done report

Fixed the CrossTicketLeakage sibling-attribution scan
(_leaked_hits_for_candidate, src/frob/tickets/_land.py) so a sibling
ticket that merely DECLARES scope over a path it never actually
committed a change to no longer misattributes a hit for that path.

Before this fix, a hit only required: (1) the path matches other's
DECLARED scope glob, (2) other's own LEDGER RECORD moved at all since
the fork (T-1390's existing check, proving "was worked on SOMEWHERE",
not "touched THIS path"). A genuinely active sibling with a broad,
honest scope declaration (e.g. src/**) that simply never edited a
specific overlapping file still misattributed a hit -- the exact
incident: T-1608/1609/1661/2936/2944 merely declared scope over
tests/unit/test_process_reap.py without editing it, blocking T-2930's
`--force` re-staged, actually-correct content.

Fix: `_drop_hits_other_branch_never_touched` (new), called from
`_leaked_hits_for_candidate` after the existing T-1855 wiring-grant
filter -- resolves `other_id`'s own live branch via the cross-worktree
lease side-channel (`_sibling_branch_ref`, the SAME `read_all_leases`
`_effective_leakage_scope` already reads) and drops any hit path that
branch's own content, compared against root's CURRENT tip, shows NO
real difference for (`_sibling_branch_touched_path`). Deliberately
CONSERVATIVE: any ambiguous case (branch unresolvable, path new to
BOTH sides, path present on root but absent from other's branch) keeps
the hit -- this can only ever NARROW an existing refusal, never widen
a gap.

Note on the "brand-new file" edge case: the first version of this fix
treated "neither side has ever seen this path" as safe-to-exempt, which
broke the EXISTING `test_refuses_when_sibling_ticket_still_open`
regression test (a synthetic leak where held_id's ledger record and a
copied file both land on the LANDING branch, but held_id's own REAL
branch never carries the file at all -- a real leak this per-path
narrowing must never wave through just because the file is new to both
refs). Tightened: only "both present, identical" or "other has it, root
doesn't" ever narrow; "neither has it" now stays a hit (`None`,
conservative), matching the real T-2948 incident shape anyway (an
EXISTING file like test_process_reap.py, not a brand-new one).

Proof:
- must-fire: `test_sibling_actively_worked_but_never_touched_the_overlapping_path_does_not_block`
  -- a genuinely IN_PROGRESS, real-commits sibling in a DIFFERENT
  worktree, with a broad declared scope covering a PRE-EXISTING shared
  file it never edits; the landing ticket's own edit to that file no
  longer blocks. Confirmed FAILING at parent (--check-repro against
  48b52808b, the test-committed-alone-first commit) before the fix,
  PASSING after.
- must-still-refuse: `test_sibling_actively_worked_and_genuinely_touched_the_overlapping_path_still_refuses`
  -- the mirror case, same sibling, but its own branch ALSO genuinely
  edits the overlapping path -- still refuses with CrossTicketLeakage.
- Existing coverage unaffected: the full
  `tests/unit/test_land_cross_ticket_leakage.py` module (24 tests,
  including the T-1355/T-1370/T-1390/T-1639/T-1855/T-1967/T-2111/T-2547
  regression suite this scan already carried) plus
  `tests/unit/test_land_machinery_owned_leakage.py` and
  `tests/unit/test_land_step_ordering.py`'s post-mutation recheck suite
  (29 tests total) all run clean -- specifically confirming the real
  T-1352/T-1276 leak-via-bad-merge incident this module exists for is
  STILL caught (`test_refuses_when_sibling_ticket_still_open`), which
  the first draft of this fix regressed and this final version restores.

Filed: none.

### Changed
```
 src/frob/tickets/_land.py                    | 123 +++++++++++++++++++++++++
 src/frob/tickets/_land_git_ops.py            | 128 +++++++++++++++++++++++++--
 tests/test_ticket_land.py                    | 113 +++++++++++++++++++++++
 tests/unit/test_land_cross_ticket_leakage.py | 117 ++++++++++++++++++++++++
 tickets/T-2947/done-report.md                |  86 ++++++++++++++++++
 tickets/T-2947/ticket.md                     |  10 ++-
 tickets/T-2948/ticket.md                     |  15 +++-
 7 files changed, 583 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_actively_worked_but_never_touched_the_overlapping_path_does_not_block` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_actively_worked_and_genuinely_touched_the_overlapping_path_still_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_refuses_when_sibling_ticket_still_open` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_declaring_broad_scope_but_untouched_does_not_block` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 25 error(s), 939 warning(s), 855 waived
- error-findings: COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, LARGE001@src/frob/stats/_agentic.py, PRE001@tickets/T-2948, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
