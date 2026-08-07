---
id: T-1671
title: 'frob ticket evidence: designate the BUG002 repro test explicitly and validate
  node-id shape at bind time'
state: dropped
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Two defects in how evidence binds, both surfaced while landing T-1616.

(a) BUG002 infers its designated repro test from bind ORDER -- _designated_repro_test takes the FIRST pytest node id in ticket.evidence. That is positional, not declared: rebinding evidence in a different order silently repoints the mutation check at a different test. 'frob ticket evidence' must let a ticket designate the repro test explicitly, with the bind-order rule kept only as a fallback for tickets that never declare one.

(b) Node-id shape and existence are validated at LAND time, not at BIND time. A malformed id (pytest-style path::Class::method rather than the frob path::Class.method convention) or an id naming a test that does not exist binds cleanly and only fails much later, in the land gate, when the cost of the mistake is highest. Validate shape and resolve the node against the collected suite when the evidence is bound.

Filed by the coordinator after the originating agent's own draft of this ticket was lost during its land merge -- see T-1669.

## Drop reason
- 2026-08-06: duplicate of T-1670, which is the originating agent's own ticket -- it was renumbered from its draft id at land, not dropped; I searched for the pre-renumber draft id and wrongly concluded it was lost