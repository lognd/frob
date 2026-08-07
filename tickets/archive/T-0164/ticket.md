---
id: T-0164
title: COV002 demands per-declaration frob:ticket edges inside .strata files -- boilerplate
  x28
state: done
kind: ux
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
- tests/test_gates.py::TestCov002StrataModuleCoverage::test_module_level_ticket_edge_covers_nested_declaration
- tests/test_gates.py::TestCov002StrataModuleCoverage::test_declaration_without_module_edge_still_fires
designated_repro_test: null
threat: null
component: null
---
Typani pilot: COV002 required a frob:ticket directive on every strata declaration (module/node/flow/assert) individually -- ~28 copy-paste edges for one ticket with no granularity value. Design decision needed: either a module-level directive in a .strata file covers all its declarations (likely right -- a design file is one artifact), or document why per-declaration edges matter. Whichever way, kill the boilerplate.