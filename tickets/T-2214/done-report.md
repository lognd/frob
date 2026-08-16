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
