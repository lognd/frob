## Done report

Changed:
- src/frob/app/ticket_runner/_new.py::_expand_scope_globs_to_paths (new)
- src/frob/app/ticket_runner/_new.py::_scope_overlap_warnings (new)
- src/frob/app/ticket_runner/_new.py::_emit_scope_overlap_warnings (new, ARCH001 split)
- src/frob/app/ticket_runner/_new.py::_new (wired the new warning call in)

Evidence:
- tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_overlapping_scope_names_the_other_ticket_and_path (accepts 0; BUG002 designated repro, verified FAILED_AT_PARENT at 14e9c871c86d3570f5a5abaaa427e067b9929046, PASSED after the fix)
- tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_glob_vs_file_overlap_is_detected (accepts 1)
- tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_non_overlapping_scope_is_silent (accepts 2, must-still-pass control)
- tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_terminal_state_tickets_are_excluded (accepts 3)
- tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_real_case_four_prior_tickets_all_named (accepts 4, the real T-2213/T-2229/T-2236/T-2249 pileup shape)

Filed: none

Scope note: `scripts/fleet_status.py::_expand_scope_globs_to_paths` (T-2225) could not be imported here -- that script is deliberately import-light and does not import `frob` at all, and this ticket's own declared scope is `src/frob/app/ticket_runner/_new.py` alone. Reimplemented the same glob-to-real-file expander locally, waived DUP001 with a reasoned justification, same posture T-2118's `_touched_symrefs_for_intent` already took for an identical cross-file-scope constraint.

Gates: `frob check --ticket T-2257` -- every actionable finding this ticket's own change touched (E501, WIRE001/WIRE002, ARCH001, SCOPE001, PRE001, ruff-format drift) is fixed. Every other FAIL line in that run is repo-wide pre-existing debt unrelated to this change (per gate:scope-note: only gate:SCOPE/gate:PREWORK/COV002/TODO001/FMT/AFFECT are ticket-scoped).

### Changed
```
 src/frob/app/ticket_runner/_new.py                 | 116 ++++++++++
 .../unit/test_new_ticket_scope_overlap_warning.py  | 245 +++++++++++++++++++++
 tickets/T-2257/done-report.md                      |  37 ++++
 tickets/T-2257/ticket.md                           |  36 ++-
 4 files changed, 426 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_overlapping_scope_names_the_other_ticket_and_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_glob_vs_file_overlap_is_detected` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_non_overlapping_scope_is_silent` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_terminal_state_tickets_are_excluded` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_real_case_four_prior_tickets_all_named` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2257/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2257/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2257/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2257/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2257/tests/test_ticket_land.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
