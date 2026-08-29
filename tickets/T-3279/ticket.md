---
id: T-3279
title: Re-stamp abandoned deprecated-baseline and ratchet locks (DEPR006/WAIVE011)
state: queued
kind: bug
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
- frob-deprecated-baseline.lock.json
- frob-ratchet.lock.json
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
T-3243's sweep found DEPR006 (frob-deprecated-baseline.lock.json unstamped for 1198 commits since 2026-07-28) and WAIVE011 (frob-ratchet.lock.json unstamped for 1410 commits since 2026-07-23) both firing repo-wide -- pre-existing accumulated drift, not caused by T-3228's own change. Remedy per each finding's own message: re-run tighten_deprecated_baseline and commit the refreshed lock (DEPR006), and run frob pool snapshot RULE for each stale pool and commit the updated lock (WAIVE011) -- or pin either as a deliberate freeze if that is the actual decision. Left unfixed in T-3243 (a sweep-regression ticket) because a full re-stamp across this many commits is real, standalone maintenance work, not a quick fix.