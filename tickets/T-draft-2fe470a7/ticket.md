---
id: T-draft-2fe470a7
title: 'frob coord watch: land, quarantine and CI events as one stream'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.535.0
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
frob coord watch: an event stream for the coordinator (one line per event, exits on demand): land outcomes as entries change status, quarantine raise/clear transitions, and CI run completion with per-job results by subscribing to frob ci watch (never a second poller). Positive control: a fixture queue transition and a fixture run completion each emit exactly one line. Replaces the coordinator's three shell monitor loops.
