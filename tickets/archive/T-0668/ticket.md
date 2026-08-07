---
id: T-0668
title: 'strata: exact interface-conformance check - declared node interface == real
  public code surface'
state: done
kind: security
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0667
parent: T-0341
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- src/frob/graph/**
- docs/modules/strata.md
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_undeclared_public_symbol_fires
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_declared_but_absent_symbol_fires
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_exact_match_is_silent
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_node_with_no_interface_attr_is_never_checked
- tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_dunder_all_overrides_name_based_collection
designated_repro_test: null
acceptance:
- text: Given a node declaring fewer public symbols than the bound module exports,
    when checked, then the obligation fires
  evidence:
  - tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_undeclared_public_symbol_fires
- text: Given a node declaring a symbol the bound module does not export, when checked,
    then the obligation fires
  evidence:
  - tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_declared_but_absent_symbol_fires
threat: null
component: null
---
A node's declared interface must equal the bound module's real public surface (no under- or over-declaration) -- closes acceptance-criterion (2). Depends on coverage-totality's binding pass existing first (need a bound node before its interface can be checked).