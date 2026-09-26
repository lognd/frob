---
id: T-draft-418fe919
title: frob.toml [fix] disabled list and land --no-tier-a flag
state: queued
kind: feature
origin: human
created: '2026-09-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
flavour: null
due: null
rank: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/app/config.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/gates/_fix_engine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: DOC006 inline waivers (T-draft-7ee140de)
  actor: logan
  at: '2026-09-26'
  old_length: 790
  new_length: 896
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->Split from T-draft-e955fd26 deliverable 2: that ticket could not touch src/frob/app/config.py (scope collision with T-draft-fcfdafdf's live in-progress lease on the same file at start time). Deliver: (1) [fix] disabled = ["RULE", ...] in frob.toml/AppConfig, consumed by apply_tier_a_fixes'/_tier_a_pre_land_step's exclude computation as an ADDITIONAL source alongside the existing hardcoded exclude tuple; (2) --no-tier-a on frob ticket land as the explicit-flag tier (skips _tier_a_pre_land_step entirely for that invocation). T-draft-e955fd26 already ships TEST010 hardcoded-disabled in _tier_a_pre_land_step's exclude tuple as an interim measure; once this ticket's config knob exists, TEST010's disable can move from hardcoded to the default disabled list (still overridable per-repo).