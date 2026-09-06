---
id: T-4077
title: 'M-8: error-state a11y assertion plus RHF aria-invalid lint'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: medium
parent: T-4071
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
- text: given the RHF aria-invalid lint (part b), when an input registered with RHF
    has no aria-invalid attribute, then it is flagged
  evidence: []
- text: given an auth form test with no axe assertion after a failed submit, when
    this ticket's part a ships, then it is flagged as missing error-state a11y coverage
  evidence: []
- text: given T-4034's kind=a11y obligation, when this ticket's design step runs,
    then it states whether these tests bind under that kind
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
M-8 (F-273). RELATES TO T-4034 (frob:tests kind=a11y, already filed under T-4025) but is a distinct, more specific ask -- T-4034 is about DECLARING that a test is a11y-shaped at all; this item is about WHAT an a11y test must actually assert once declared. Not a duplicate; cross-reference T-4034 in this ticket's design step as the obligation-kind this rule's tests would be bound under.

VERIFIED: the a11y checks the consumer already has (axe-core as a devDependency, COMP-1502 enforcing tap target/text size/focus ring as class-string CONSTANTS) cannot see an unfired validation state -- axe only audits the RENDERED DOM, and no existing test renders a form in its error state, so the error state's accessibility is simply never examined by anything.

FINDING THIS WOULD HAVE CAUGHT: a form's error state (the DOM after a failed submit -- error messages, aria-invalid attributes, focus movement) was never rendered by any test, so axe-core (installed, configured, capable) never got a chance to audit it -- structurally the same "capability exists, is never invoked" shape as M-3, applied to a11y instead of API-contract drift.

Proposed, two parts per the consumer: (a) require an axe assertion in each auth form's test AFTER a failed submit specifically (not just on the happy-path render), and (b) a lint rule requiring any input registered with React Hook Form (RHF) to carry aria-invalid (a structural JSX-attribute-presence check, no data-flow needed). Part (b) is the cheaper, purely structural half and can ship independently of (a).
