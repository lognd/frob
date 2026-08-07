---
id: T-0093
title: 'strata grammar: explicit trust clause for queue/balancer'
state: done
kind: feature
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- strata-core/src/parse.rs
- src/frob/strata/_ast.py
- src/frob/strata/_infra.py
- tests/unit/strata/test_infra.py
- docs/strata/surface.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_infra.py::TestQueueDesugar::test_queue_no_trust_clause_defaults_to_trusted
- tests/unit/strata/test_infra.py::TestQueueDesugar::test_queue_explicit_trust_clause_wins_over_default
- tests/unit/strata/test_infra.py::TestBalancerDesugar::test_balancer_explicit_trust_clause_wins_over_default
designated_repro_test: null
threat: null
component: null
---
T-0064 discovery: std.infra's queue/balancer grammar has no TRUST clause (unlike store/cache/cdn), so _infra.py::elaborate_infra defaults both to "trusted" -- documented in docs/strata/surface.md#std-infra as a deliberate deviation. Add an optional (or mandatory, per law 2) trust clause to the queue/balancer grammar productions and thread it through StoreDecl-sibling AST models and elaborate_infra instead of the hardcoded default.