---
id: T-0514
title: 'strata audit G10: differential/property tests for FactBase''s native Rust
  kernels'
state: done
kind: security
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/strata/
- strata-core/src/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_kernel_properties.py::test_propagated_demand_matches_fixpoint_oracle
- tests/unit/strata/test_kernel_properties.py::test_propagated_demand_is_deterministic
- tests/unit/strata/test_kernel_properties.py::TestZeroDeclaredRateFedCycle::test_self_loop_fed_by_literal_zero_rate_reports_unbounded
designated_repro_test: null
threat: null
component: null
---
Split from T-0497 (too large to rush inside that ticket's remaining budget -- needs a pure-Python reference implementation designed and cross-checked, not a rushed patch). docs/audits/strata.md finding G10: FactBase.reachable/worst_age/propagated_demand are native Rust kernels (strata-core), trusted from Python with no differential or property-based test suite proving the Rust and an independent reference implementation agree on the same inputs. A subtle divergence (an off-by-one in age propagation, a wrong SCC handling, a rounding difference in demand aggregation) could silently ship undetected since only end-to-end behavioral tests exercise the combined system, not the kernel in isolation against a trusted oracle. Fix direction: a pure-Python reference implementation of at least worst_age/reachable/propagated_demand (small, deliberately naive, no perf concerns) plus a property-based (hypothesis-style, or hand-authored adversarial corpus) differential test that generates random-ish FactBase graphs and asserts the Rust kernel and the Python reference agree on every one.