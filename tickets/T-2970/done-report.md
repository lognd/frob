## Done report

Changed:
- src/frob/dup/_legacy.py::_MIN_LINES_OVERRIDES (new constant: tests/ -> 20)
- src/frob/dup/_legacy.py::_effective_min_lines (new helper)
- src/frob/dup/_legacy.py::_index_function/_scan_py_file/_scan_cpp_file/_scan_tree/find_duplicates
  (threaded min_lines_overrides through, defaulting to _MIN_LINES_OVERRIDES so
  every existing caller -- frob check's dup stage, the frob dup CLI, frob.gates
  prework/arch -- gets the narrowed tests/ behavior automatically)
- docs/modules/dup.md (new "tests/ directory floor (T-2970)" section)
- tests/unit/test_dup.py::TestTestsDirectoryFloor (2 new tests: the retirement
  case and the REQUIRED positive control)

Disposition: directory-scoped min_lines override (candidate 1 from the ticket
body), not the fixture-shape heuristic -- lower implementation cost, and the
measured size distribution (81% of the tests/ population under 20 lines) made
a simple floor sufficient without a new AST-shape classifier.

Positive control (REQUIRED before landing, per the playbook's "positive
control or it proves nothing"):
tests/unit/test_dup.py::TestTestsDirectoryFloor::test_genuine_helper_duplicate_at_20_lines_still_fires
plants a real 20+-line assertion-sequence helper (ticket-shape validation
logic, not fixture literals) copied verbatim into two different tests/ files
and asserts find_duplicates still reports it as a group under the narrowed
default -- proving the narrowing does not blind the detector to genuine
tests/ duplication, only to sub-20-line fixture noise. The companion test
(test_short_fixture_style_duplicate_under_tests_is_no_longer_a_group) proves
the SAME synthetic fixture-shaped duplicate is retired under the new default
but still fires with min_lines_overrides=() (the pre-T-2970 unscoped
behavior), confirming the retirement is caused by the override, not an
unrelated regression.

Re-measured (uv run frob check --json --only static, tool=="frob-dup",
every location under tests/, not already "[waived"):
- Before (T-2955's measurement baseline, re-confirmed at ticket start): 480
  unaccounted groups, all clone_type="renamed" (0 exact among the tests/
  unwaived population at either measurement).
- After: 64 unaccounted groups, all clone_type="renamed", all >=20 lines
  (T-2955's 4 sampled groups -- test_arch.py x2, test_litmus_waive vs
  test_litmus_waive_store, test_gates.py, test_dup.py -- are among the
  standing 64, still individually reviewable, not silently exempted).
- Retired: 431 groups (89.8%). Full retired-message list captured during
  this ticket's work (available on request; omitted here for length -- every
  retired group's largest fragment was under the new 20-line tests/ floor).

Filed: none. The 64 remaining tests/ groups are disclosed residue, not
driven to zero (T-2970's acceptance explicitly allows "a measured reduction
... reported", not zero) -- no follow-up ticket filed per the coordinator's
explicit "do NOT force it to zero" instruction; the residue count and
composition (all >=20 lines) is recorded here for whoever picks up the next
pass.

Gates: `uv run frob check --json --only static` re-measured clean of new
errors from this change; src/frob/gates cluster (T-2966, landed earlier in
this series) remains at 0 unaccounted after this land, confirmed by the same
measurement pass.

### Changed
```
 docs/modules/dup.md      | 33 ++++++++++++++++
 src/frob/dup/_legacy.py  | 75 +++++++++++++++++++++++++++++++++---
 tests/unit/test_dup.py   | 99 ++++++++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2970/ticket.md | 11 +++++-
 4 files changed, 210 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/unit/test_dup.py::TestTestsDirectoryFloor::test_short_fixture_style_duplicate_under_tests_is_no_longer_a_group` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup.py::TestTestsDirectoryFloor::test_genuine_helper_duplicate_at_20_lines_still_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 30 error(s), 685 warning(s), 854 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2962/ticket.md, DOC008@docs/commands/check.md, F401@/home/logan/projects/frob/.claude/worktrees/t-2966-2970/src/frob/gates/_lexical_selfcheck.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2966-2970/src/frob/gates/_port_selfcheck.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/serve/_socketd.py, PRE001@tickets/T-2970, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
