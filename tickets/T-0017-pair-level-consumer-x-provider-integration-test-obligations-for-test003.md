---
id: T-0017
title: Pair-level (consumer x provider) integration test obligations for TEST003
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
evidence: []
attachments: []
---
TEST003 alpha semantics treat every src/<pkg> directory with a public symbol as an interface owing min_integration edges (an honest over-approximation, per docs/gates.md's Phase 4 notes). Deferred: derive real consumer x provider pairs once frob.graph gains cross-file import edges, and require min_integration per pair rather than per provider.