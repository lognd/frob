---
id: T-4073
title: 'H-1: node declares no-PII, client_storage write requires waiver'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: high
parent: T-4071
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_pii_structural/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a strata node with an explicit no-PII declaration, when a client_storage
    write occurs on that node with no per-call-site waiver, then it is flagged
  evidence: []
- text: given the same write with a reasoned per-call-site waiver present, when frob
    check runs, then it is accepted
  evidence: []
- text: given the cheaper first step, when this ticket is designed, then taint/dataflow
    analysis is explicitly deferred rather than blocking this ticket
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
H-1 (F-273). VERIFIED: PII gate (src/frob/gates/_pii_structural/) compares against strata carries declarations; there is currently no way for a node to declare it carries NO PII at all (an absence declaration), only positive carries() facts.

FINDING THIS WOULD HAVE CAUGHT: emails written to localStorage on the browser node, invisible because the browser node declares no carries at all -- so there is nothing for a PII rule to compare a client-side write against. SYS100/SYS103 check WHICH FILES hold client_storage capability, not WHAT flows into it; logging.ts sat on the allowlist so the capability ceiling was satisfied while the actual PII leak was invisible.

PREFER THE CHEAPER FIRST STEP OVER TAINT ANALYSIS, per the consumer's own explicit ranking and the coordinator's instruction: taint/dataflow from a carries("contact.email") source to a client_storage sink on a foreign node is the ambitious version and should NOT gate the cheap one. The cheap first step: extend the carries model so a node can declare it carries NO PII (an explicit negative/empty declaration, distinct from simply omitting carries()), and make any client_storage write on such a node require an explicit per-call-site waiver -- turning a silent gap into a mandatory, reviewable exception. FALLING BACK further: an INV rule bound to a docstring's own "redacted before storage" claim (e.g. logging.ts) would independently have forced a test feeding a real value through the redaction function -- note this as a second, complementary angle (ties to T-3954's docstring-claims-as-obligations theme) rather than a replacement for the carries fix.
