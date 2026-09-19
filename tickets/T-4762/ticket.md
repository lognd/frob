---
id: T-4762
title: 'Standing test: render every registered type, git init, and require a clean
  frob check'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4761
parent: T-4757
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/integration/test_scaffold_green_day_one.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given every registered type, when it is rendered, git-initialised and checked,
    then frob check reports zero findings
  evidence: []
- text: Given a newly registered type, when the test runs, then it is covered without
    editing the test, because the test iterates the registry
  evidence: []
- text: Given a deliberately broken fixture template, when the test runs, then it
    fails and names the offending type and finding
  evidence: []
- text: Given a zero-finding result, when the test asserts, then it also asserts the
    check actually ran and evaluated a non-zero number of rules
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The green-day-one requirement needs a test that cannot rot, because every
previous scaffold-cleanliness ticket (T-3262, T-3330, T-3719, T-3931) fixed
findings without leaving a standing check, and the types went red again.

Add an integration test that, for EVERY registered project type: renders it
into a temporary directory, runs git init plus an initial commit, runs frob
check in the rendered tree, and asserts the result is clean.

The test iterates the registry, so a newly registered type is covered the
day it is registered rather than the day someone remembers to extend a list.

Positive control: the test must FAIL if a template regresses. Prove it by
asserting the failure path explicitly -- a deliberately broken fixture
template (one bare TODO marker) makes the assertion fire, and the test body
names the offending type and finding rather than reporting a bare boolean.
A zero-findings result that came from frob check failing to run at all must
be distinguishable from a genuine pass: assert the check actually ran and
reported a rule count above zero.
