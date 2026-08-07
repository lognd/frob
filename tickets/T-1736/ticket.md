---
id: T-1736
title: Wire frob.verify.record_intent into the land-commit path so the verify queue
  actually gets entries
state: queued
kind: feature
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
found while landing T-1688: frob.verify._watermark.record_intent has no real caller yet -- T-1687 built it foundation-only and T-1688's worker only drains/advances/compacts an existing queue, it never enqueues. Something at land-commit time (most likely src/frob/tickets/_land.py's post-land hook) needs to call record_intent with the landed commit sha and touched symrefs, or the coalescing worker never has anything to verify.