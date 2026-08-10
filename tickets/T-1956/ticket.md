---
id: T-1956
title: Wire find_unregistered_rule_ids into the T-0756 acceptance preflight (or a
  dedicated gate), not just a test
state: in-progress
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
- src/frob/tickets/_evidence.py
- tests/test_tickets_new_gate_rule_acceptance.py
- src/frob/tickets/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: wire find_unregistered_rule_ids into the T-0756 preflight caller in _evidence.py
    and its own unit tests, T-1956
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_tickets_new_gate_rule_acceptance.py
  reason: wire find_unregistered_rule_ids into the T-0756 preflight caller in _evidence.py
    and its own unit tests, T-1956
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/tickets/_models.py
  reason: new TicketError variant for the T-1956 unregistered-rule-id close refusal
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_tickets_new_gate_rule_acceptance.py::TestUnregisteredRuleIdsInScope::test_empty_when_nothing_unregistered_in_scope
- tests/test_tickets_new_gate_rule_acceptance.py::TestUnregisteredRuleIdsInScope::test_reports_an_unregistered_id_whose_file_is_in_scope
- tests/test_tickets_new_gate_rule_acceptance.py::TestUnregisteredRuleIdsInScope::test_excludes_an_unregistered_id_outside_scope
- tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnregisteredGateRule::test_close_refused_when_scope_constructs_an_unregistered_rule_id
- tests/test_tickets_new_gate_rule_acceptance.py::TestTransitionRefusesOnUnregisteredGateRule::test_close_allowed_once_the_id_is_registered
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1937 built the broad, repo-wide completeness net (`frob.gates._rule_id_scan.scan_candidate_rule_id_literals`/`find_unregistered_rule_ids`) and wired it into a drift-lock TEST (`tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_real_repo_registry_is_complete`), which runs on every normal test/check pass -- so a new unregistered rule id anywhere under src/ already fails loud automatically today, satisfying the ticket's core "automatic over documenting the caveat harder" ask.

What is NOT done yet (T-1937's own declared scope was `src/frob/gates/_rule_id_scan.py` plus `gates/__init__.py`/`gates/_waive.py`, not `frob.tickets._new_gate_rule_acceptance`): `find_unregistered_rule_ids` has no production caller outside its own tests (WIRE001). The natural wiring is threading this broader, shape-agnostic scan into `frob.tickets._new_gate_rule_acceptance`'s own T-0756 acceptance preflight (or a new dedicated gate rule) so a NEW unregistered id is refused at close/land time directly, not only caught retroactively the next time the test suite runs. That module is a different ticket's scope (out of T-1937's own declared files) -- wiring it is this follow-up's job.
