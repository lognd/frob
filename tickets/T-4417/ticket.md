---
id: T-4417
title: Instrument land phases with per-phase elapsed-seconds timestamps
state: queued
kind: feature
origin: human
created: '2026-09-11'
priority: high
parent: T-4410
tier: story
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN a land runs WHEN each phase (worktree setup, graph load, gate check,
    test run, squash, sweep dispatch, etc.) starts and ends THEN the land log emits
    a line carrying that phase's elapsed seconds
  evidence: []
- text: GIVEN this instrumentation lands WHEN a slow land is investigated THEN the
    per-phase breakdown is readable directly from the land log without needing ps
    or external profiling
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The land log today carries no phase timestamps, so the T-4408 land's 50+ minutes could not be attributed to a specific phase without external ps inspection. Add elapsed-seconds timestamps to every phase boundary in the land log so future slow lands are diagnosable from the log alone.