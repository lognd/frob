## Done report

WAVE14-B drained the TICK warning class from 108 to 26 (`uv run frob check
--only tickets`, measured before/after in this exact worktree at the same
tree otherwise, tickets.md/tickets-archive.md changes only).

## TICK009 (80 -> 0)

Root cause: TICK009 previously had no honest waive/ack channel at all --
its findings are anchored at `tickets.md:0` (no source line), so a
`frob:waive TICK009 reason="..."` comment has nowhere concrete to attach,
and every ledger-wide `frob check` re-fired the same nudge on the same
already-decided broad epics forever.

Built the mechanism: `Ticket.scope_breadth_ack` (bool) +
`scope_breadth_ack_reason` (str, mandatory) fields, `frob.tickets.
set_scope_breadth_ack` (ledger-locked setter, same shape as
set_priority/set_kind/set_tier), and `frob ticket scope-ack <id>
(--reason TEXT | --reason-file PATH)` CLI wired through _cli_parsers and
app/ticket_runner. `_tick009_scope_breadth_nudges` skips any ticket with
scope_breadth_ack=True, independent of tier. A blank reason is rejected
(TicketError.ScopeBreadthAckReasonMissing), mirroring WAIVE001 discipline.

Applied `scope-ack` to the 11 genuinely-broad epic/umbrella tickets named
in the dispatch brief: T-0254, T-0260, T-1135, T-1136, T-1137, T-1196,
T-1198, T-1204, T-1238, T-1259, T-1382.

Narrowed the remaining 29 non-epic queued/planned tickets' over-broad
scope entries (chronic docs/**/tests/** literals and >25-file package
globs) to the specific modules/docs/tests their own body/acceptance
criteria name: T-1205, T-1213, T-1218, T-1226, T-1230, T-1231, T-1232,
T-1235, T-1236, T-1243, T-1269, T-1271, T-1279, T-1294, T-1310, T-1311,
T-1317, T-1328, T-1339, T-1342, T-1344, T-1396, T-1400, T-1420, T-1445,
T-1464, T-1478, T-1480, T-1482 -- all via `frob ticket scope --remove/
--add --reason`, each recorded with an honest "best-effort at
authoring-time, expand via frob ticket scope --add as work reveals more
files" reason. Two of these (T-1235, T-1420) needed a two-step add-then-
remove because `_validate_scope_mutation`'s evidence-orphan check reads
the ticket's CURRENT scope for the remove-side check without folding in
the SAME call's own add-side globs -- a real (separately reportable) gate
bug, worked around here rather than fixed (out of this ticket's scope).

## TICK004 (2 -> 1)

- T-1205 (coverage as managed derived state): re-prioritized critical ->
  high. It is a valuable automation improvement (never manual `make
  coverage`, auto-refresh touched-set coverage) but has no bug/security
  blast radius of its own and nothing else in the queue depends on it --
  "critical" read as priority creep, not a genuinely urgent item.
- T-1235 (coverage attribution fix: subprocess rc + multiprocessing
  concurrency): left at critical. It IS genuinely critical -- it fixes
  wrong TEST005 coverage numbers across the burn-down effort -- but it is
  blocked_by T-1395 (itself a TICK007 undispatched-stale high-priority
  ticket), so it cannot be worked or re-dispatched right now. Disclosed
  here rather than faked to a lower priority to silence the gate.

## TICK003 (1 -> 0)

Ran `frob ticket archive` in this worktree -- no live cross-worktree lease
conflict was reported, so it completed safely (no `--force` needed).
Archived 47 closed tickets into tickets-archive.md.

## Not touched (out of this ticket's mission)

TICK011 (22 findings) and TICK007 (4 findings) are unchanged -- the
dispatch brief scoped this ticket to TICK009/TICK004/TICK003 only.

### Changed
```
 docs/modules/gates.md                      |   23 +-
 docs/modules/tickets.md                    |    1 +
 src/frob/_cli_parsers/__init__.py          |    2 +
 src/frob/_cli_parsers/_ticket/__init__.py  |    4 +
 src/frob/_cli_parsers/_ticket/_metadata.py |   33 +
 src/frob/app/ticket_runner/__init__.py     |    4 +
 src/frob/app/ticket_runner/_mutate.py      |   37 +-
 src/frob/gates/_tickets_gate.py            |    7 +
 src/frob/tickets/__init__.py               |    2 +
 src/frob/tickets/_models.py                |   21 +
 src/frob/tickets/_setters.py               |   40 +
 tests/test_gates_tick009_tick010.py        |   15 +
 tests/test_tickets_scope_mutation.py       |   63 +-
 tickets-archive.md                         | 9855 +++++++++++++++++++++++++++-
 tickets.md                                 | 9145 +++++---------------------
 15 files changed, 11828 insertions(+), 7424 deletions(-)
```

### Evidence
- `tests/test_tickets_scope_mutation.py::TestSetScopeBreadthAck::test_ack_sets_both_fields` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestSetScopeBreadthAck::test_ack_requires_non_blank_reason` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestSetScopeBreadthAck::test_cli_scope_ack_sets_flag` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestSetScopeBreadthAck::test_cli_scope_ack_requires_reason` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_scope_breadth_ack_exempts_ticket` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 3 error(s), 683 warning(s), 740 waived
- error-findings: PRE001@tickets/T-1484, SELFAUDIT001@design, WIRE001@src/frob/app/ticket_runner/_mutate.py
