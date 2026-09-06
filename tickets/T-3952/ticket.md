---
id: T-3952
title: 'ASSERT001: no bare assert in src/**'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: high
parent: T-3942
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a bare assert statement in a src/** module outside tests/, when frob
    check runs, then ASSERT001 fires naming the file and line
  evidence: []
- text: given the existing corpus, when the rule is first turned on, then a baseline/ratchet
    is used rather than a repo-wide failure
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-179 (T-3942 item 5). The cheapest rule in either report per the consumer. Proposed in their first audit (T-3919, never decomposed/built) and the identical bare-assert pattern reappeared verbatim in the newest module they wrote for the delta audit. FINDING THIS WOULD HAVE CAUGHT: F-179 -- a bare assert statement in src/** used for a runtime/security-relevant check that a production build with -O strips silently. Rule: a lexical/AST gate rejecting bare assert in src/** (test files exempt), pointing the author at typani Result/ensure idioms instead. No prior ticket found via git grep for ASSERT001.