---
id: T-1115
title: 'arch: split remaining ~14 gate families out of src/frob/gates/__init__.py
  (~9802 lines) -- T-1077 residue refile'
state: done
kind: feature
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/modules/gates.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestDebtGate::test_debt001_malformed_directive_is_reported
- tests/test_gates.py::TestDebtGate::test_debt002_closed_ticket_is_reported
- tests/test_gates.py::TestDebtGate::test_debt003_expired_by_date_is_reported
- tests/test_gates.py::TestDebtGate::test_clean_debt_produces_no_violations
- tests/test_gates.py::TestDebtGate::test_lists_every_debt_entry
- tests/test_gates.py::TestDeprecatedGate::test_depr001_malformed_directive_is_reported
- tests/test_gates.py::TestDeprecatedGate::test_depr002_closed_ticket_is_reported
- tests/test_gates.py::TestDeprecatedGate::test_depr003_in_window_warns
- tests/test_gates.py::TestDeprecatedGate::test_depr004_past_sunset_errors
- tests/test_gates.py::TestDeprecatedGate::test_depr005_new_caller_errors
- tests/test_gates.py::TestDeprecatedGate::test_clean_deprecated_produces_no_violations
- tests/test_gates.py::TestDeprecatedGate::test_lists_every_deprecated_entry
designated_repro_test: null
acceptance:
- text: GIVEN src/frob/gates/__init__.py WHEN the remaining gate families (DEBT/DEPR,
    SCOPE/PREWORK, INV00x, TEST00x, DECISIONS, TICK00x, COMPLIANCE00x, SYS00x/DOC00x,
    DUP00x, REL00x, FUZZ00x, DOCLINK/DOCANCHOR, PERF, run_gates spine, COV00x) are
    extracted one cohesive family per land THEN gates/__init__.py drops below the
    800-line large-file threshold with no public API change and all existing tests
    pass
  evidence:
  - tests/test_gates.py::TestDebtGate::test_debt001_malformed_directive_is_reported
threat: null
component: null
---
Refile of T-1077's residue draft, which died at land (TICK006 phantom repaired by the coordinator). T-1077 extracted the TODO00x/FMT001 family (gates/__init__.py 10164 -> ~9802); the remaining families follow T-1072/T-1077's one-family-per-land discipline: verbatim moves with directives intact, lazy call-time imports back to frob.gates where init-time circularity threatens, re-export only externally-called names, split-carried INV006 waivers where prose moves.