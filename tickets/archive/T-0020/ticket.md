---
id: T-0020
title: 'Gate convergence: collection oracle, evidence matching, fixture excludes'
state: done
kind: bug
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- tests/**
- invariants/**
- scripts/**
- pyproject.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestSeverityOverrides::test_override_downgrades_and_ignores_garbage
- tests/test_prework_parity.py::TestCliStartRecordsGateCompatibleDigest::test_start_then_gate_is_clean
- tests/test_graph.py::TestCorruptCacheRecovery::test_garbage_cache_file_is_recreated
designated_repro_test: null
threat: null
component: null
---
