---
id: T-4435
title: 'Land spends 40+ min single-threaded after the wip commit: two load_all(worktree)
  calls in the sibling-state helpers'
state: queued
kind: bug
origin: agent
created: '2026-09-12'
priority: critical
parent: T-4410
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- tests/unit/test_land_sibling*.py
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
MEASURED 2026-09-12: the T-4434 land (pid 2845732) ran 81 minutes: 40 min pre-land (Tier-A fixes, BUG002 repro, native rebuild) then, after the wip commit logged at 00:22, 41 minutes single-threaded CPU-bound (utime rising ~1s/s, RSS 200MB, ONE thread, NO child processes, open fds = log + land.lock + one socket, no sqlite handle) with no further log line until the merge. The killed 98-minute T-4412 land on 2026-09-11 had the same shape (CPU-bound, no fds). Code path: src/frob/tickets/_land.py right after `_wip_commit` calls `_sibling_ticket_states(worktree, ...)` and `_sibling_reopen_log_signatures(worktree, ...)`, each of which calls `load_all(worktree)` -- two full ledger loads of 4000+ ticket dirs with no log line before or after, then the v2 store merge. Nothing else in that window spawns git. Every land pays this, so the serial land chain moves at ~1 land/hour. ACCEPTANCE: (1) a log line with elapsed time around each `load_all` in the post-wip stretch so the phase is visible; (2) one `load_all` per land shared by both sibling helpers (or the T-4397 per-run cache reused); (3) measured post-wip-to-merge time under 5 minutes on this checkout. Belongs with T-4410/T-4411 (land cost).
