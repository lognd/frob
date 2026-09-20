---
id: T-4996
title: 'SYS design-quality rule: contract drift (a declared contract that no longer
  matches what the code does; 45 units of ratchet slack and 3 dead entries today)'
state: queued
kind: feature
origin: agent
created: '2026-09-19'
priority: medium
blocked_by:
- T-5081
parent: T-4804
tier: ticket
sprint: v1.1.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: v0.536.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
acceptance:
- text: Given T-4804 decided SYS grows into a design-quality gate and contract drift
    is one of its four subjects, when this lands, then a SYS rule reports a declared
    contract that no longer matches the code, with a positive-control fixture per
    T-4993 that makes it fire in CI.
  evidence: []
- text: Given SF-05 measured 7 keys under ceiling for 45 units of slack and 3 dead
    entries (cli::env, serve::eval, tickets_ledger::eval) with 0 over ceiling and
    0 unlocked, when this rule evaluates the ratchet, then it consumes T-4670's drift
    reporter rather than inventing a second notion of drift.
  evidence: []
- text: Given T-4671 is making the SYS111 ceiling derivable rather than committed,
    when this rule is designed, then it is read against that design and does not reintroduce
    a hand-committed number.
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

BLOCKED BY the module-system story (T-5081, "Strata module system:
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

## THIS LEAF: contract drift

Subject: a declared contract that no longer matches what the code does.

This is the subject with the strongest existing evidence, because the capability
ratchet is exactly a contract that drifts and is currently policed only in one
direction. SF-05 measured, against the committed lock at HEAD: 7 keys UNDER
their ceiling for a total slack of **45**, and **3 dead entries** (cli::env,
serve::eval, tickets_ledger::eval), with 0 over ceiling and 0 unlocked. The
one-way ratchet never re-tightens, so 45 new capability sites can land with
SYS111 silent. T-4670 files the drift REPORT; this leaf is the rule that decides
when drift is a finding.

Related and to be read first: T-4671 (derive the SYS111 ceiling rather than
commit it, ending the five-ticket race chain T-4495 -> T-4563 -> T-4596 ->
T-4607 -> T-4633) and T-4668 (one lock loader/writer/schema, designed for
per-module locks). This leaf must not invent a second notion of drift beside
T-4670's reporter -- consume it.

Per-module contracts are the reason for the blocker: the module system's
two-sided `accepts` contract makes "contract drift" a checkable relation
between two modules, not just between a model and its own lock.
