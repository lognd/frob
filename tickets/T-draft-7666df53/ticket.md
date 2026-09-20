---
id: T-draft-7666df53
title: 'SYS design-quality rule: unreviewed assumes (never reviewed at all, distinct
  from T-4675''s overdue-review verdict)'
state: queued
kind: feature
origin: agent
created: '2026-09-19'
priority: medium
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
- text: Given T-4804 decided SYS grows into a design-quality gate and unreviewed assumes
    are one of its four subjects, when this lands, then a SYS rule reports an assume
    that was never reviewed, with a positive-control fixture per T-4993 that makes
    it fire in CI.
  evidence: []
- text: Given T-4675 (SF-07) separately wires the OVERDUE-review verdict and is the
    critical leaf before the 2026-10-15 cliff, when this rule is designed, then it
    targets never-reviewed assumes and does not duplicate or block T-4675.
  evidence: []
- text: Given all 33 assumes in design/frob.strata are currently one templated shape
    that D-M8 (T-4677) requires rewriting as module-owned and specific, when this
    rule lands, then its interaction with that rewrite is recorded so it does not
    fire 33 times on day one.
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

## THIS LEAF: unreviewed assumes

Subject: an assume that was never reviewed at all -- distinct from an assume
whose review date has passed.

**Explicitly NOT this leaf:** T-4675 (SF-07) wires the OVERDUE-assume verdict
and is the CRITICAL leaf with a hard deadline -- all 33 assumes in
design/frob.strata carry review "2026-10-15", and _claims.py:654 only logs a
warning while _models.py:589, docs/strata/evidence.md:117 and charter.md:4 all
claim it is a gate failure. That is a different bug: a rule that exists and is
not wired. This leaf is the broader question of whether an assume was ever
genuinely reviewed by anyone.

Measured context (SF-08, now decided as D-M8 on T-4677): all 33 assumes are ONE
templated shape, one owner (`logan`), one date, one per node per CWE. D-M8
decided that assumes become module-owned and specific, and that a structural
gate REFUSES templated assumes. This leaf's rule is the quality half of that:
an assume that is specific and module-owned can still be unreviewed.

Design questions to settle and record: what evidence constitutes a review
(a dated owner attestation? a linked ticket?); how a NEW assume is distinguished
from a never-reviewed old one; and what the rule does about the 33 existing ones
during the D-M8 rewrite, so this does not fire 33 times on day one.
