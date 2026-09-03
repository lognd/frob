---
id: T-3737
title: mark load-sensitive adversarial tests with bounded reruns (flaky marker)
state: queued
kind: ux
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
- tests/**
- pyproject.toml
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
CI flaky-test whack-a-mole: a different subset of adversarial concurrency/subprocess/socket stress tests fails each run under pytest -n auto on shared CI runners. Underlying bugs have been fixed round after round (cache: 9 rounds); residual failure is load-timing, not a deterministic bug. Apply @pytest.mark.flaky(reruns=2, reruns_delay=1) from pytest-rerunfailures (dev dep since T-3709) to the class of genuinely nondeterministic tests: two-process/concurrent race tests, subprocess daemon tests, socket bind timing tests. Mark ONLY provably load-timing tests, never a deterministic assertion.