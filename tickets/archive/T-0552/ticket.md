---
id: T-0552
title: 'gates: native-language frob:tests edges get TEST001-004 credit with zero execution
  (B3)'
state: done
kind: bug
origin: auditor
created: '2026-07-21'
priority: high
parent: T-0403
tier: ticket
sprint: null
scope:
- src/frob/gates/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestTest013NativeUnverified::test_fires_on_structural_only_edge
- tests/test_gates.py::TestTest013NativeUnverified::test_silent_on_executed_edge
designated_repro_test: null
threat: null
component: null
---
docs/audits/gates-accounting.md B3/E3. _edge_has_execution_evidence: for TS/C/C++ (_NATIVE_TEST_EXTENSIONS) an edge counts as valid execution evidence if it merely looks like test code by name/path and resolves in the snapshot -- frob runs no TS/C/C++ test collector, so it is never actually executed. An empty void test_foo(){} satisfies TEST001-004. RIGHT-WAY fix direction: either wire real TS/C/C++ test collectors (vitest/ctest already exist per-pipeline per T-0404 finding 1 -- join their results into gate evidence) or mark native frob:tests edges as an explicit degraded 'unverified' state that does not silently satisfy TEST001. Overlaps T-0404 finding 1 (gates not run in native pipelines at all) -- coordinate the two fixes.