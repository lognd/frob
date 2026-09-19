---
id: T-3825
title: 'F-020: frob check --only sys SELFAUDIT001/SYS103 reports files as unbound
  that ARE bound by a multi-glob code= line (or stale .frob design cache) -- gate
  cannot go green; fix multi-glob code binding / cache freshness'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: T-4665
tier: ticket
sprint: v1.1.0
runs_last: false
milestone: v1.1.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: null
  new_value: T-4665
  reason: '2026-09-19: SF-17 in the STRATA friction audit; joins story B of epic T-4662
    -- a false positive that blocks green and whose stale-cache half interacts with
    T-4669'
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
