---
id: T-6494
title: 'dropped: runtime cache-stampede-under-load detection (research row 8.3)'
state: dropped
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-6401
tier: ticket
sprint: sysdesign
runs_last: false
milestone: 0.539.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'DOC006 inline waivers: body names files this ticket will create (T-6448)'
  actor: logan
  at: '2026-09-25'
  old_length: 1113
  new_length: 1105
- mode: set
  reason: 'DOC006 inline waiver: dotted pointer to a future module (T-6448)'
  actor: logan
  at: '2026-09-25'
  old_length: 1105
  new_length: 1105
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: dropped: runtime cache-stampede-under-load detection (research row 8.3)
kind: feature
tier: dropped
parent: T-SYS-SH
scope: --
blocked_by: []

Reason: research row 8.3 ("Cache stampede protection") is explicitly tagged dynamic-only in
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its scaffold" -->scratchpad/sysdesign-research.md's tag column: "Hot-key cache-read code with no single-flight/
lock guard around the recompute-on-miss path flags a stampede risk when the design model marks
the key as high-QPS | dynamic-only". Per the owner stance, dynamic-only rows become a
frob:tests obligation, never a static rule -- actually detecting a stampede requires runtime
load, which no static analysis can observe. The declared-vs-observed STATIC companion (does the
design declare and prove a `stampede_guard`) is a legitimately different, separately justified
check and is filed as SYSDESIGN304/305 (T-SYS-E-STAMPEDE), not dropped.
