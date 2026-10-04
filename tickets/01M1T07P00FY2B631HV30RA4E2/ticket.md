+++
id = "01M1T07P00FY2B631HV30RA4E2"
title = "H3-13: policy.pattern banning per-frame TypedArray allocation in Renderer"
type = "security"
category = "todo"
priority = "low"
parent = "01M1T07NZSWG65V1BFPEJK6SE6"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-04T22:22:22Z"
aliases = ["T-4096"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/policy/__init__.py"]

[[acceptance]]
text = "given a new Uint8Array(/new Float64Array( call inside a function reachable from a Renderer method body, when the new policy.pattern runs, then it fires unless waived with a reason"
bound = false

[[acceptance]]
text = "given the same construct outside any Renderer-reachable call graph, when the pattern runs, then it stays quiet"
bound = false
+++

H3-13 (F-296). VERIFIED: git grep for a per-frame-allocation policy.pattern (new Uint8Array/Float64Array inside a Renderer method) found nothing in src/frob.

FINDING THIS WOULD HAVE CAUGHT: UT-1714's "never allocates a fresh output buffer per tick" test case checks IDENTITY of the caller's buffer across ticks -- it can only see whether the SAME reference is reused, not whether the renderer allocates OTHER fresh buffers internally on each tick. Detecting actual per-frame heap allocation would need heap instrumentation, which the consumer's own text concedes is out of frob's reach -- the honest, achievable rule is structural instead.

Proposed: a [[policy.pattern]] banning `new Uint8Array(`/`new Float64Array(` (and by extension other TypedArray constructors) inside any function reachable from a Renderer method body, waivable with a reason (some genuinely one-time/non-hot-path allocations inside a Renderer class are legitimate and need an escape hatch, not a blanket ban). Scope this to Renderer-reachable call graphs specifically -- the same reachability the consumer's own text implies ("reachable from a Renderer method body") -- rather than a blanket ban on TypedArray construction anywhere in the file, which would over-fire on legitimate one-time setup code.
