---
id: T-0002
title: frob.fuzz generators + FUZZ gates (Phase 8)
state: dropped
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0001
parent: null
tier: ticket
sprint: null
scope:
- src/frob/fuzz/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Phase 8 (0.2.0), designed in docs/modules/fuzz.md: Arbitrary protocol (derive from pydantic / __fuzz__ / register), FUZZ001-003 gates, frob test --fuzz with digest-stamped corpus under .frob/corpus (LRU-capped), invariant-anchored default obligation; Rust/TS generator wiring as follow-on. Blocked by T-0001 (frob.fuzz's R6 probing depends on frob-core).

Delivered under T-0034 (fuzz library + gate + CLI). Remaining polish (Rust/TS runners,
full per-ecosystem rules) tracked in the ticket body/docs notes.