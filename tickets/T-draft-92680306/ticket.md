---
id: T-draft-92680306
title: 'SYSDESIGN304: high-fanout cache-fill flow with `stampede_guard` undeclared
  or unproven'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-draft-49d2300b
parent: T-draft-ce656788
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
scope:
- src/frob/strata/_stampede.py (new)
- tests/fixtures/sysdesign/sysdesign304/**
scope_breadth_ack: true
scope_breadth_ack_reason: sysdesign epic tree, scope reviewed by coordinator
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'DOC006 inline waivers: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 2376
  new_length: 2465
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN304: high-fanout cache-fill flow with stampede_guard undeclared or unproven
kind: feature
tier: leaf
parent: T-SYS-SE
milestone: 0.539.0
sprint: sysdesign
points: 3
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/strata/_stampede.py (new), docs/modules/gates.md (SYSDESIGN304 row),
       tests/fixtures/sysdesign/sysdesign304/**
blocked_by: [T-SYS-A-INFRA-CACHE-QUEUE]
tag: Static: design (declared-vs-observed pair; see dynamic-only note below)

<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its scaffold" -->Research row 8.3 is tagged dynamic-only in scratchpad/sysdesign-research.md ("Hot-key
cache-read code with no single-flight/lock guard around the recompute-on-miss path flags a
stampede risk when the design model marks the key as high-QPS | dynamic-only"). Per the owner
stance, the RUNTIME stampede-under-load behavior itself is a test obligation, not a static
rule, and is filed as a dropped ticket in Story H (T-SYS-DROP-STAMPEDE-DYNAMIC), not
reintroduced here.

This leaf is a distinct, legitimately static companion, the same two-step pattern REL220/221
already uses for backoff: STRATA-EXPRESSIVENESS.md's `stampede_guard` grammar proposal (section
C) states "Enables RULE: high-fanout flow into a cache-fill with no stampede_guard =
thundering-herd risk (pairs with existing `fanout` numeric on the same flow -- REL-family, e.g.
REL262). Authority: Meta/memcached 'leases' paper, Vattani et al. probabilistic early
expiration." SYSDESIGN304 checks DECLARATION and PROOF of `stampede_guard` (does the flow
declare it, does bound code contain a real lock/single-flight/probabilistic-early-expiry
token) -- it does not attempt to detect an actual stampede at runtime, so it does not
contradict row 8.3's dynamic-only tag.

Acceptance criteria: SYSDESIGN304 fires on either of two conditions, folded into one id per
the coordinator's contiguous-numbering directive -- a cache-fill flow with `fanout` above a
threshold and no `stampede_guard` declared flags; a flow declaring `stampede_guard` with no
bound code containing a real lock/single-flight/probabilistic-early-expiry token also flags,
unproven. Positive-control fixture: tests/fixtures/sysdesign/sysdesign304/
high-fanout-no-stampede-guard/**.
