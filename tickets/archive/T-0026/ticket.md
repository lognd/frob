---
id: T-0026
title: 'Unify exclude surface: dup/arch/cycle scanners must respect [graph] exclude'
state: done
kind: bug
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/cycle_runner.py
- src/frob/arch/**
- src/frob/cycle/**
- src/frob/dup/**
- src/frob/excludes.py
- src/frob/graph/**
- tests/test_excludes.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_excludes.py::test_dup_scanner_honors_exclude
- tests/test_excludes.py::test_load_and_match_globs
designated_repro_test: null
threat: null
component: null
---
