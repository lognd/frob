---
id: T-5157
title: cache load_archive across ticket new side-effect checks
state: queued
kind: feature
origin: human
created: '2026-09-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_archive.py
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
Found while working T-3993: profiling frob ticket new on this repo (711 active + ~4048 archived tickets) shows 5 independent load_archive calls inside one command (scope-closure warnings, scope-overlap warnings, orphaned-lock scan, plus new_ticket itself), each re-parsing the FULL archived-ticket set from scratch -- ~20k YAML parses, ~70s of a ~95s run. Cache/memoize the archive parse for the duration of one process (or thread a shared parsed-archive object through the call sites) so repeat callers in the same command do not re-read+re-parse the same files. Out of T-3993 scope (src/frob/app/ticket_runner/_new.py only).