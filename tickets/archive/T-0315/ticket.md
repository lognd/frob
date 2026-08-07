---
id: T-0315
title: TEST005 branch-coverage floor applies to test-file symbols (fixtures/helpers)
  -- should skip like TEST001
state: done
kind: bug
origin: auditor
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_coverage.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestTestGate::test_test005_skips_test_file_symbols
designated_repro_test: null
threat: null
component: null
---
FROBLEMS (lithos): TEST001/TEST002 skip symbols in test files (gates._is_test_file), but TEST005's per-symbol branch floor applies to test-file fixtures/helpers too. Environment-gated fixture branches (e.g. tool-unavailable fallbacks) can never reach the floor in CI without the tool, forcing pure-noise per-site waivers. Fix: TEST005 should skip test files exactly like TEST001/002 (reuse gates._is_test_file). Likely removes several of frob's own 180 T-0160 waivers too. Test: a test-file fixture with a gated branch does not produce TEST005.