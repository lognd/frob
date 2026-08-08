---
id: T-1811
title: Exact-duplicate ticket refusal at frob ticket new time (T-1744 case 2)
state: done
kind: feature
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_models.py
- tests/test_tickets.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets.py::TestNewTicketExactDuplicateRefusal::test_exact_title_and_scope_match_is_refused
- tests/test_tickets.py::TestNewTicketExactDuplicateRefusal::test_scope_order_does_not_evade_the_match
- tests/test_tickets.py::TestNewTicketExactDuplicateRefusal::test_different_title_is_not_a_duplicate
- tests/test_tickets.py::TestNewTicketExactDuplicateRefusal::test_different_scope_is_not_a_duplicate
- tests/test_tickets.py::TestNewTicketExactDuplicateRefusal::test_dropped_duplicate_does_not_block_refiling
- tests/test_tickets.py::TestNewTicketExactDuplicateRefusal::test_unreadable_ledger_does_not_block_filing
designated_repro_test: null
threat: null
component: null
---
Case 2 of T-1744 ("Detect a queued ticket whose described fix already
landed outside the ticket workflow"), split into its own ticket because
T-1744's own three acceptance criteria are written entirely against
cases 1/3 (fix-already-landed, premise-already-false) and none of them
resolve against case 2's evidence -- forcing this work under T-1744's
own id would either leave real acceptance criteria permanently unbound
or require binding evidence to criteria it does not actually satisfy.

Implements exact-duplicate refusal at `frob ticket new` time, per the
coordinator's priority ordering (case 2 first): six duplicate tickets
(exact title AND exact scope, including two triplicates) reached the
queue on 2026-08-07 before being caught and dropped by hand -- 5%
phantom backlog, with nothing in the tool comparing a new ticket
against existing ones.

`_find_exact_duplicate`/`_refuse_exact_duplicate`
(src/frob/tickets/_new_renumber.py) refuse with the new
`TicketError.DuplicateTicket` (src/frob/tickets/_models.py) when an
existing, non-`dropped` ticket has the EXACT same title (string
equality) and EXACT same scope (set equality, order-independent).
HIGH-PRECISION ONLY per the hard constraint: no fuzzy/similarity
matching -- this repo files near-identical titles for genuinely
distinct follow-ups constantly, and a fuzzy matcher would refuse
legitimate work at creation time, which is far more damaging than
letting an occasional true duplicate through. `dropped` tickets are
excluded (circumstances change). Fails OPEN on an unreadable ledger.

T-1744 itself stays open for cases 1 (fix-already-landed) and 3
(premise-already-false), which still need their own design pass.

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
