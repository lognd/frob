---
id: T-0012
title: 'frob ticket renumber: remedy for sequential-id collisions'
state: dropped
kind: bug
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
frob ticket renumber -- remedy for sequential-id collisions when two agents create tickets concurrently on separate branches and both claim the same T-#### id. Deferred post-0.1.0.

Delivered under T-0032.