---
id: T-0651
title: 'strata: MESSAGE SCHEMA VERSION obligation on events/queues'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0331
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_message_schema.py::TestMissingSchemaVersion::test_queue_node_without_schema_version_fires
- tests/unit/strata/test_message_schema.py::TestMissingSchemaVersion::test_event_node_without_schema_version_fires
- tests/unit/strata/test_message_schema.py::TestMissingSchemaVersion::test_discharged_and_non_event_queue_nodes_clean
- tests/unit/strata/test_message_schema.py::TestMissingSchemaVersion::test_waiver_discharges_finding
- tests/unit/strata/test_message_schema.py::TestUnprovenSchemaVersion::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_message_schema.py::TestUnprovenSchemaVersion::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_message_schema.py::TestUnprovenSchemaVersion::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
designated_repro_test: null
acceptance:
- text: Given an event/queue node with no schema version declared, when checked, then
    the obligation fires
  evidence:
  - tests/unit/strata/test_message_schema.py::TestMissingSchemaVersion::test_queue_node_without_schema_version_fires
  - tests/unit/strata/test_message_schema.py::TestMissingSchemaVersion::test_event_node_without_schema_version_fires
  - tests/unit/strata/test_message_schema.py::TestMissingSchemaVersion::test_discharged_and_non_event_queue_nodes_clean
  - tests/unit/strata/test_message_schema.py::TestMissingSchemaVersion::test_waiver_discharges_finding
  - tests/unit/strata/test_message_schema.py::TestUnprovenSchemaVersion::test_declared_with_no_code_evidence_fires
  - tests/unit/strata/test_message_schema.py::TestUnprovenSchemaVersion::test_declared_with_real_code_evidence_discharges
  - tests/unit/strata/test_message_schema.py::TestUnprovenSchemaVersion::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
threat: null
component: null
---
Every event/queue node must declare a message schema version for backward-compat tracking.