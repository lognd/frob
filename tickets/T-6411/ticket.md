---
id: T-6411
title: 'GRAMMAR consistency: resolve `Flow.timeout` typed-field-with-no-grammar-production
  gap'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-6467
parent: T-6510
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
- strata-core/src/parse/grammar_flow.rs
- docs/strata/kernel.md
- src/frob/strata/_models.py
scope_breadth_ack: true
scope_breadth_ack_reason: sysdesign epic tree, scope reviewed by coordinator
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
OWNER-OWNED: strata surface change; owner reviews before dispatch


title: GRAMMAR consistency: resolve Flow.timeout typed-field-with-no-grammar-production gap
kind: feature (OWNER-OWNED)
tier: leaf
parent: T-SYS-SA
milestone: 0.539.0
sprint: sysdesign
points: 3
scope: strata-core/src/parse/grammar_flow.rs, docs/strata/kernel.md,
       src/frob/strata/_models.py, tests/fixtures/sysdesign/flow-timeout-fix/**
blocked_by: [T-SYS-A-FLOW-HEDGE]

Finding (STRATA-EXPRESSIVENESS.md, "CORRECTIONS TO PRIOR SYSDESIGN-INVENTORY.md", item 3):

"`Flow.timeout` is a typed kernel field (_models.py:456) with NO dedicated grammar keyword
feeding it in the flow_prop loop read in full (grammar_flow.rs:8-113 accepts label/age/rate/
size/attr/transport/fanout/growth/authenticates_via/utility only) -- REL200/201 almost
certainly reads `timeout` off the generic `attr timeout=<q>` clause, not a first-class
production. This is a real 'typed field with attr-only feed' inconsistency worth flagging to
the owner directly (possibly dead/aspirational kernel surface, or fed by an elaborator-side
attr-to-field promotion this audit did not locate) -- VERIFY BEFORE RELYING ON for anyone
building deadline-propagation tooling."

Acceptance criteria: the owner decides one of two resolutions and this ticket implements it:
(a) add a dedicated `timeout QUANTITY` production to flow_prop so `Flow.timeout` is fed
directly (closing the inconsistency by promoting attr to grammar), or (b) confirm the
attr-only path is intentional and document the elaborator-side `attr timeout=<quantity-string>`
-to-field promotion explicitly in docs/strata/kernel.md so future readers (including
SYSDESIGN301 deadline-propagation work, Story E) do not re-discover this as a live bug. Either
resolution updates docs/strata/kernel.md with the confirmed mechanism. Positive-control
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
fixture: tests/fixtures/sysdesign/flow-timeout-fix/attr-vs-grammar-timeout/design.strata
proving whichever path is chosen actually feeds REL200/201.
