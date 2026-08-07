---
id: T-0034
title: 'Wire fuzz+vet: FUZZ gate, frob test --fuzz, capability scan merge, gates degrade
  without diff'
state: done
kind: feature
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/fuzz/**
- src/frob/vet/**
- src/frob/gates/**
- src/frob/app/test_runner.py
- src/frob/app/config.py
- src/frob/__main__.py
- tests/test_fuzz.py
- tests/test_vet.py
- tests/test_gates.py
- tests/system/**
- pyproject.toml
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestGatesDegradeWithoutDiff::test_diff_independent_gates_run_without_git
- tests/test_vet.py::TestLockfileParsers::test_find_lockfile_uv
designated_repro_test: null
threat: null
component: null
---
