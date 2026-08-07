---
id: T-0070
title: strata errors-total, panics-contained, observe blocks (ERR/OBS gates)
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0050
parent: T-0051
tier: ticket
sprint: null
scope:
- docs/strata/**
- tickets.md
- strata-core/**
- Makefile
- .github/**
- design/litmus/**
- src/frob/strata/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_observe.py::TestObservabilityHappyPath::test_errors_total_and_panics_become_node_attrs
- tests/unit/strata/test_observe.py::TestObservabilityFailClosed::test_unknown_log_class_is_rejected
- tests/unit/strata/test_observe.py::TestObservabilityHappyPath::test_errors_total_without_observe_is_non_fatal
designated_repro_test: null
threat: null
component: null
---
Exhaustive ErrorSet consumption + variant liveness + no-discarded-Result (graph join); per-language panic chokepoints; observe = obligated labeled flows to an observability node; log rules enable detection SLAs via the cascade.