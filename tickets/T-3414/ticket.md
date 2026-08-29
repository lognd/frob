---
id: T-3414
title: 'DOC011: stale T-draft-ad5e921b citation in docs/modules/tickets.md'
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/tickets.md
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
docs/modules/tickets.md:99 cites 'T-draft-ad5e921b', a draft id that was renumbered to T-3360 once the ticket was persisted (drafts get a real T-#### id on the next reconcile) -- the doc anchor never got updated to follow the rename, so DOC011 fires. Fix: replace the stale 'T-draft-ad5e921b' citation with 'T-3360'.