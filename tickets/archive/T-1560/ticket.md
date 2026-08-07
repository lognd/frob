---
id: T-1560
title: 'post-T-1555 error burn: 16 orphaned WIRE001 waivers, 2 renamed-evidence COV003s,
  2 ARCH001 splits, PERF001, 3 PII012'
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets.py::TestV2StateTransitions::test_transitions_mined_oldest_first
- tests/test_tickets.py::TestV2StateTransitions::test_no_history_returns_empty_tuple
- tests/test_tickets.py::TestV2StateTransitions::test_byte_similar_sibling_ticket_does_not_drop_transitions
- tests/test_ticket_land.py::TestLandPlan::test_tick_gate_dirty_unwinds_finalize_but_keeps_the_durable_merge
designated_repro_test: null
acceptance:
- text: 'GIVEN a full unscoped frob check on main THEN gate errors are 0: the 16 WIRE002
    stale waivers rebind to the open successor ticket, T-1269/T-1495 evidence ids
    rebind to the renamed tests via evidence --replace, _land_plan_locked and v2_state_transitions
    drop under the ARCH001 60-line threshold via genuine helper extraction, _v2_path_lineage
    membership test uses a set, and the 3 PII012 test-token suggestions carry reasoned
    waivers'
  evidence:
  - tests/test_tickets.py::TestV2StateTransitions::test_transitions_mined_oldest_first
  - tests/test_tickets.py::TestV2StateTransitions::test_no_history_returns_empty_tuple
  - tests/test_tickets.py::TestV2StateTransitions::test_byte_similar_sibling_ticket_does_not_drop_transitions
  - tests/test_ticket_land.py::TestLandPlan::test_tick_gate_dirty_unwinds_finalize_but_keeps_the_durable_merge
threat: null
component: null
---
Post-T-1555 re-measure found 26 errors. 2 (PRE001/SCOPE001) were an uncommitted archive artifact, fixed. The rest: 15 waivers name done T-1490 + 1 names done T-1488 (WIRE002); T-1269 evidence test_tick_gate_dirty_unwinds_everything renamed to test_tick_gate_dirty_unwinds_finalize_but_keeps_the_durable_merge, T-1495 evidence test_no_foreign_commit_unwinds_cleanly_as_before renamed to test_no_foreign_commit_unwinds_to_the_merge_commit_not_pre_merge (COV003); ARCH001 on src/frob/tickets/_land.py::_land_plan_locked (67) and src/frob/tickets/_store.py::v2_state_transitions (77); PERF001 at _store.py:790 (list membership in loop); PII012 x3 in tests/unit/test_dup_legacy_cpp.py (lexer-token identifiers, not credentials).