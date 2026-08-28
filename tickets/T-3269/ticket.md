---
id: T-3269
title: fleet_status cannot distinguish live check contention from stalled agents
state: queued
kind: feature
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/fleet_status.py
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
found while working T-3256 (frob check admission budget).

fleet_status cannot distinguish "N frob check processes are legitimately live and
contending for the box" from "N agents are stalled". host_load() already reads
1-minute load average + MemAvailable; stale_forkserver_count/_derive_forkserver_stale_after_s
already count OLD/orphaned forkservers -- but nothing counts or characterizes YOUNG, live
forkservers as a distinct "contention" signal. T-3256's own field measurement (six
concurrent frob check runs, 51 forkservers all 137-194s old, load 35.89) would present to
an operator reading fleet_status identically to six genuinely stalled agents: elevated
load, low free memory, many forkserver processes, none flagged stale.

WHAT TO BUILD: a fleet_status signal that reports live (non-stale) forkserver count +
their age distribution alongside host_load, so "contention" (many young, active
forkservers) reads differently from "stall" (few forkservers, or old ones past the stale
threshold). T-3256 (src/frob/check/__init__.py's new cross-process admission registry
under .frob/check-admission/) may be a usable data source: it already tracks one live
marker per concurrently-running frob check PID with a start timestamp, which is a more
direct "how many checks are contending right now" signal than inferring it from
forkserver age heuristics.
