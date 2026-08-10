## Done report

Implements T-1744 case 2 (duplicate detection at `frob ticket new`
time). See ticket body for the split-off rationale.

`_find_exact_duplicate`/`_refuse_exact_duplicate`
(src/frob/tickets/_new_renumber.py) refuse `new_ticket` with the new
`TicketError.DuplicateTicket` (src/frob/tickets/_models.py) when an
existing, non-`dropped` ticket has the EXACT same title (string
equality) and EXACT same scope (set equality, order-independent).
HIGH-PRECISION ONLY: no fuzzy/similarity matching. `dropped` tickets
excluded. Fails OPEN on an unreadable ledger.

6 tests passing. T-1744 stays open (requeued) for cases 1/3 -- carried
forward: the "already landed" check must verify CODE presence on main,
never trust `state: done` alone (T-1508 proof).

ARCH001 on `new_ticket` (130+ lines) is PRE-EXISTING on main, confirmed
before this ticket touched the file.

No root-cause fix needed under DEAD001/WIRE001/OPAQUE001/REF002.

### Changed
```
 tickets/T-1811/ticket.md | 59 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 59 insertions(+)
```

### Evidence
- `tests/test_tickets.py::TestNewTicketExactDuplicateRefusal::test_exact_title_and_scope_match_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestNewTicketExactDuplicateRefusal::test_scope_order_does_not_evade_the_match` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestNewTicketExactDuplicateRefusal::test_different_title_is_not_a_duplicate` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestNewTicketExactDuplicateRefusal::test_different_scope_is_not_a_duplicate` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestNewTicketExactDuplicateRefusal::test_dropped_duplicate_does_not_block_refiling` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestNewTicketExactDuplicateRefusal::test_unreadable_ledger_does_not_block_filing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 3 error(s), 952 warning(s), 732 waived
- error-findings: ARCH001@src/frob/tickets/_new_renumber.py, invalid-assignment@tests/test_ticket_land.py, invalid-return-type@src/frob/tickets/_new_renumber.py
