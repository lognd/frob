---
id: T-3723
title: frob coverage --full fails with no data to report, injects -n without xdist
state: queued
kind: bug
origin: human
created: '2026-09-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/coverage/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
apollo FROBLEMS.md 2026-09-03: frob coverage --full runs pytest with --cov-report= then coverage xml -i, which dies with 'No data to report' (no .coverage produced by its own pytest invocation). Also its first failure mode was injecting -n 12 into a repo without pytest-xdist installed (exit 4 usage error, reported as 'suite was RED'). Manual workaround: uv run pytest --cov + uv run coverage xml -i + frob check --stamp-coverage works.