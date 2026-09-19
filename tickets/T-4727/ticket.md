---
id: T-4727
title: record verb/subverb for --help and argparse usage-error exits
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/__main__.py
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
found while working T-4689: argparse's own --help and usage-error SystemExit happen inside parser.parse_args, before App()/timed_call is ever entered, so those exits record no telemetry row at all (not even an empty one). frob ticket show T-4689 for context on the verb/subverb fields this would need to carry.