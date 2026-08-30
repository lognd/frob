---
id: T-3492
title: Wire java into vet/dup/docblock capability facets
state: queued
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability_registry/**
- src/frob/dup/_exhaustiveness.py
- src/frob/gates/_docblocks.py
- src/frob/lang/_support.py
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
found while working T-1601: java gets a real frob.lang grammar/walker but the capability dangerous-op registry, dup clone-detection exhaustiveness table, and DOC004 fenced-code-block bucket have no java entry yet -- mirrors T-2906's bash/csharp facet-wiring follow-up exactly. frob.lang._support marks these three facets KNOWN_GAP for java citing this ticket in the interim.