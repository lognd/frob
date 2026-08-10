---
id: T-1608
title: 'Cross-language inspection stress test: one repo, every supported language,
  one obligation graph'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
blocked_by:
- T-1607
parent: T-1597
tier: ticket
sprint: null
runs_last: false
scope:
- tests/**
- src/frob/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The payoff test for the whole epic: a single fixture repository containing every supported language at once, carrying a real obligation graph across language boundaries.

What it must demonstrate:
- Doc edges from a symbol in one language to documentation that also covers symbols in another.
- Test edges from a test written in one language binding a symbol implemented in another (the FFI/binding shape frob users actually have: Python tests over a Rust or C++ core, a TypeScript client over a Java service).
- Waivers, todos, and ticket directives resolving identically regardless of the host language's comment syntax.
- A full frob check over the mixed repo producing correct, non-degraded results -- and, critically, ANNOUNCING any language whose analysis could not run rather than silently reporting zero findings for it.

That last point is this drive's recurring lesson applied to the language layer: a silent under-report is indistinguishable from a clean result, and every incident this session traced back to exactly that. A mixed-language repo multiplies the opportunities for it.