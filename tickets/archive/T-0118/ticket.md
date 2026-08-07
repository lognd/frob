---
id: T-0118
title: T-0074 scope missing tickets.md/docs/strata (unlike sibling phase-3 tickets)
state: dropped
kind: bug
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-0074's declared scope is ['src/frob/strata/**', 'tests/unit/strata/**'] only. Sibling phase-3 scope tickets (T-0069, T-0070, T-0073) all additionally include tickets.md and docs/strata/** so that frob:ticket start/evidence/sweep CLI mechanics (which necessarily write tickets.md) and design-doc updates pass SCOPE001. T-0074's implementation work (crash contracts, _crash.py) is fully in scope, but recording evidence via 'frob ticket evidence T-0074 ...' produces an unavoidable SCOPE001 on tickets.md that cannot be fixed without touching the ticket's own scope field, which an implementer must not do unilaterally. Fix: amend T-0074's scope list (and any other under-scoped tickets in the phase-3 tree) to include tickets.md, matching the sibling pattern.

Dropped: obsolete. The entire phase-3 tree (T-0074/T-0075/T-0076,
umbrella T-0052) closed with the SCOPE001 residual documented in each
Done report; amending scope on closed tickets is a retroactive no-op.
The general lesson (tickets touching code must scope tickets.md for CLI
mechanics) is captured in the phase-3 Done reports and applied to all
tickets filed since.

## Failure log
- 2026-07-18 attempt 1: obsolete: phase-3 tree closed, amendment retroactive no-op