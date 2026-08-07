---
id: T-0040
title: 'frob mutate: mutation testing quality oracle'
state: done
kind: feature
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/mutate/**
- src/frob/app/mutate_runner.py
- src/frob/app/app.py
- src/frob/app/config.py
- src/frob/__main__.py
- tests/test_mutate.py
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_mutate.py::test_run_mutations_survivors_when_tests_weak
- tests/test_mutate.py::test_run_mutations_all_killed_by_strong_test
designated_repro_test: null
threat: null
component: null
---
