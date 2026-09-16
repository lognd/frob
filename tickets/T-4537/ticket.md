---
id: T-4537
title: Declare env.read capability for src/frob/doctor.py's Unity toolchain env lookups
  in design/frob.strata
state: dropped
kind: ux
origin: human
created: '2026-09-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
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
T-4501 added os.environ.get reads to src/frob/doctor.py (_unity_hub_default_roots, _locate_unity_editor) for UNITY_PATH/UNITY_EDITOR/PROGRAMFILES. This trips gate:SELFAUDIT (SELFAUDIT001, node=cli capability env.read observed but not declared) since src/frob/doctor.py is not yet in design/frob.strata's env.read via-list (line ~195). T-4501 could not add it because design/frob.strata was LIVE-leased by T-3613 for that ticket's whole work window -- inline frob:waive SELFAUDIT001 added at both sites in the meantime (same T-3020/T-3014 precedent in src/frob/gates/_narrative_blocks.py). Add 'src/frob/doctor.py' to the env.read via-list and remove the two inline waivers.

## Drop reason
- 2026-09-16: declaration added by the coordinator in T-4501's own land (cli env.read via src/frob/doctor.py)
