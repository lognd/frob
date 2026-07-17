---
id: T-0002
title: frob.fuzz generators + FUZZ gates (Phase 8)
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by:
- T-0001
parent: null
scope:
- src/frob/fuzz/**
evidence: []
attachments: []
---
Phase 8 (0.2.0), designed in docs/fuzz.md: Arbitrary protocol (derive from pydantic / __fuzz__ / register), FUZZ001-003 gates, frob test --fuzz with digest-stamped corpus under .frob/corpus (LRU-capped), invariant-anchored default obligation; Rust/TS generator wiring as follow-on. Blocked by T-0001 (frob.fuzz's R6 probing depends on frob-core).