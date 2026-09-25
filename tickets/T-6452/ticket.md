---
id: T-6452
title: 'dropped: chaos/fault-injection test execution and verification (research row
  9.8)'
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
  old_length: 1478
  new_length: 1470
- mode: set
  reason: 'DOC006 inline waiver: dotted pointer to a future module (T-6448)'
  actor: logan
  at: '2026-09-25'
  old_length: 1470
  new_length: 1470
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: dropped: chaos/fault-injection test execution and verification (research row 9.8)
kind: feature
tier: dropped
parent: T-SYS-SH
scope: --
blocked_by: []

Reason: research row 9.8 ("Chaos testing / fault injection practiced, not just designed for")
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its scaffold" -->is explicitly tagged dynamic-only in scratchpad/sysdesign-research.md's tag column: "A service
with circuit breakers/retries/graceful-degradation declared (sec. 6) but no chaos/fault-
injection test referencing it flags as an unverified resilience claim | dynamic-only". Per the
owner stance, dynamic-only rows become a frob:tests obligation, never a static rule -- whether
a chaos experiment actually ran and passed is a runtime/CI-pipeline fact, not something static
analysis of source can prove. STRATA-EXPRESSIVENESS.md's finding that the `scenario`/
RemoveNode/ScaleRate/SetTrust rewrite machinery is already "structurally chaos-engineering-
shaped" is noted for a future frob:tests obligation documenting `scenario` as the chaos idiom,
but that documentation-only follow-up is not itself a lint rule and is not filed as a separate
ticket here (it is a docs/strata/surface.md note the T-SYS-A-LATTICE or a future docs pass can
pick up incidentally, not a scoped leaf of its own).
