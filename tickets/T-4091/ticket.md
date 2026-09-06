---
id: T-4091
title: 'H3-1a: policy.pattern for wasm-twin buffer-length parity in TS'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: medium
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
- text: given a TypedArray.prototype.set call with a function-result argument in a
    module that also declares a length-validated wasm twin, when the new policy.pattern
    runs, then it fires
  evidence: []
- text: given a TS-side length check matching the wasm twin's refusal, when the pattern
    runs, then it stays quiet
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
H3-1's first half (F-296). Part of the round's structural theme: a prose contract enforced on one side of an ABI boundary and unenforced on the other. Strata SYS-031 states "engine functions operate on caller-owned buffers with explicit cols/rows/count parameters" -- enforced in Rust BY HAND, unenforced in TypeScript entirely.

VERIFIED: git grep for a length-mismatch check tied to SYS-031 or a TypedArray.set validation pattern found nothing in src/frob -- confirmed missing, not partially implemented.

FINDING THIS WOULD HAVE CAUGHT: a fallback (non-wasm) TypeScript implementation of a wasm ABI entry point accepting a caller buffer of the wrong length silently, where its wasm twin would refuse the same mismatch. The specific bug: a window pointermove handler paints with the CURRENT cols/rows and an out buffer whose size was computed from a STALE grid size (a resize race), and nothing on the TS side checks the buffer length against the current cols/rows/count before use, the way the Rust/wasm side does by hand.

Proposed: a [[policy.pattern]] on TS matching a `TypedArray.prototype.set` call whose argument is a function-call result (not a literal), inside a module that also declares a length-validated wasm twin (the wasm/native counterpart entry point) -- flagging the case where the JS/TS fallback path has no matching length-refusal that its wasm sibling already performs. State explicitly during design: this is a NARROW, SYS-031-SPECIFIC pattern (paired-implementation length parity), not a general ABI-contract enforcement mechanism -- do not over-scope it into the latter.
