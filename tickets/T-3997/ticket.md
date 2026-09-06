---
id: T-3997
title: 'TESTMOCK001: fully-mocked subjects need a non-mocked companion'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: high
blocked_by:
- T-3985
parent: T-3984
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a frob:tests-bound symbol whose only binding test mocks every collaborator,
    when frob check runs, then TESTMOCK001 fires
  evidence: []
- text: given a second test for the same symbol with at least one non-mocked binding,
    when frob check runs, then the rule is satisfied
  evidence: []
- text: given T-3933's own scenario, when this rule ships, then it would have flagged
    the synthetic LANGUAGE_COLLECTORS stand-in before F-171 surfaced the gap externally
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-207 (T-3984 item 12). VERIFIED: git grep for TESTMOCK001 across src/frob found nothing. THIS HAS A LIVE INSTANCE IN OUR OWN CODE, the strongest possible motivating example: T-3933 documents that T-3925's TestTicketEvidenceVitestOracle used a SYNTHETIC LANGUAGE_COLLECTORS["ts"] lambda standing in for a real ts collector -- the test proved BINDING (node-id resolution) end-to-end while real vitest EXECUTION stayed completely unproven. Every collaborator the test exercised was mocked; nothing non-mocked backed it up, and the gap sat invisible until a separate consumer report (F-171) surfaced it.

FINDING THIS WOULD HAVE CAUGHT: exactly the T-3933 shape -- a frob:tests-bound symbol whose test double-mocks every one of its collaborators, so the test can pass while the real, non-mocked code path (the one that actually runs in production) has never been exercised at all. Proposed rule TESTMOCK001: where every collaborator of a frob:tests-bound symbol is monkeypatched/mocked in the binding test, require at least one OTHER test (for the same symbol or a documented equivalent) with at least one non-mocked binding -- so full-mock coverage of a symbol is never the ONLY evidence for it.

This is also directly connected to T-3985 (the subject-count primitive): a fully-mocked test suite for a symbol is, from the real production code's point of view, examining zero real subjects even though the test suite reports green.
