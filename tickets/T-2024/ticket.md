---
id: T-2024
title: Add the real frob:doc anchor for T-2006's revalidate_dispatchable_sweep_tickets
  once T-1696's tickets.md lease clears
state: queued
kind: docs
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-2006 added `revalidate_dispatchable_sweep_tickets` (src/frob/app/
ticket_runner/_rapid_sweep.py) as a new public symbol with a COV001
waiver instead of a real frob:doc anchor, because its natural doc home
(docs/modules/tickets.md's existing deferred-post-land-sweep section,
T-1684/T-1983) is under T-1696's live cross-worktree lease.

Once that lease clears: add a short subsection to docs/modules/
tickets.md's deferred-post-land-sweep section describing
revalidate_dispatchable_sweep_tickets (called from frob ticket doable's
own render path, _query._doable) and its relationship to T-1983's
_close_resolved_sweep_tickets (same drop mechanism, different call-site
timing), then remove the COV001 waiver and add the real frob:doc anchor.
