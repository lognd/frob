---
id: T-6455
title: 'GRAMMAR: module-level `owner STRING` declaration'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-6434
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
- strata-core/src/parse/grammar_module.rs
- docs/strata/surface.md#module
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


title: GRAMMAR: module-level owner STRING declaration
kind: feature (OWNER-OWNED)
tier: leaf
parent: T-SYS-SA
milestone: 0.539.0
sprint: sysdesign
points: 2
scope: strata-core/src/parse/grammar_module.rs, docs/strata/surface.md#module,
       src/frob/strata/_models.py, tests/fixtures/sysdesign/module-owner/**
blocked_by: [T-STORE-301-ATTR]

Finding (STRATA-EXPRESSIVENESS.md, section G "STRUCTURE"):

"`module` IS effectively a bounded context (a named, export-controlled unit), but there's no
explicit 'team X owns module Y' declaration -- ownership rides `Waiver.owner`/`Claim.owner` (a
person string on individual waivers/claims, _models.py:374,585) not on the module/node itself.
Proposal (GRAMMAR, minor): top-level or node_prop `owner STRING` clause, grammar_module.rs
(module-level) and/or grammar_node.rs (node-level), desugars to attr/typed field. Enables
RULE: a module with no declared owner and open `frob:waive` entries -- ownership-hygiene
check, authority: this repo's own existing Waiver.owner precedent generalized."

Node-level `owner` is covered by T-SYS-A-NODE-OPS; this leaf is the module-level half only
(different grammar file, genuinely scope-disjoint).

Acceptance criteria: grammar_module.rs gains a top-level `owner STRING` clause on `module { }`
blocks, desugars to attr, registered in T-STORE-301-ATTR's table. Positive-control fixture:
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
tests/fixtures/sysdesign/module-owner/module-no-owner-open-waiver/design.strata.
