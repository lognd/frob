## Done report

T-1856 implements the first-class anchor marker item 2 of T-1853 left
open, within its declared scope (src/frob/tickets/_models.py,
src/frob/tickets/_land.py):

1. `Ticket.anchor: bool` + `Ticket.anchor_reason: str | None`
   (src/frob/tickets/_models.py) -- declared intent, not inferred body
   prose. `TicketError.AnchorReasonMissing` and
   `LandError.AnchorTerminalLand` added alongside, mirroring the
   scope_breadth_ack/ScopeBreadthAckReasonMissing precedent (T-1484).

2. `set_anchor(root, ticket_id, *, anchor, reason)`
   (src/frob/tickets/_land.py) -- library-level set/clear in one
   ledger-locked write, rejecting a blank reason the same way
   `set_scope_breadth_ack` does.

3. `_refuse_anchor_terminal_land` (src/frob/tickets/_land.py), wired as
   the FIRST check in `_land_precheck_remaining_checks` -- an
   unconditional refusal to land an `anchor=True` ticket to
   done/dropped, independent of whether any live-tracker citation
   currently resolves (the structural fix `_check_live_tracker_
   citations`'s diff-aware grep alone cannot provide: it only fires when
   citations are found, and only a human/agent reading prose knew this
   ticket must never close). This directly closes the T-1820 near-miss
   T-1853's body documents.

NOT done here, out of this ticket's declared scope -- filed as a
follow-up draft (renumbers at land):
- CLI wiring (`frob ticket anchor <id> --set/--clear --reason TEXT`):
  needs src/frob/app/ticket_runner/_mutate.py +
  src/frob/_cli_parsers/_ticket/_metadata.py, neither declared for
  T-1856.
- `frob ticket doable` output disclosure: needs
  src/frob/tickets/_doable.py, explicitly off-limits this session
  (another agent held it), plus src/frob/app/ticket_runner/_query.py.
- T-1820/T-1831 (the live anchor examples) have NOT had `set_anchor` run
  against them yet -- the mechanism exists but is not yet applied to the
  real anchors it protects; the follow-up notes this.

### Changed
```
 tickets/T-1856/ticket.md           | 17 +++++++++++-
 tickets/T-1867/ticket.md | 57 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 73 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_live_tracker.py::TestAnchorMarker::test_terminal_land_refused` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestAnchorMarker::test_non_terminal_land_not_refused` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestAnchorMarker::test_non_anchor_terminal_land_not_refused` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestAnchorMarker::test_set_anchor_requires_reason` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestAnchorMarker::test_set_anchor_round_trips` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 10 error(s), 937 warning(s), 748 waived
- error-findings: COV001@.claude/hooks/_shellscan.py, COV001@.claude/hooks/diagnosis-nudge.py, COV001@.claude/hooks/dispatch-telemetry.py, COV001@.claude/hooks/frob-suggest.py, COV001@.claude/hooks/frob-timeout-guard.py, COV001@.claude/hooks/sync-claude-config.py, COV001@design/frob.strata, DOC003@docs/commands/sys.md, SELFAUDIT001@design, TEST001@.claude/hooks/_shellscan.py
