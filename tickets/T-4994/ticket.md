---
id: T-4994
title: 'SYS design-quality rule: dead nodes (declared but nothing reaches, binds or
  implements them)'
state: queued
kind: feature
origin: agent
created: '2026-09-19'
priority: medium
blocked_by:
- T-draft-0a0c7b43
parent: T-4804
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given T-4804 decided SYS grows into a design-quality gate and dead nodes are
    one of its four subjects, when this lands, then a SYS rule reports a node that
    nothing reaches, binds or implements, with a positive-control fixture per T-4993
    that makes it fire in CI.
  evidence: []
- text: Given T-4678's correction 2 measured twelve consumer designs in sibling checkouts
    (5,682 lines) using 14 keywords found nowhere in frob's own designs, when the
    rule reports a node as unreached, then it states which corpus it searched -- unreferenced
    in this repo is not dead.
  evidence: []
- text: Given SYS101 already false-positives on design-first repos by flagging capabilities
    declared before implementation (T-3821, F-016), when a node is deliberately declared
    ahead of its implementation, then this rule does not fire -- it must not recreate
    that defect.
  evidence: []
threat: null
component: strata
anchor: false
anchor_reason: null
land_commit: null
---

Design-quality leaf under T-4804's decision (SF-01): SYS grows from a
self-conformance-only gate into a DESIGN-QUALITY gate. A decision turned into a
leaf -- the owner has decided the SUBJECT; the rule design is the work.

BLOCKED BY the module-system story (T-draft-0a0c7b43, "Strata module system:
imports, export surfaces, two-sided contracts, per-module elaboration and link").
Per-module contracts change what this rule can see and what it should assert, so
designing it against today's monolith would be designing against a moving
target. The blocker edge must be attached once that story is promoted to a real
id -- it was still a draft when this leaf was filed, and `frob ticket block`
takes a real ticket id.

WHY THE FAMILY NEEDS NEW SUBJECT MATTER (SF-01): telemetry records 614,294 rule
fires across 82 rule ids; ZERO start with SYS and SELFAUDIT001 appears once,
while design/frob.strata absorbed 434 commits in 60 days. The audit's own
caveat is that SYS is a self-conformance gate so zero is partly the intended
steady state -- which is exactly why the owner decided to widen the subject
rather than retune the existing rules.

NO RULE IS RETIRED under T-4804's decision, and every rule this leaf adds is
subject to T-4993's liveness requirement: it may not stay registered without a
positive-control fixture that makes it fire in CI.

## THIS LEAF: dead nodes

Subject: a node declared in a design that nothing reaches, binds, or implements.

Measured precedent for why this is worth a rule -- the same class already
bit the language itself. SF-09/T-4678's keyword audit found 68 DORMANT
constructs (fully wired parser -> elaborator -> gate, but no design uses them)
and 4 DEAD-CANDIDATEs (parsed into the AST, read by NOTHING: the whole boundary
`admit` block, now T-4911). A design-quality rule for dead NODES is the same
question asked of the model instead of the grammar.

Design questions the implementer must settle and record:
- What counts as "reached"? Inbound flow, outbound flow, a claim naming it, a
  `code` binding, or a consumer design importing it. Per T-4678's correction 2,
  a node unused in THIS repo may be used by one of the twelve consumer designs
  in sibling checkouts (5,682 lines) -- so "unreferenced here" is not "dead",
  and the rule must say which corpus it searched.
- What is the remedy the finding proposes? Deleting a node is exactly the move
  the owner refused for keywords; prefer "wire it or record why it is pending".

Guard-design traps (memory/guard-design-lessons.md): failing open when the
design fails to load; crying wolf on nodes that are deliberately declared ahead
of implementation -- which is SF-15/T-3821's whole complaint about SYS101 on
design-first repos, so this rule must not recreate that defect.
