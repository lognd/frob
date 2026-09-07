---
id: T-4223
title: split a display-only error-code list into a display axis and a needs-client-recovery
  axis, and require the totality test to answer both
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: low
parent: T-4166
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates
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
Consumer F-362/M4-5 (T-4166): a display-layer list (IGNORED_ERROR_CODES) is used to discharge a recovery question -- the totality test checks only that every backend code appears in one of two lists, not whether the code needing a recovery ACTION (e.g. re-bootstrapping CSRF) got one. Split into DISPLAY_ONLY and a second, independently-answered axis, with the totality test asserting both. Related family to T-4166's own registry-vs-surface totality theme (F-373 in T-4175) but a distinct code path -- kept separate rather than merged. Not fixture-testable in frob's own tree: no client/server error-code registry duo exists here.