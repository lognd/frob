---
id: T-0273
title: 'dup exact_regions: O(k^2) pair emission needs a run-size guard before [dup].region_kernel
  ships enabled'
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: T-0187
tier: ticket
sprint: null
scope:
- frob-core/**
- src/frob/dup/**
- tests/**
- docs/modules/dup.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_dup_core.py::TestExactRegions::test_run_size_guard_bounds_pair_emission_and_signals_truncation
- tests/unit/test_dup_core.py::TestExactRegions::test_run_size_guard_does_not_trip_below_the_cap
designated_repro_test: null
threat: null
component: null
---
T-0193 review finding (non-blocking, feature is off by default): emit_run_pairs is unbounded O(k^2) in run size -- reviewer demonstrated 2000 identical 20-token docs => 1,999,000 pairs in 17.5s, no cap/guard/warning. A real monorepo with thousands of near-identical generated/boilerplate symbols sharing a block >= region_min_tokens would hit multi-second-to-worse pair emission. Add a run-size guard BEFORE anyone flips [dup].region_kernel=true in a real frob.toml: options -- skip/report-truncated beyond some k with a WARN, or downgrade to reporting only the top-N longest matches per run, or cap total pairs with an honest 'truncated at N' signal (never silently drop without a signal, T-0193-recall-bug lesson). Regression: a large-k fixture completes under a time/pair bound and emits the truncation signal.