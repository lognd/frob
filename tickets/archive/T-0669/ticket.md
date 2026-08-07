---
id: T-0669
title: 'strata: PURPOSE contract - node purpose carries an allowed-effect profile
  checked against code'
state: done
kind: security
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0667
parent: T-0341
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- src/frob/graph/**
- docs/modules/strata.md
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestPurposeContract::test_read_only_purpose_with_write_effect_fires
- tests/unit/strata/test_selfconform.py::TestPurposeContract::test_effect_outside_profile_fires
- tests/unit/strata/test_selfconform.py::TestPurposeContract::test_unrecognized_profile_fires
- tests/unit/strata/test_selfconform.py::TestPurposeContract::test_effect_inside_profile_is_silent
- tests/unit/strata/test_selfconform.py::TestPurposeContract::test_node_with_no_purpose_attr_is_never_checked
designated_repro_test: null
acceptance:
- text: Given a node whose purpose declares a read-only effect profile but whose bound
    code performs a write, when checked, then the obligation fires
  evidence:
  - tests/unit/strata/test_selfconform.py::TestPurposeContract::test_read_only_purpose_with_write_effect_fires
threat: null
component: null
---
Each node's declared purpose must carry an allowed-effect profile (e.g. 'read-only query' cannot emit writes); real observed effects outside that profile fail via _effects.py::check_capability_conformance -- closes acceptance-criterion (3).