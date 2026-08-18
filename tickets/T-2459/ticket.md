---
id: T-2459
title: Recovered from T-2394's phantom TICK006 citation of T-draft-b08172a8
state: queued
kind: bug
origin: agent
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
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
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2394's Done report claimed T-draft-b08172a8 was filed, but T-draft-b08172a8 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> esting requeue/close/archive/land dispatch). Fixed by
giving each a real one-file scope; re-ran the touched set clean
afterward. Also found and filed T-draft-b08172a8 (out of scope: the
related-title duplicate detector false-positiving "holder"/"collider" at
71%, breaking a pre-existing TestTicketSt