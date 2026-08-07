---
id: T-0036
title: 'frob stats: DORA-ish delivery measurement (queue health + commit cadence)'
state: done
kind: feature
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/stats/**
- src/frob/app/stats_runner.py
- src/frob/app/app.py
- src/frob/app/config.py
- src/frob/__main__.py
- tests/test_stats.py
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_stats.py::test_collect_combines_both
- tests/test_stats.py::test_commit_stats_classifies_conventional_types
designated_repro_test: null
threat: null
component: null
---
