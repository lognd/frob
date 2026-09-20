---
id: T-draft-ed33feae
title: Bind follow_up ticket ids to 3 orphaned WIRE001 waivers (CI wire002 live-repo
  gate)
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: T-4806
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/dup/_legacy_cs.py
- tests/unit/test_land_merge_conflict_drop.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: test_wire002_zero_against_live_repo passes with zero WIRE002 findings
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 35476139324 on dev: tests/unit/gates/test_wire002_live_repo.py test_wire002_zero_against_live_repo fails because 3 live frob:waive WIRE001 sites are missing a follow_up attribute: src/frob/dup/_legacy_cs.py at _collect_locals_cs (line 36) and _serialize_cs_body (line 131), and tests/unit/test_land_merge_conflict_drop.py at _seed_widget_worktree (line 114). Add a follow_up pointing at a real open ticket to each waiver.