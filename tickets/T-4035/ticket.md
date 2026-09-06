---
id: T-4035
title: 'frob:mirror: cross-language literal-constant equality directive'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: high
parent: T-4025
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/dsl.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a design note settling the directive syntax and how it resolves a target
    in a different language/grammar, when this ticket's design step completes, then
    the note is attached before implementation, and it explicitly states whether Caddyfile
    has any grammar to parse against yet
  evidence: []
- text: given two frob:mirror-linked constants whose literal values diverge, when
    frob check runs, then the mismatch is flagged
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Item 7. VERIFIED: git grep for frob:mirror across tickets/ shows it was proposed in T-3928's body (frontend-unique item, "a frob:mirror directive asserting literal equality across languages") but never filed as its own child ticket -- I deferred it in that decomposition pass for budget reasons and said so explicitly. This item supplies the second, stronger motivating case, so filing it now under T-4025 rather than going back to add it to T-3928; do not file a third ticket for the same construct.

FINDING THIS WOULD HAVE CAUGHT: THE CADDYFILE BLIND SPOT PRODUCED A REAL OUTAGE, not spec drift. It was filed as harmless at the time because no consumer of the relevant value existed yet; the consumer then landed on a DIFFERENT branch in a DIFFERENT language, and nothing connected the two -- a cross-language constant pair (a value in the Caddyfile's config language and its counterpart in application code) silently diverged with no mechanism watching either side for the other. This is a MEASURED INSTANCE of the exact cross-language desync T-3928 already records as the motivating case for frob:mirror, and CLAUDE.md's own "two copies of a rule is a bug waiting to desync" made checkable.

Proposed: frob:mirror <path>::<identifier> (or equivalent) asserting literal equality between a constant in this file and a named constant in another file/language, checked at frob check time regardless of language grammar boundaries -- needs no taint analysis, just two literal values compared. Note this also depends on Caddyfile getting SOME frob grammar (already tracked: T-3928's shell-grammar-plus-policy-catalogue ticket, T-3955, covers ops/**.sh; Caddyfile itself has no tracked grammar effort yet -- flag that gap explicitly in this ticket's design step rather than assuming Caddyfile parsing is free.
