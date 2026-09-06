---
id: T-4096
title: 'H3-13: policy.pattern banning per-frame TypedArray allocation in Renderer'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: low
parent: T-4089
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/policy/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a new Uint8Array(/new Float64Array( call inside a function reachable
    from a Renderer method body, when the new policy.pattern runs, then it fires unless
    waived with a reason
  evidence: []
- text: given the same construct outside any Renderer-reachable call graph, when the
    pattern runs, then it stays quiet
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
H3-13 (F-296). VERIFIED: git grep for a per-frame-allocation policy.pattern (new Uint8Array/Float64Array inside a Renderer method) found nothing in src/frob.

FINDING THIS WOULD HAVE CAUGHT: UT-1714's "never allocates a fresh output buffer per tick" test case checks IDENTITY of the caller's buffer across ticks -- it can only see whether the SAME reference is reused, not whether the renderer allocates OTHER fresh buffers internally on each tick. Detecting actual per-frame heap allocation would need heap instrumentation, which the consumer's own text concedes is out of frob's reach -- the honest, achievable rule is structural instead.

Proposed: a [[policy.pattern]] banning `new Uint8Array(`/`new Float64Array(` (and by extension other TypedArray constructors) inside any function reachable from a Renderer method body, waivable with a reason (some genuinely one-time/non-hot-path allocations inside a Renderer class are legitimate and need an escape hatch, not a blanket ban). Scope this to Renderer-reachable call graphs specifically -- the same reachability the consumer's own text implies ("reachable from a Renderer method body") -- rather than a blanket ban on TypedArray construction anywhere in the file, which would over-fire on legitimate one-time setup code.
