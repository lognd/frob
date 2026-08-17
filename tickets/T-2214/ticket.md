---
id: T-2214
title: 'Nothing gates an oversized function at land time, so ARCH001 accumulates in
  exactly the files the fleet works most: 4 findings in _land_cmd.py, plus fleet_status.py,
  _new.py and telemetry.py'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
evidence_scope:
- tests/test_ticket_work_and_land_finish.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_new_over_threshold_function_refuses_the_land
- tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_pre_existing_over_threshold_function_merely_touched_does_not_refuse
- tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_an_unrelated_land_touching_no_python_files_is_unaffected
- tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_waived_over_threshold_function_does_not_refuse
- tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_empty_touched_set_is_a_no_op
designated_repro_test: tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_new_over_threshold_function_refuses_the_land
acceptance:
- text: 'Measured correlation between fleet activity and ARCH debt. ARCH001/ARCH103
    errors by file: src/frob/app/ticket_runner/_land_cmd.py 4, scripts/fleet_status.py
    1, src/frob/app/telemetry.py 1, src/frob/app/ticket_runner/_new.py 1. Lands touching
    those same files today: fleet_status.py 4, _land.py 3, _land_cmd.py 3, _new.py
    2. The debt concentrates exactly where the fleet works most -- no single land
    is unreasonable, the accumulation is. Concrete instance: scripts/fleet_status.py::ticket_readiness
    reached 80 lines (threshold 60) after seven separate lands in one day. This test
    MUST fail against current main.'
  evidence:
  - tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_new_over_threshold_function_refuses_the_land
  - tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_pre_existing_over_threshold_function_merely_touched_does_not_refuse
  - tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_an_unrelated_land_touching_no_python_files_is_unaffected
  - tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_waived_over_threshold_function_does_not_refuse
  - tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_empty_touched_set_is_a_no_op
- text: 'ARCH001 is a SIZE threshold, not a missing-directive family -- it cannot
    be expressed in T-2201''s _DOC_TEST_EDGE_FAMILIES (label, directive, waive_rule)
    shape, and T-2201''s author was right to parameterise the edge families and disclose
    ARCH as out of scope rather than force it in. This needs its own diff-scoped check:
    for each function the diff ADDS or MODIFIES, measure its post-diff length and
    decision count and refuse when the diff pushes it past threshold. Compare against
    the merge-base so a function already over threshold and merely touched is not
    blamed on this land.'
  evidence:
  - tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_new_over_threshold_function_refuses_the_land
  - tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_pre_existing_over_threshold_function_merely_touched_does_not_refuse
  - tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_an_unrelated_land_touching_no_python_files_is_unaffected
  - tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_waived_over_threshold_function_does_not_refuse
  - tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_empty_touched_set_is_a_no_op
- text: Do NOT reintroduce a full unscoped frob check at land time -- that is the
    ~208s cost T-1684 removed and T-2114/T-2201 correctly avoided by working from
    the diff alone. Do NOT refuse on a function that was ALREADY over threshold before
    the diff; that would block unrelated work in the busiest files and is exactly
    the global-vs-attributable mistake T-2198 just fixed for the TICK gate. Refuse
    only on what the landing diff itself made worse.
  evidence:
  - tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_pre_existing_over_threshold_function_merely_touched_does_not_refuse
  - tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_an_unrelated_land_touching_no_python_files_is_unaffected
  - tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_waived_over_threshold_function_does_not_refuse
  - tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_empty_touched_set_is_a_no_op
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Done report

Nothing gated an oversized function at land time, so ARCH001/ARCH103 debt
concentrated exactly in the files the fleet works most (_land_cmd.py,
fleet_status.py, _new.py, telemetry.py) -- no single land unreasonable,
the accumulation was.

ARCH001 is a SIZE threshold, not a missing-directive family, so it cannot
be expressed in T-2201's `_DOC_TEST_EDGE_FAMILIES` (label, directive,
waive_rule) table shape. Added its own diff-scoped check instead:
`_assert_diff_does_not_worsen_long_functions_pre_land`, wired into
`_land_core_prepare` right after the T-2114 doc/test-edge check, same
unconditional-across-every-profile posture.

`_new_or_worsened_long_functions_in_diff` reuses
`frob.arch._python._check_long_functions` (the SAME complexity-aware
detector `arch_gate` itself dispatches, long-AND-complex, not a
reimplementation) against each touched python file's CURRENT content and
the SAME file's content at the merge-base (`git show` written to a scratch
file so `frob.lang.raw_tree` can parse it identically). Refuses only a
function whose symref is over threshold NOW but was NOT already over
threshold at the merge-base -- a pre-existing over-threshold function
merely touched is never blamed on this land, the same global-vs-
attributable distinction T-2198 fixed for the TICK gate. A
`frob:waive ARCH001` directly above the def is honored (the same escape
hatch `arch_gate`/`frob.gates._match_waiver` already provide for this
exact rule), via the same `_frob_directive_block`/`_genuine_comment_lines`
machinery T-2114/T-2201 already use to distinguish a real directive from
a string literal that merely looks like one.

No full unscoped `frob check` reintroduced: two bounded `raw_tree` parses
per touched `.py` file, the same cost class T-2114's doc/test-edge check
already pays, not the ~208s T-1684 removed from the land critical path.

Two DSL/DRIFT issues surfaced and were fixed in a follow-up commit:
`frob:tests` directives must use the dotted `Class.method` form, not
`Class::method` (DRIFT002); a prose test comment that happened to start
with the literal text "frob:waive ARCH001" tripped DSL001 as an attempted
malformed directive and was reworded.

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py   | 203 ++++++++++++++++++++++++++++--
 tests/test_ticket_work_and_land_finish.py | 117 +++++++++++++++++
 tickets/T-2214/done-report.md             |  59 +++++++++
 tickets/T-2214/ticket.md                  |  32 ++++-
 4 files changed, 399 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_new_over_threshold_function_refuses_the_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_pre_existing_over_threshold_function_merely_touched_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_an_unrelated_land_touching_no_python_files_is_unaffected` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_waived_over_threshold_function_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_empty_touched_set_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2208/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2208/tests/test_ticket_work_and_land_finish.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2214, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
