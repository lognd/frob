---
id: T-draft-ba249d18
title: 'TEST010 fixer: move a production-side frob:tests declaration onto the test
  symbol instead of only deleting it'
state: queued
kind: feature
origin: agent
created: '2026-09-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
due: null
rank: null
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
scope:
- src/frob/gates/_fix_engine_text.py
- src/frob/gates/_fix_engine.py
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
Reported by the crunk session (2026-09-26): a TEST010 direction flip (moving
frob:tests from production symbols to the test symbols) had no automated fix,
so an agent parsed 389 TEST010 messages and scripted the moves by hand.

Verified against dev b41443f46d: a Tier-A TEST010 handler exists
(`fix_test010_redundant_test_declaration`) but it only DELETES a redundant
production-side declaration (T-4710/T-5261); when the test side has no
declaration yet, the fix leaves the binding lost. Deliver: when the named
test symbol exists and carries no frob:tests, the fixer writes the directive
at the test symbol (same reason text) and then deletes the production-side
copy; when the test symbol cannot be resolved, keep today's behaviour.
Positive control: a fixture where the test side lacks the directive; after
--fix the directive exists on the test side and TEST010 no longer fires.
