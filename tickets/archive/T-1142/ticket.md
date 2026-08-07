---
id: T-1142
title: 'tickets: flow report undercounts landed/day -- mine archive + git history,
  not just the live ledger'
state: done
kind: bug
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_tickets_velocity.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: documented ticket_flow's T-1142 archive-merge fix in the flow section, per
    playbook section 6
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_tickets_velocity.py::TestTicketFlow::test_archived_ticket_still_counts_toward_landed
- tests/test_tickets_velocity.py::TestTicketFlow::test_archived_ticket_still_counts_toward_filed
designated_repro_test: null
acceptance:
- text: GIVEN days on which archived tickets landed (e.g. 2026-07-26/27 with ~50 lands
    each) WHEN frob ticket flow runs THEN the landed column reflects them (sourced
    from tickets-archive.md and/or git history per T-0938's mining) and the ETA extrapolation
    uses the corrected net rate
  evidence:
  - tests/test_tickets_velocity.py::TestTicketFlow::test_archived_ticket_still_counts_toward_landed
threat: null
component: null
---
First real run of T-1100's flow verb (2026-07-28) showed landed=0 for 2026-07-26 and 2026-07-27 when the zero-drive record shows roughly fifty lands each day -- archived tickets fall out of the landed count, so the trailing net rate and ETA are wrong in exactly the situations the verb was built for (heavy landing waves followed by archive sweeps).