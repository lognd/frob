---
id: T-0173
title: sys audit output repeats identical WARNING blocks across all views
state: done
kind: ux
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/sys_runner.py
- src/frob/strata/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_audit.py::TestGroupGaps::test_group_gaps_by_view
designated_repro_test: null
threat: null
component: null
---
logand.app pilot: the same WARNING blocks print once per configured view (8x duplication), burying the per-view differences that matter. Deduplicate: print shared findings once with a views-affected annotation, keep per-view sections for view-specific results only. Snapshot-test the output shape.