---
id: T-0037
title: 'Smart-dup: frob-core Rust kernels + DUP gate + build wiring'
state: done
kind: feature
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- frob-core/**
- src/frob/dup/**
- src/frob/gates/**
- tests/test_dup_smart.py
- tests/test_excludes.py
- tests/test_gates.py
- Makefile
- .github/**
- docs/**
- tests/fixtures/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_dup_smart.py::TestFindClones::test_finds_renamed_clone_pair
- tests/test_gates.py::TestGatesDegradeWithoutDiff::test_diff_independent_gates_run_without_git
designated_repro_test: null
threat: null
component: null
---
