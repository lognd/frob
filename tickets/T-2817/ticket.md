---
id: T-2817
title: document T-2807's unattributed-land-process probe in coordinator-scripts.md
state: done
kind: docs
origin: human
created: '2026-08-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/guides/coordinator-scripts.md
- scripts/wait_for_land_slot.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: scripts/wait_for_land_slot.py
  reason: clearing the two COV001/AFFECT001 waivers T-2807 took only because this
    doc was leased by T-2755 at the time; that lease is now released
  actor: logan
  at: '2026-08-21'
evidence:
- cmd:./scripts/.t2817_evidence_check.sh exit=0 sha256=4fa85af22da8
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2807 added scripts/wait_for_land_slot.py::probe_unattributed_land_process and wired it into wait_for_slot's unattributed_probe gate, but docs/guides/coordinator-scripts.md was leased by a concurrent ticket (T-2755) for T-2807's whole worktree lifetime, so COV001/AFFECT001 were waived there instead of fixed. Add a #probe_unattributed_land_process anchor and update the #wait_for_slot section to describe the new gate, then clear the two waivers in scripts/wait_for_land_slot.py.