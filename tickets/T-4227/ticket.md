---
id: T-4227
title: 'evidence classification: a test whose subject is constructed in the test file
  rather than imported from the package is weaker evidence'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: high
parent: T-4175
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer F-373/P3 (T-4175): a system test builds a throwaway app with one synthetic route per error type and asserts against that -- it never touches the real routers, so an error body constructed anywhere other than the intended mapper is outside its reach by construction. The test is green and its subject is not the system. This is the dogfooding-blindness class expressed as a test-design defect, and it is detectable in principle: label a test whose subject (app/route table/registry instance) is constructed inline in the test file, rather than imported from the package under test, as a distinct and weaker evidence kind. High-value, generic. Fixture-testable: YES, frob's own evidence-binding code with a synthetic example (a test that builds its own throwaway object instead of importing the real one).