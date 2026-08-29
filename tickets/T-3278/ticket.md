---
id: T-3278
title: check-coverage.yaml gate_rule_entries has 3 stale ids vs known_gate_rule_ids
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/design/registry/check-coverage.yaml
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
Found while working T-3243 (REG005: declared gate_rule_total vs entry count drift, fixed separately). tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules fails: gate_rule_entries has 355 ids but known_gate_rule_ids() (the live rule registry) has only 352 -- 3 entries in check-coverage.yaml do not correspond to any currently-registered gate rule id. REG005 only checks the declared total against the entries list length (both now 355, consistent); it does not check entries against the live rule set, which is what this failing test does. Needs someone to diff the two id sets and either remove the 3 stale entries or register the missing rules.