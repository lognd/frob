---
id: T-4400
title: Recovered from T-4399's phantom TICK006 citation of T-4313
state: queued
kind: bug
origin: agent
created: '2026-09-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.540.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.540.0
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
Auto-filed by the TICK006 Tier-A fix (T-1544): T-4399's Done report claimed T-4313 was filed, but T-4313 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> ift clean (0 errors, DRIFT002 resolved); frob check --ticket T-4399 clean for in-scope files (gate:FMT/gate:PRE now pass; remaining FAILs -- gate:DOC T-4313 phantom-ticket citation, gate:LARGE, gate:TICK TICK004/TICK006 backlog, ruff-format on src/frob/gates/__init__.py -- are repo-wide pre-existing