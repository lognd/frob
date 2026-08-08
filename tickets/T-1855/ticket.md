---
id: T-1855
title: Disclose implicit CLI-wiring scope in ticket show and CrossTicketLeakage refusal
state: queued
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_query.py
- src/frob/_cli_parsers/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1848 narrowed the implicit FEATURE CLI-wiring grant in _models.py (CLI_WIRING_FILES: ticket_runner/** -> ticket_runner/__init__.py only), but that ticket's declared scope was only src/frob/tickets/_models.py, so it could not also: (1) disclose the effective (declared + implicit CLI-wiring) scope in 'frob ticket show'; (2) have the CrossTicketLeakage land refusal say WHY a file is claimed (implicit CLI-wiring rule vs declared scope); (3) make 'frob ticket scope --remove' refuse or warn when the removed glob is still covered implicitly. See T-1848's body for the full incident writeup and required behavior.