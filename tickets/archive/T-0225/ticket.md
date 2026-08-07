---
id: T-0225
title: TEST003 fires on design/ dir; strata ids need e2e-binding obligation not unit/integration
  gates
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/lang/_walk_strata.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestTestGate::test_test003_exempts_strata_design_files
- tests/test_gates.py::TestConventionUnitBinding::test_test009_fires_on_unbound_design_file
- tests/test_gates.py::TestConventionUnitBinding::test_test009_satisfied_by_e2e_edge
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 10: T-0168 exempted .strata from TEST001/TEST002 but TEST003 ('interface design has 0 integration tests') still fires on the design dir (graphite +16 findings). Per the refs, system ids bind kind=e2e. Decide + implement consistently with T-0168: exempt design artifacts from TEST003, and (design decision, document it) whether a SYS-family obligation should demand e2e bindings for flows instead.