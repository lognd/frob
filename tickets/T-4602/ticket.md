---
id: T-4602
title: Wire CONFIGPATH001/ROUTE001 gates into the gate registry and docs/modules/gates.md
state: dropped
kind: feature
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: T-4221 hit the same design/frob.strata lease conflict as the docs/modules/gates.md
    one this ticket already tracks; recording the specific via-list fix needed
  actor: logan
  at: '2026-09-19'
  old_length: 1018
  new_length: 1639
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4114 (config_path_default_gate/CONFIGPATH001) and T-4115 (route_response_model_gate/ROUTE001) both add a standalone, fully-tested gate module + docs page, but neither is wired into src/frob/gates/__init__.py's gate dispatch table/_KNOWN_GATE_RULES, and neither rule appears in docs/modules/gates.md's own rule table or the file's frob:enumerates directive -- both were out of scope for T-4114/T-4115 (declared scope is just the gate module + its test file), and docs/modules/gates.md itself was leased by T-4111 for the whole duration of both tickets' work, so its own rule-table row could not be added there either. Wire both gates into the dispatch table (gate name config_path_defaults / route_response_model, matching each module's own tests) and add their rule-table rows + frob:enumerates entries to docs/modules/gates.md once free, or fold the standalone docs pages (docs/modules/gate-config-path-defaults.md, docs/modules/gate-route-response-model.md) into it and update each gate's frob:doc anchor to match.

Also fold in: src/frob/gates/_inv.py's time_stable_gate/_spawn_time_stable_test/time_stable_offset_s (T-4221, INV010) read os.environ and spawn a pytest subprocess -- SYS100/SELFAUDIT fires on both (env.read, exec) because design/frob.strata's gates component env.read/exec via-lists (currently keyed on src/frob/gates/_bug_repro.py only) do not yet name _inv.py. design/frob.strata was leased by T-4111 for T-4221's entire duration (the same lease conflict T-4221's own Done report names for docs/modules/gates.md), so this could not be fixed in T-4221 itself -- add src/frob/gates/_inv.py to both via-lists once free.

## Drop reason
- 2026-09-19: duplicate promotion of the same draft (T-draft-9a4eb7be) by successive lands; T-4605 carries the superset body (absorbed by T-4605)
