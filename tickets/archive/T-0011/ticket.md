---
id: T-0011
title: Mutation testing as the test-quality oracle
state: dropped
kind: feature
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/testing/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Add mutation testing (mutmut or equivalent) as the honest test-quality oracle; TEST-family gains a mutation-score floor. Counts and coverage floors are gameable proxies (assert-free tests pass them) -- this is the real defense. Deferred post-0.1.0.

Delivered under T-0040 (frob mutate). MUT gate (score floor on
invariant-anchored symbols) + non-Python remain follow-on.