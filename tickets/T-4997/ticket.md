---
id: T-4997
title: 'SYS design-quality rule: per-module audit findings reach the gate as findings,
  not as a report nobody reads'
state: queued
kind: feature
origin: agent
created: '2026-09-19'
priority: medium
blocked_by:
- T-5081
parent: T-4804
tier: ticket
sprint: null
runs_last: false
milestone: 0.536.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given T-4804 decided SYS grows into a design-quality gate and per-module audit
    findings are one of its four subjects, when this lands, then a module's own audit
    verdict surfaces as a SYS finding, with a positive-control fixture per T-4993
    that makes it fire in CI.
  evidence: []
- text: Given the per-module audit hook is part of the module-system story and does
    not exist yet, when that story lands, then this leaf's blocker edge is attached
    to its promoted id and the rule is specified against the real hook, not guessed.
  evidence: []
- text: Given an audit that produces a report is not an audit that produces a gate
    finding, when this lands, then the deliverable is the finding path itself and
    a test asserts a module audit result reaches frob check.
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

## THIS LEAF: per-module audit findings

Subject: surfacing, as SYS findings, the per-module audit results the module
system produces -- so a module's own quality verdict reaches the gate rather
than staying in a report nobody reads.

This leaf is the most tightly coupled to the module-system story of the four:
the per-module audit hook is part of that story (see its sibling ticket on the
strata linker: import-cycle detection, two-sided accepts contract, per-module
audit hooks). It cannot be specified before that hook exists.

Why it matters for SF-01's ratio: the SYS family currently asks one question
about one monolithic model, and answers zero. Per-module findings give it N
subjects that change independently, which is the structural fix for a gate whose
zero is uninformative.

Per memory/catalogued-is-not-enforced.md, note the trap this leaf exists to
avoid: an audit that produces a report is not an audit that produces a gate
finding. The deliverable is the finding path, not the report.
