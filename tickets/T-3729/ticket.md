---
id: T-3729
title: frob internal pytest spawn ignores project venv -> re-verification SKIPPED-UNMEASURED
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
apollo FROBLEMS.md 2026-09-03: land/reverify/evidence claim pytest-xdist missing though project venv has it; frob spawn uses a different interpreter/addopts, causing claims re-verification SKIPPED-UNMEASURED every land -- real measurement hole, deeper than T-3722. Fix: spawn uses project venv interpreter + addopts.