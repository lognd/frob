---
id: T-5181
title: 'frob-arch lock-order-cycle reported on declared_source_prefixes (T-5117):
  sequential with-blocks flagged as nested'
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/_nodes.py
- src/frob/arch/_lock_order.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-09-21 04:40 (frob check --base dev): frob-arch:lock-order-cycle ERROR at src/frob/lang/_nodes.py:244/248 -- 'declared_source_prefixes acquires _declared_source_prefixes_cache_lock before _pyproject_data_cache_lock (244) and _pyproject_data_cache_lock before _declared_source_prefixes_cache_lock (248)'. Reading the code landed by T-5117: the first with-block releases the prefixes lock (return or fall-through) BEFORE declared_project_package_name takes the pyproject lock, so the acquisitions are sequential, not nested. Decide which is wrong: if the analyzer treats any two acquisitions in one function body as ordered regardless of nesting, that is an analyzer false positive to fix (with a regression test: sequential with-blocks must not be a cycle); if the second path really nests (a later with-block that calls back into the first lock), restructure declared_source_prefixes. Verify: the error disappears on frob check --base dev either way.