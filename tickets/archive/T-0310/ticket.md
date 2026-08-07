---
id: T-0310
title: SYS101 fires unfixably on nodes whose entire code glob resolves to [graph].exclude'd
  paths
state: done
kind: bug
origin: auditor
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_selfconform.py
- src/frob/strata/_host_isolation.py
- tests/**
- docs/strata/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestStaleDesign::test_stale_design_skips_node_fully_within_graph_exclude
- tests/unit/strata/test_selfconform.py::TestStaleDesign::test_stale_design_still_fires_when_node_has_non_excluded_file
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
designated_repro_test: null
threat: null
component: null
---
