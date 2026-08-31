---
id: T-3554
title: check-coverage registry missing entry for AUTOFIX001 (T-3526)
state: queued
kind: bug
origin: human
created: '2026-08-31'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/design/registry/check-coverage.yaml
- tests/test_check_coverage_registry.py
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
MEASURED run 33361224273 (HEAD 8d4c18055): tests/test_check_coverage_registry.py fails assert 359 == 360 plus its exhaustiveness sibling test. A newly registered gate rule (almost certainly AUTOFIX001 from T-3526) has no docs/design/registry/check-coverage.yaml entry -- the registry's own count drifted from the live gate-rule count by exactly one. Add the missing entry (copy an adjacent rule's shape/fields) and confirm both the count assertion and the exhaustiveness test pass.