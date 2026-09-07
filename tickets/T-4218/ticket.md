---
id: T-4218
title: 'strata: declare client-persisted browser storage as a capability with cleared_on
  triggers, and require a code path per trigger'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4157
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata
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
Consolidates T-4157/H4-7 (localStorage used with SPEC-023 saying 'no storage' -- undeclared privacy-surface import, would fail SYS100 if declared as a capability e.g. browser.local_storage) with F-362/M4-6 (T-4166 -- a return-path stash's lifecycle has write/consume/invalidate-on-logout events and only two are implemented; declare browser-persisted state with cleared_on='logout,consume' and require a code path for each declared trigger). Not fixture-testable in frob's own tree: no browser storage surface exists here.