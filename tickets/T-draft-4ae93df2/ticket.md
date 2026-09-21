---
id: T-draft-4ae93df2
title: 'explore_runner.py: open parse-artifact cache read-only for single-process
  explore commands'
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/explore_runner.py
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
found while working T-5135 (perf audit H-item, xref/map 11s): lang._parse_file_with_artifact_cache is a passthrough whenever PARSE_ARTIFACT_CACHE_ENV is unset, which is every single-process command including frob explore -- 1643 uncached parses measured on frob explore xref. Fix direction: stamp/open the artifact cache read-only for explore commands, same as gate workers do. Could not fix under T-5135: explore_runner.py was removed from T-5135's scope due to a live cross-worktree lease collision with T-4690.