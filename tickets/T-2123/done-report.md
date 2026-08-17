## Done report

Changed:
- src/frob/tickets/_new_renumber.py::new_ticket (wired the new filing-time warning call in)
- src/frob/tickets/_new_renumber.py::_warn_over_broad_scope_on_new (new)
- src/frob/tickets/_new_renumber.py::_worst_over_broad_multiple (new)
- src/frob/tickets/_new_renumber.py::_CATASTROPHIC_SCOPE_MULTIPLE (new)

Evidence:
- tests/unit/test_new_ticket_over_broad_scope_warning.py::TestWarnOverBroadScopeOnNew::test_over_broad_scope_warns_at_filing_time (BUG002 designated repro; verified FAILED_AT_PARENT at 18565c7b113cd36ff9bfcaffa337a3db527de1d0, PASSED after the fix)
- tests/unit/test_new_ticket_over_broad_scope_warning.py::TestWarnOverBroadScopeOnNew::test_precise_scope_is_silent_at_filing_time (must-still-pass control)
- tests/unit/test_new_ticket_over_broad_scope_warning.py::TestWarnOverBroadScopeOnNew::test_ack_bypasses_the_warning
- tests/unit/test_new_ticket_over_broad_scope_warning.py::TestWarnOverBroadScopeOnNew::test_severity_scales_with_a_catastrophic_match_count (the second, "8 shown of 614" T-2123 finding)

Filed: none

Scope note: this is a WARN-only extension, not a hard refusal like T-1866's start-time enforcement. A brand-new ticket being filed has no id yet to acknowledge via `frob ticket scope-ack`, so refusing filing outright would strand the author mid-command with no way forward inside the same invocation. A `frob ticket new --scope-breadth-ack` flag would close this circularity fully but needs `AppConfig`/CLI-parser changes outside this ticket's own declared scope (`src/frob/tickets/_new_renumber.py` alone) -- noted here rather than worked around silently; a follow-up ticket for that CLI flag is worth filing if the WARN-only posture proves insufficient in practice.

Gates: `frob check --ticket T-2123` -- every actionable finding this ticket's own change touched (E501, unsorted import, ruff-format drift, SCOPE001 test file outside scope, PRE001 stale sweep) is fixed. LARGE001 on this file (1472 lines, threshold 800) is pre-existing debt (already 1363 lines / already over threshold before this ticket's own 109-line addition) -- this ticket adds to it but is not its cause and fixing it is out of scope. Every other FAIL line in that run is repo-wide pre-existing debt unrelated to this change (per gate:scope-note: only gate:SCOPE/gate:PREWORK/COV002/TODO001/FMT/AFFECT are ticket-scoped).

### Changed
```
 src/frob/tickets/_new_renumber.py                  | 119 ++++++++++++++++-
 .../test_new_ticket_over_broad_scope_warning.py    | 148 +++++++++++++++++++++
 tickets/T-2123/ticket.md                           |  18 ++-
 3 files changed, 280 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_new_ticket_over_broad_scope_warning.py::TestWarnOverBroadScopeOnNew::test_over_broad_scope_warns_at_filing_time` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_over_broad_scope_warning.py::TestWarnOverBroadScopeOnNew::test_precise_scope_is_silent_at_filing_time` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_over_broad_scope_warning.py::TestWarnOverBroadScopeOnNew::test_ack_bypasses_the_warning` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_over_broad_scope_warning.py::TestWarnOverBroadScopeOnNew::test_severity_scales_with_a_catastrophic_match_count` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2123/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2123/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2123/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2123/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2123/tests/test_ticket_land.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
