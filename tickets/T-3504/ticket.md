---
id: T-3504
title: Wire strata/graph/vet examined-sites into WAIVE004 (blocked pending a sound
  site-identity mapping)
state: queued
kind: feature
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_coverage_sites.py
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
Re-filed replacement for T-2057, which this ticket's own title duplicates verbatim: T-2057 was DROPPED (blocked pending a sound site-identity mapping) but 12 separate frob:waive WIRE001 sites across src/frob/app/ticket_runner/_land_cmd.py, src/frob/gates/_arch.py, src/frob/gates/_coverage_sites.py, src/frob/gates/_render_lint.py, and tests/unit/test_new_ticket_scope_overlap_warning.py cite follow_up="T-2057" as their live-ticket accountability anchor for a deliberately-permanent (not actually pending) WIRE001 waiver posture -- T-2057 dropping orphaned all 12 (WIRE002, T-3490's sweep regression). This ticket exists ONLY to give those waivers a real, open follow_up target again; it carries no work of its own beyond what T-2057 already described (still blocked on the same sound site-identity mapping prerequisite T-2057 was).