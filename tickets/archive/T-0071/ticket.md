---
id: T-0071
title: 'strata-core: independent Rust/PyO3 kernel crate (closure + propagation)'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
parent: T-0051
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- tests/unit/strata/**
- docs/strata/**
- tickets.md
- pyproject.toml
- strata-core/**
- Makefile
- .github/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_facts.py::TestClosure::test_boundaries_stop_taint_unless_asked_otherwise
- tests/unit/strata/test_facts.py::TestClosure::test_worst_age_reports_unbounded_on_a_positive_cycle
- tests/unit/strata/test_litmus_payments.py::TestGoldenFindings::test_golden_2_refund_decision_reads_a_stale_replica
designated_repro_test: null
threat: null
component: null
---
Own crate mirroring the frob-core maturin pattern; NOT shared with lithos (inspiration only). Kernels: fixpoint closure, staleness/capacity propagation over big models. No pure-Python fallback once adopted.