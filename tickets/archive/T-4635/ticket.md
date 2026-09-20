---
id: T-4635
title: land loads a full snapshot in _record_verify_intent_for_landed_commit AFTER
  publishing (10+ min in the serial land critical path); defer the verify-intent snapshot
  to the async sweep or reuse the pre-land snapshot
state: dropped
kind: bug
origin: human
created: '2026-09-19'
priority: critical
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
## Drop reason
- 2026-09-19: same root cause as T-4634 (_record_verify_intent_for_landed_commit's post-publish snapshot reload); T-4634's fix (reuse the pre-publish snapshot) is the one change that closes both (absorbed by T-4634)
