---
id: T-draft-73587936
title: 'REG008 burn-down: 249 findings against check-coverage.yaml registry'
state: queued
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
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
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while draining CI run 35951365410 (dev 9e0c89bb19). Failing:
tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml

The test expects zero REG008 findings against
docs/design/registry/check-coverage.yaml; the real repo currently produces
249 ERROR-severity REG008 findings (assert [...] == [] fails with "Left
contains 248 more items" i.e. 249 total). Sample finding: "REG008: ...
relative to the enforcing rule, or re-disposition the entry".

Size (249) suggests either a bulk-generated registry file gone stale
against real coverage, or a detector regression that started flagging
entries it previously accepted. This drain pass did not have time to
root-cause which; needs a dedicated read of REG008's detector plus
check-coverage.yaml's recent history.
