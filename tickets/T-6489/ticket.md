---
id: T-6489
title: resilience gaps not in REL (SYSDESIGN301+)
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-6476
tier: story
sprint: sysdesign
runs_last: false
milestone: 0.539.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
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
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: resilience gaps not in REL (SYSDESIGN301+)
kind: feature
tier: story
parent: T-SYS-EPIC
milestone: 0.539.0
sprint: sysdesign
scope: (none -- story, no direct code scope)
blocked_by: []

Body:

Per SYSDESIGN-INVENTORY.md's REL-family conclusion ("health/timeout/retry/backoff/circuit-
breaker/bulkhead is EXHAUSTIVELY COVERED"), this story files only what REL genuinely does not
cover: deadline propagation across hops (distinct from REL200/201's per-hop timeout, PARTIAL
per the inventory), a server-wide/process retry budget (distinct from REL220's per-flow
backoff/jitter), request hedging (new grammar from Story A), and cache stampede-guard
declaration (new grammar from Story A). Idempotency-key-on-unsafe-retries is already COVERED
by REL221 and is not re-filed here.
