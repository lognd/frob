---
id: T-4474
title: PassengerTickets fires on MOVED directives (5 false refusals in one day); compare
  directive identities, not diff lines
state: in-progress
kind: bug
origin: agent
created: '2026-09-13'
priority: high
parent: T-4410
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_passenger*.py
- src/frob/tickets/_land.py
- tests/unit/test_land_cross_ticket_leakage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-09-13, five lands in one day refused with PassengerTickets (T-1618): T-4443 (frob:ticket T-4431/T-4434 directives MOVED with the functions extracted to _native_staleness_digest.py), T-4465 (T-3935), T-4448 (T-1934), T-4179 (T-0991), and T-4463's sibling case; in every one the "passenger" was an existing directive line that the ticket's refactor moved, re-wrapped, or split across a helper extraction -- no other ticket's code rode along. The coordinator landed each with --allow-cross-ticket, which is the escape hatch T-1618 reserved for genuinely joint landings, so the guard now buys overrides instead of catching passengers (the unwaivable-error-buys-excuses shape). FIX: the passenger detector must compare directive IDENTITIES, not diff lines: a `frob:ticket T-XXXX` (or frob:tests / frob:doc naming another ticket) that appears as an addition is a passenger only if the SAME directive (same anchor symbol or same normalized text) is not also present in the base tree at any location -- a move, re-wrap, or split of an existing directive is not a passenger. Token/grammar comparison (parse the directive, compare (ticket id, kind, anchor)), never line-text diffing. ACCEPTANCE: (1) a unit test that moves a `frob:ticket T-OTHER` directive from one file to another in the branch asserts NO PassengerTickets finding; (2) a test that adds a brand-new `frob:ticket T-OTHER` directive still fires; (3) the refusal message lists, per id, whether the directive is new or moved. Sprint v0.532.0.
