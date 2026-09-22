---
id: T-draft-a7b46c03
title: squawk migration-safety adapter
state: queued
kind: feature
origin: human
created: '2026-09-22'
priority: high
parent: T-5148
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/sql/_squawk_adapter.py
- src/frob/doctor.py
- tests/fixtures/sql/**
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
_RELEVANT_TOOLS entry for squawk (T-5139 pattern, OPTIONAL_FOR_GATE -- migrations are a narrower relevance than the whole SQL family), relevant_when = a migrations directory exists. Spawn+parse squawk's JSON output into frob Violations: NOT-NULL-without-default, index-without-CONCURRENTLY, lock-taking rewrites. Fixture: a migration file with each planted anti-pattern.