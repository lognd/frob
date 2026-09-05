---
id: T-3863
title: 'ticket-hygiene family (TICK003/004/007/012/014) burn-down: 917 unwaived findings'
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
T-3844 burn-down: this rule/cluster (TICK003,TICK004,TICK007,TICK012,TICK014) carried 917 unwaived warning-level findings on the 2026-09-05 full unscoped 'frob check --no-cache' baseline measured for T-3844 (see that ticket's body for the full histogram). It is intentionally NOT promoted to error by T-3844 -- promoting a rule that still fires reds the build for everyone. This ticket's job: drive the live unwaived finding count for TICK003,TICK004,TICK007,TICK012,TICK014 to zero (real fixes and/or reasoned frob:waive entries), then promote TICK003,TICK004,TICK007,TICK012,TICK014 from warn to error in frob.toml's [gates.severity] T-1002 managed zone as a follow-up to this same campaign.