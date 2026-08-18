---
id: T-2409
title: no kotlin test collector (test_discovery capability gap)
state: queued
kind: feature
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/testing/_collect_kotlin.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2365's adapter-capability conformance axis (frob.lang._support.derive_capability_registry) marks test_discovery KNOWN_GAP for kotlin: frob.testing has collect_python_tests/collect_rust_tests/collect_ts_tests/collect_cpp_tests but no kotlin collector, even though frob.lang has a real kotlin grammar (T-0723). Add collect_kotlin_tests mirroring collect_ts_tests's shape (or the closest JVM-toolchain analogue) and wire it into frob.testing.__init__.