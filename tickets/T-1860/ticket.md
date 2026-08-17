---
id: T-1860
title: Update tickets.md cross-ticket-leakage doc anchor for T-1855's reason disclosure
state: queued
kind: docs
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/modules/tickets.md
  reason: 'T-1780: docs/modules/tickets.md was split by subject; this ticket''s own
    touched code lives in the landing cluster (frob ticket land / BUG002), so its
    scope now names docs/modules/tickets-landing.md instead of the monofile every
    other unrelated ticket also held a lease on'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: 'T-1780: docs/modules/tickets.md was split by subject; this ticket''s own
    touched code lives in the landing cluster (frob ticket land / BUG002), so its
    scope now names docs/modules/tickets-landing.md instead of the monofile every
    other unrelated ticket also held a lease on'
  actor: logan
  at: '2026-08-16'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-1855 added reason-disclosure (declared vs implicit-cli-wiring) to the
CrossTicketLeakage refusal in _check_cross_ticket_leakage/_report_leaked_
tickets (src/frob/tickets/_land.py), which trips AFFECT001 against that
function's existing frob:doc anchor (docs/modules/tickets.md#cross-
ticket-leakage-only-refuses-on-an-in_progress-sibling-t-1639). T-1855
could not update the doc itself: docs/modules/tickets.md was leased to
T-1686 (in-progress) at the time. Update that anchor's prose to describe
the per-path reason annotation ("declared" vs "implicit-cli-wiring") once
the file is free, and drop the frob:waive AFFECT001 T-1855 left on
_check_cross_ticket_leakage.
