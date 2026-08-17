## Done report

Changed:
- src/frob/tickets/_doable.py::_open_blockers (extended: self-heals against a narrowed IN_PROGRESS blocker's live lease)
- src/frob/tickets/_doable.py::_doable_candidates (threads `root` through to `_open_blockers`)

Evidence:
- tests/test_tickets.py::TestDoableStaleBlockedBySelfHeals::test_narrowed_in_progress_blocker_self_heals (BUG002 designated repro; verified FAILED_AT_PARENT at 1a0f7b7c322467fe5b87ab0da872e3f21c41ea23, PASSED after the fix)
- tests/test_tickets.py::TestDoableStaleBlockedBySelfHeals::test_still_overlapping_in_progress_blocker_still_blocks (must-still-pass control: narrowing-triggered self-heal, never a blanket bypass)
- tests/test_tickets.py::TestDoableStaleBlockedBySelfHeals::test_queued_blocker_never_self_heals_on_scope (must-still-pass control: a QUEUED blocker, no live lease, is never auto-cleared)

Filed: none

Scope note (deliberate narrowing of the ticket's own request): implemented as a READ-TIME reconciliation folded into `doable`'s own `_open_blockers` computation (one of the two options the ticket itself names), not a `blocked_by` ledger WRITE or a new `frob ticket unblock` verb. Two reasons: (1) a verb needs CLI-parser/AppConfig wiring outside this ticket's declared scope (`src/frob/tickets/_doable.py` alone); (2) `frob ticket block` is measured as a general dependency-ordering primitive with no reason field (`_block` in `_lifecycle.py` records ANY `--by` id unconditionally) -- unconditionally auto-clearing on scope-disjointness alone would silently discard a deliberate non-scope sequencing block the moment it happens to have no scope overlap, which could be immediately for an intentionally-generic dependency. The fix is therefore deliberately restricted to an IN_PROGRESS blocker (a QUEUED/PLANNED/BLOCKED blocker's edge is always left untouched, per test_queued_blocker_never_self_heals_on_scope) -- only an actively-worked, scope-leasing ticket has a "current live lease scope" to compare against in the first place, which is also the exact shape T-2076's own real incident took. The `blocked_by` field itself is never mutated on disk; this recomputes fresh on every `doable` call, so there is nothing to persist and no write-time race, mirroring T-2095's "may only ever be CLEARED, never newly created" reasoning one step further (nothing is even written).

Gates: `frob check --ticket T-2104` -- every actionable finding this ticket's own change touched (COV002 missing frob:ticket edges, SCOPE001 test file outside scope, PRE001 stale sweep, ruff-format drift) is fixed. Every other FAIL line in that run is repo-wide pre-existing debt unrelated to this change (per gate:scope-note: only gate:SCOPE/gate:PREWORK/COV002/TODO001/FMT/AFFECT are ticket-scoped).

### Changed
```
 src/frob/tickets/_doable.py | 76 ++++++++++++++++++++++++++++++++++-----
 tests/test_tickets.py       | 88 ++++++++++++++++++++++++++++++++++++++++++++-
 tickets/T-2104/ticket.md    | 17 +++++++--
 3 files changed, 170 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestDoableStaleBlockedBySelfHeals::test_narrowed_in_progress_blocker_self_heals` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestDoableStaleBlockedBySelfHeals::test_still_overlapping_in_progress_blocker_still_blocks` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestDoableStaleBlockedBySelfHeals::test_queued_blocker_never_self_heals_on_scope` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, AFFECT001@src/frob/tickets/_doable.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2104/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2104/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2104/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2104/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2104/tests/test_ticket_land.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
