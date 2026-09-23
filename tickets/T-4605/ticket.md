---
id: T-4605
title: Wire CONFIGPATH001/ROUTE001 gates into the gate registry and docs/modules/gates.md
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.540.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
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
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.540.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
body_changes:
- mode: append
  reason: T-4221 hit the same design/frob.strata lease conflict as the docs/modules/gates.md
    one this ticket already tracks; recording the specific via-list fix needed
  actor: logan
  at: '2026-09-19'
  old_length: 1018
  new_length: 1639
- mode: append
  reason: T-3962 hit the same docs/modules/gates.md lease conflict (T-4111), plus
    _waive.py (T-4212) and check-coverage.yaml (T-4112) lease conflicts for the new
    INV011 rule id's own registration
  actor: logan
  at: '2026-09-19'
  old_length: 1639
  new_length: 3412
- mode: append
  reason: T-3961 implementation (T-4622) hit the identical _sys.py/_waive.py lease-blocked
    wiring gap this ticket already tracks for INV011/CONFIGPATH001/ROUTE001
  actor: logan
  at: '2026-09-19'
  old_length: 3412
  new_length: 4685
- mode: append
  reason: T-4633 hit the same docs/modules/gates.md lease conflict (T-4111) for its
    own SYS111 auto-accept doc addition
  actor: logan
  at: '2026-09-19'
  old_length: 4685
  new_length: 5468
- mode: append
  reason: T-3964 implementation hit the identical _sys.py/_waive.py lease-blocked
    wiring gap this ticket already tracks for SYS116/SYS117/INV011/CONFIGPATH001/ROUTE001
  actor: logan
  at: '2026-09-19'
  old_length: 5438
  new_length: 6420
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4114 (config_path_default_gate/CONFIGPATH001) and T-4115 (route_response_model_gate/ROUTE001) both add a standalone, fully-tested gate module + docs page, but neither is wired into src/frob/gates/__init__.py's gate dispatch table/_KNOWN_GATE_RULES, and neither rule appears in docs/modules/gates.md's own rule table or the file's frob:enumerates directive -- both were out of scope for T-4114/T-4115 (declared scope is just the gate module + its test file), and docs/modules/gates.md itself was leased by T-4111 for the whole duration of both tickets' work, so its own rule-table row could not be added there either. Wire both gates into the dispatch table (gate name config_path_defaults / route_response_model, matching each module's own tests) and add their rule-table rows + frob:enumerates entries to docs/modules/gates.md once free, or fold the standalone docs pages (docs/modules/gate-config-path-defaults.md, docs/modules/gate-route-response-model.md) into it and update each gate's frob:doc anchor to match.

Also fold in: src/frob/gates/_inv.py's time_stable_gate/_spawn_time_stable_test/time_stable_offset_s (T-4221, INV010) read os.environ and spawn a pytest subprocess -- SYS100/SELFAUDIT fires on both (env.read, exec) because design/frob.strata's gates component env.read/exec via-lists (currently keyed on src/frob/gates/_bug_repro.py only) do not yet name _inv.py. design/frob.strata was leased by T-4111 for T-4221's entire duration (the same lease conflict T-4221's own Done report names for docs/modules/gates.md), so this could not be fixed in T-4221 itself -- add src/frob/gates/_inv.py to both via-lists once free.


Also fold in: T-3962 (INV011 forbidden-constant reachability) added the rule's docs page as a standalone file, docs/modules/gate-inv011-forbidden-constant-reachability.md, and pointed src/frob/gates/_design_invariants.py's frob:doc directives at it -- docs/modules/gates.md was leased by T-4111 for T-3962's entire duration (the same lease conflict this ticket's body already tracks for T-4114/T-4115/T-4221). Once docs/modules/gates.md is free: fold the standalone page's "INV011 (forbidden-constant reachability)" section into it (next to the existing "INV007 and INV008 (T-0757)" section), add an INV011 row to the rule table and to the file's frob:enumerates members list, retarget src/frob/gates/_design_invariants.py's frob:doc anchors from the standalone file onto docs/modules/gates.md#inv011-forbidden-constant-reachability-t-3962 (or whatever heading the fold-in lands under), and delete the now-redundant standalone page.

