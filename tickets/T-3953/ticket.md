---
id: T-3953
title: 'RACE001: concurrent read-then-write test obligation'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: high
parent: T-3942
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_inv.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a function with an unlocked read of a value followed by a write derived
    from it and no lock/Lua/INCR/conditional-UPDATE guard, when frob check runs, then
    RACE001 fires
  evidence: []
- text: given a docstring/spec claiming cap, quota, single-use or idempotent behavior
    with no concurrent-callers test, when frob check runs, then a test obligation
    is reported
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-181 (T-3942 item 7), same rule as T-3919 item 3 (first audit, never decomposed/built -- T-3919 has zero children as of this filing). Two findings in the delta audit are in its scope. FINDING THIS WOULD HAVE CAUGHT: a read-then-write on the same key/row inside one function with no lock, Lua script, INCR-first or conditional UPDATE -- specifically components whose spec/docstring says cap / quota / single-use / idempotent but which do plain read-check-write. Rule: RACE001 detects the read-then-write shape; pair with a test obligation that any component whose spec row says cap/quota/single-use/idempotent needs a concurrent-callers test. NOTE the auditor's own caveat: this is a heuristic shape and will be waived into uselessness fast (the exact dynamic item 1 of T-3919 is about) -- cost the false-positive rate before shipping broadly; consider starting as a WARN-tier advisory rather than a hard gate. Cross-ref: T-3919 item 3 is the same ask from the first audit; do not file a second ticket there, cite this one.