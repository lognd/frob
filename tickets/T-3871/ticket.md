---
id: T-3871
title: 'DEAD001 (unreferenced private symbol) burn-down: 36 unwaived findings'
state: queued
kind: bug
origin: agent
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
T-3844 burn-down: this rule/cluster (DEAD001) carried 36 unwaived warning-level findings on the 2026-09-05 full unscoped 'frob check --no-cache' baseline measured for T-3844 (see that ticket's body for the full histogram). It is intentionally NOT promoted to error by T-3844 -- promoting a rule that still fires reds the build for everyone. This ticket's job: drive the live unwaived finding count for DEAD001 to zero (real fixes and/or reasoned frob:waive entries), then promote DEAD001 from warn to error in frob.toml's [gates.severity] T-1002 managed zone as a follow-up to this same campaign.