---
id: T-draft-5ff600a1
title: 'Drainer lifecycle: a land-queue cycle in the frob serve daemon with single-drainer
  lock, progress-aware deadline, and queue/stuck-since in frob status'
state: queued
kind: feature
origin: human
created: '2026-09-21'
priority: high
blocked_by:
- T-4738
- T-3270
parent: T-5106
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/serve/_daemon.py
- src/frob/tickets/_land_queue.py
- src/frob/app/status_runner.py
- tests/unit/serve/**
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
Leaf E of T-5106 (~3 pts). The drainer has a lifecycle: a cycle in the existing daemon, not a third process. Blocked by T-4738 (land-status.json) and T-3270 (progress-aware deadline).
- `frob serve`'s `_daemon.py` gains a land-queue poll cycle that calls `drain_next` for one entry per cycle when the land-queue lock is free; single-drainer is enforced by holding `.frob/land-queue.lock` for the cycle, so a second drainer is a refusal, not "safe but wasteful".
- Per-land deadline uses T-3270's progress-aware budget; on timeout the entry is marked failed with "timed out at phase X" from `.frob/land-status.json` and leaf D's unwind runs.
- `frob status` shows queue depth, the landing entry with its current phase and "stuck since" when a phase exceeds its median by 3x, and the last N results; the coordinator stops tailing /tmp logs.
- A one-shot `frob ticket land --drain` stays for cron/CI deployments (T-1444 design question 3 answered: the daemon is the lifecycle, the one-shot is the fallback).
