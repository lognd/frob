---
id: T-4410
title: 'Large-project landing: scoped pre-land sweep, CI as the unscoped authority'
state: queued
kind: feature
origin: human
created: '2026-09-11'
priority: high
parent: null
tier: epic
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
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
Owner design decision (2026-09-11): for large projects, frob ticket land must not run the full gate suite or full test suite synchronously; CI/CD is the single source of full-suite/full-gate runs. Under the rapid profile, frob ticket land still runs the T-1463 baseline-capture thread -- a full in-process frob check -- because it feeds the post-land sweep (src/frob/app/ticket_runner/_land_cmd.py around line 5570, comment citing T-1575's deferred baseline-thread-free rapid path). With ~4200 tickets and ~1400 files that check takes 25-45 minutes per land (T-4408 land: 50+ min at 100% CPU, single thread, no children); T-4397 only cut the ticket gate's share. Tests already run touched-set under rapid; the cost is gates. This epic covers replacing the synchronous unscoped sweep with a scoped one, moving the unscoped sweep to a rate-limited detached batch, and making CI the declared unscoped authority.