Also: T-3962 registers the new gate rule id INV011 (frob.gates._design_invariants.inv011_violations, wired into src/frob/gates/__init__.py's "invariant" thread job) but src/frob/gates/_waive.py -- where INV011 needs a _KNOWN_GATE_RULES entry (the same UnregisteredGateRuleConstructed land-time refusal T-2388/T-2441 hit for PORT001/GATESSCHEMA001/etc) and docs/design/registry/check-coverage.yaml needs a CHK-GATE-INV011 entry (frob.gates._design_invariants.inv011_violations already carries a frob:enforces CHK-GATE-INV011 directive expecting it) -- were both leased by other in-progress tickets (T-4212 and T-4112 respectively) for T-3962's entire duration. Register "INV011" in _waive.py's _KNOWN_GATE_RULES frozenset (T-2441 courtesy-registration pattern) and add a CHK-GATE-INV011 row to check-coverage.yaml once each file is free.

Also fold in: T-4622 (T-3961 provenance/trust-as-identity implementation) added src/frob/gates/_sys_provenance.py with two new rule ids (SYS116 undeclared provenance, SYS117 trust_identity without carries -- renumbered from an initial SYS114/SYS115 pick that collided with T-4113's outbound-destination/foreign-flow-rate rules) but could not wire evaluate_provenance into src/frob/gates/_sys.py::sys_gate's dispatch, nor register SYS116/SYS117 in src/frob/gates/_waive.py's _KNOWN_GATE_RULES frozenset -- both files were leased by in-progress T-4212 for the ticket's entire duration (the same _waive.py lease conflict this ticket's own T-3962 fold-in item above already names for INV011). Once _sys.py and _waive.py are free: wire evaluate_provenance(model) into sys_gate's dispatch (mirrors how SELFAUDIT001/other SYS1xx families are folded in), register SYS116 and SYS117 in _KNOWN_GATE_RULES (T-2441 courtesy-registration pattern), and add their rows to docs/modules/gates.md's rule table + frob:enumerates members list (the standalone docs/strata/provenance-trust-identity.md page this ticket wrote can then fold into docs/modules/gates.md the same way T-3962's INV011 page is asked to above, or stay standalone with a frob:doc retarget -- reviewer's call).

Also fold in: T-4633 (SYS111 ratchet-ceiling land race, measured T-4508 x2, T-4111) added a standalone docs page, docs/modules/gate-sys111-ratchet-auto-accept.md, documenting the new `_branch_own_via_growth`/`FROB_LAND_TICKET_ENV` branch-own-via-addition auto-accept in `frob.strata._effects.capability_ratchet_violations` -- docs/modules/gates.md was leased by T-4111 for T-4633's entire duration (the same lease conflict this ticket's body already tracks for T-4114/T-4115/T-4221/T-3962/T-3961). Once docs/modules/gates.md is free: fold the standalone page's content into it next to the existing SYS111 discussion (the fix_sys111_capability_ratchet_sync T-2001 paragraphs and the SYS111 rule-catalog table row), then delete the now-redundant standalone page.


Also fold in: T-3964 (dataset construct: parent_store=/append_only node attrs) added src/frob/strata/_dataset.py with a new SYS118 structural check (check_dangling_parent_store: a parent_store= attr naming a node id that does not exist in the model). Kept gate-agnostic on purpose (returns plain finding strings, not a Violation model) mirroring T-3961's own _sys_provenance.py posture -- not yet wired into any frob.gates dispatch table or _KNOWN_GATE_RULES. Once a wiring pass covers this fold-in ticket's other pending SYS116/SYS117 item: also wrap check_dangling_parent_store's findings as Violations, dispatch it from wherever the reviewer wires SYS116/SYS117, register SYS118 in _KNOWN_GATE_RULES, and add its row to docs/modules/gates.md's rule table + frob:enumerates members list (the standalone docs/strata/dataset-construct.md page this ticket wrote can then fold into docs/modules/gates.md the same way, or stay standalone with a frob:doc retarget -- reviewer's call).