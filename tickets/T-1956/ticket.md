---
id: T-1956
title: Wire find_unregistered_rule_ids into the T-0756 acceptance preflight (or a
  dedicated gate), not just a test
state: queued
kind: feature
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_new_gate_rule_acceptance.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1937 built the broad, repo-wide completeness net (`frob.gates._rule_id_scan.scan_candidate_rule_id_literals`/`find_unregistered_rule_ids`) and wired it into a drift-lock TEST (`tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_real_repo_registry_is_complete`), which runs on every normal test/check pass -- so a new unregistered rule id anywhere under src/ already fails loud automatically today, satisfying the ticket's core "automatic over documenting the caveat harder" ask.

What is NOT done yet (T-1937's own declared scope was `src/frob/gates/_rule_id_scan.py` plus `gates/__init__.py`/`gates/_waive.py`, not `frob.tickets._new_gate_rule_acceptance`): `find_unregistered_rule_ids` has no production caller outside its own tests (WIRE001). The natural wiring is threading this broader, shape-agnostic scan into `frob.tickets._new_gate_rule_acceptance`'s own T-0756 acceptance preflight (or a new dedicated gate rule) so a NEW unregistered id is refused at close/land time directly, not only caught retroactively the next time the test suite runs. That module is a different ticket's scope (out of T-1937's own declared files) -- wiring it is this follow-up's job.
