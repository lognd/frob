## Done report

T-2104 (landed today, 353475ea) already added a read-time reconciliation to
`doable`/`doable_blocked`: an IN_PROGRESS blocker's `blocked_by` edge stops
counting once its LIVE lease scope has narrowed away from any overlap with
the blocked ticket's own scope. That is the fix direction (b)/(a) T-1984
itself asked for -- and the two concrete tickets this ticket's own
description named as starved (T-1638, T-1748) have both since reached a
terminal state (done/dropped respectively) independent of this work.

Investigating the remaining scope of T-1984 found a real, distinct gap
T-2104 did not close: `doable` listing a ticket as dispatchable is NOT the
same as `frob ticket start`/`transition(... IN_PROGRESS)` actually
accepting it. The QUEUED/PLANNED -> IN_PROGRESS transition guard
(`_transition_guard` in `src/frob/tickets/_evidence.py`) consults its own,
separate `_start_blockers` helper, which never threaded `root` through and
never consulted live lease scope at all -- so a ticket T-2104's self-heal
now lists in `doable` could still refuse to actually START with
`TicketError.BlockerOpen`. This is exactly the same defect class T-1984
filed, just at a second call site T-2104's own declared scope
(`src/frob/tickets/_doable.py` only) could not reach.

Fix: `_start_blockers` now delegates to `frob.tickets._doable._open_
blockers` (the SAME T-2104 reconciliation, reused rather than re-derived --
no duplicate logic) instead of its own independent open/closed check,
threading `root` through from `_transition_guard`/`transition`, both of
which already had it available. `root=None` (any caller with no repo root)
preserves the exact prior behavior unchanged.

No unblock CLI verb was added: same reasoning T-2104's own Done report
already gave for declining one (a verb needs CLI-parser/AppConfig wiring
outside `src/frob/tickets/`'s declared scope, and `frob ticket block` is a
general dependency-ordering primitive with no reason field, so a blanket
manual-clear escape hatch risks discarding a genuine non-scope dependency
edge) -- direction (a)/(b) alone, extended to the write-side transition
guard, closes the gap T-1984 measured without that risk.

Positive control: a genuine dependency block (an IN_PROGRESS blocker whose
scope STILL overlaps, and a QUEUED blocker with no live lease at all) keeps
refusing the start exactly as before -- narrowing-triggered self-heal only,
never a blanket bypass.

### Changed
```
 src/frob/tickets/_evidence.py | 32 ++++++++++++----
 tests/test_tickets.py         | 85 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-1984/ticket.md      | 33 +++++++++++++++--
 3 files changed, 139 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestStartHonorsSelfHealedBlockedBy::test_narrowed_in_progress_blocker_no_longer_blocks_start` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestStartHonorsSelfHealedBlockedBy::test_still_overlapping_in_progress_blocker_still_refuses_start` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestStartHonorsSelfHealedBlockedBy::test_queued_blocker_still_refuses_start_regardless_of_scope` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-1984/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1984/scripts/fleet_status.py, F841@/home/logan/projects/frob/.claude/worktrees/t-1984/tests/test_ticket_land.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK004@tickets.md
