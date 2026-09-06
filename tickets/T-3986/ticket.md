---
id: T-3986
title: 'POL000: policy.pattern matching zero nodes is a config error'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: high
blocked_by:
- T-3985
parent: T-3984
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
- text: given a [[policy.pattern]] entry whose query matches zero nodes across its
    full declared glob set, when frob check runs, then POL000 fires distinct from
    a clean pass
  evidence: []
- text: given a pattern that matches at least one node with zero violations, when
    frob check runs, then POL000 stays quiet
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-196 (T-3984 item 1). VERIFIED: git grep for POL000 across src/frob found nothing -- no existing rule checks whether a [[policy.pattern]] entry ever matches. An INSTANCE of the subject-count primitive (T-3985): a policy.pattern is precisely a gate configured to be enforcing over a glob set, and matching zero nodes across its whole glob set today is invisible.

FINDING THIS WOULD HAVE CAUGHT: a malformed or over-narrow policy.pattern query silently matching nothing across its entire configured glob set -- indistinguishable today from a pattern that correctly finds no violations because the code is clean. A malformed query is a hard config error, not silence, per the consumer.

Depends on T-3985 (the subject-count primitive): once ToolResult/policy evaluation reports a per-pattern match count, POL000 is "an enforcing policy.pattern entry whose match count (nodes visited, not violations found) is zero across its full glob set" -- flag it as a configuration error distinct from a clean pass.
