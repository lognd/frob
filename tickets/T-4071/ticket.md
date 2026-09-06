---
id: T-4071
title: 'F-273: auth-pages audit -- V-model closure is satisfied by existence, never
  by reachability'
state: queued
kind: security
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: 'tier=epic: decomposition container for the eighth consumer
  audit list; scope lives on the children'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2 F-273 (auth-pages audit, 2026-09-06), verbatim in their
FROBLEMS.md. EIGHTH audit list from that repo. Prior seven: T-3919, T-3920,
T-3928, T-3942, T-3984, T-4025, T-4036.

READ THE FULL ITEM TEXT IN ../logand.app-v2/FROBLEMS.md under "## F-273" -- it is
long and specific, and each item already names the rule that would have caught
its finding. That specificity is the reason this list is high-value: the auditor
did the design work, not just the complaint.

THE CHEAPEST HIGH-VALUE ITEM, AND THEY SAY SO THEMSELVES (M-3): nothing checks TS
interfaces against backend/openapi.json, "EVEN THOUGH `npm run types`
(frontend/package.json:22) ALREADY GENERATES THE CORRECT TYPES AND IS SIMPLY NOT
WIRED INTO `check`". The remedy is to run an existing script in check mode --
exactly as `licenses:check` and `static-assets:check` already are -- and fail when
the generated file is stale. A capability that exists, is configured, and is
never invoked is the cheapest possible gate to add. START HERE.

THE STRUCTURAL THEME ACROSS THE LIST is that V-MODEL CLOSURE IS SATISFIED BY
EXISTENCE, NEVER BY REACHABILITY. Their M-1 states it exactly: COMP-1801..1805
each have a frob:describes anchor, a frob:doc back-reference and a passing unit
test, so closure is satisfied by "component exists and is tested" -- while the
auth pages are UNROUTED and unreachable. This is the SAME finding as T-4025 item 1
("a component can be fully implemented, fully tested, V-model-closed, and never
invoked"), now with a second independent instance and a concrete proposed rule: a
frontend WIRE rule asserting every exported page component under pages/** is
referenced from a route table, symmetrical to the backend's existing
route-registration check. CROSS-REFERENCE T-3985 and T-4025's child rather than
filing a third time.

ITEMS WORTH FLAGGING FOR THE DECOMPOSER:
  H-1  the PII gate compares against strata `carries` declarations, and the
       `browser` node declares none -- so there is nothing to compare a
       client-side write against. Their CHEAPER first step is good and should be
       preferred over taint analysis: let a node declare NO PII, and make any
       client_storage write on such a node require a per-call-site waiver.
  H-2  SEC110 fired and was CORRECTLY waived (the site key is genuinely public);
       the real defect is an unguarded `??` default for a required build-time
       config value, which no gate models. Note this is a case where a waiver was
       RIGHT and the missing rule is adjacent -- do not treat the waiver as the
       defect.
  M-2  no gate compares two L5 rows against each other; needs an invariant
       binding the role dispatch, so a contradiction becomes a failing invariant
       rather than two individually-consistent rows.
  M-4/M-5/M-6  three behaviours whose UT rows describe error handling in prose
       but test only the happy path; COV counted them covered because a test
       exists per COMP id. Their proposal -- bind frob:tests at the BRANCH level,
       requiring a row naming an error class to have a test asserting that class
       -- is the fourth arrival of the docstring-claims-as-obligations theme
       (T-3954). Cross-reference; do not refile.

GUIDANCE, unchanged from the previous seven: DO NOT BUILD ALL OF IT. Decompose
into leaves, keep the audit's own ordering, name the finding each child would
have caught, and VERIFY EACH AGAINST WHAT EXISTS FIRST -- five items across the
earlier epics turned out already implemented, and M-3 here is explicitly a
"already exists, not wired" case, so expect more of those.

ACCEPTANCE
- M-3 (wire `npm run types` into check) filed first as the cheapest item.
- M-1 cross-referenced to T-4025's reachability child and T-3985, not refiled.
- M-4/M-5/M-6 cross-referenced to T-3954.
- Each remaining child names the finding it would have caught.