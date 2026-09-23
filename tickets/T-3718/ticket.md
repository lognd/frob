---
id: T-3718
title: vet source scanner misses .venv-installed packages, only checks cache path
state: queued
kind: bug
origin: human
created: '2026-09-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 1.1.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_scan.py
- src/frob/vet/_registry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: v1.1.0
  new_value: v0.539.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
apollo FROBLEMS.md 2026-09-03: VET-SOURCE-UNAVAILABLE fires on typing-extensions/python-dotenv even though both are installed in .venv (uv sync succeeded). The scanner appears to look only in a cache path, not the environment it could resolve source from.