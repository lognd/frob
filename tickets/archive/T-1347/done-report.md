## Done report

frob ticket brief already assembled body+acceptance, scope+leases,
playbook hard rules, verify commands, gate baseline, and REL/land rules,
but omitted the one thing a coordinator still had to hand-type under
concurrent dispatch: the scopes of OTHER in-progress tickets.

Added a "Concurrent leases (do NOT touch)" section (compose_brief,
_concurrent_leases_section) listing every OTHER in-progress ticket id,
title, and scope globs, resolved live at brief time from the loaded
TicketQueue (brief_ticket now filters queue.tickets.values() for
state==IN_PROGRESS and id != the briefed ticket). Empty when no other
ticket is in-progress -- no section printed.

Also added a fixed "Concurrency hazards" section folding in the two
hazards the ticket body named: commit new/changed tests BEFORE running
frob ticket land (T-1338 garbled-file + git-checkout-eats-uncommitted-
work incident), and that a transient DirtyMain refusal under concurrency
is expected -- wait and retry, never touch main by hand.

Split compose_brief Scope+leases and Playbook-hard-rules blocks into
their own small helpers (_scope_and_leases_section,
_playbook_hard_rules_section) to keep compose_brief under the ARCH001
60-line threshold once the two new sections were added; behavior
unchanged, same lines emitted in the same order.

Scope widened from the original (_brief.py, docs/modules/tickets.md) to
also include src/frob/tickets/_reporting.py (brief_ticket, the
compose_brief caller wired to pass the concurrent-tickets tuple) and
tests/test_tickets_brief.py (the test file for all of this), via frob
ticket scope --add.

### Changed
```
 tickets.md | 25 ++++++++++++++++++++++---
 1 file changed, 22 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_tickets_brief.py::TestConcurrentLeases::test_lists_others` (pytest node id, verified passing when recorded)
- `tests/test_tickets_brief.py::TestBriefTicket::test_concurrent_leases` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 4 error(s), 589 warning(s), 706 waived
- error-findings: INV006@src/frob/app/__init__.py, INV006@src/frob/app/app.py, SELFAUDIT001@design, TICK003@tickets.md
