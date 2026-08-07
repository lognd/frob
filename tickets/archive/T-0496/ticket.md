---
id: T-0496
title: 'strata audit G5: utility/krb_no_transit flow marker silently defeats confidentiality
  NoFlow'
state: done
kind: security
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_facts.py
- tests/unit/strata/test_facts.py
- tests/unit/strata/test_claims.py
- tests/unit/strata/litmus/utility_hub_hardened.strata
- tests/unit/strata/litmus/utility_hub_vuln.strata
- tests/unit/strata/test_litmus_utility_hub.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_facts.py
  reason: existing test_utility_attr_stops_chaining_past_that_hop locks in the vulnerable
    behavior for the through_barriers=False (confidentiality noflow) path; must flip
    alongside the fix, plus a claims-level litmus test for the noflow discharge itself
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/strata/test_claims.py
  reason: existing test_utility_attr_stops_chaining_past_that_hop locks in the vulnerable
    behavior for the through_barriers=False (confidentiality noflow) path; must flip
    alongside the fix, plus a claims-level litmus test for the noflow discharge itself
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/strata/litmus/utility_hub_hardened.strata
  reason: T-0226's own hardened litmus (utility_hub_hardened.strata) IS the exact
    G5 vulnerability shape -- its noflow claim genuinely has a real path to its target
    through the marked hub, so it must now correctly REFUTE instead of falsely PROVE;
    fixture+test need correcting, not just the unit-level tests
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/strata/litmus/utility_hub_vuln.strata
  reason: T-0226's own hardened litmus (utility_hub_hardened.strata) IS the exact
    G5 vulnerability shape -- its noflow claim genuinely has a real path to its target
    through the marked hub, so it must now correctly REFUTE instead of falsely PROVE;
    fixture+test need correcting, not just the unit-level tests
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/strata/test_litmus_utility_hub.py
  reason: T-0226's own hardened litmus (utility_hub_hardened.strata) IS the exact
    G5 vulnerability shape -- its noflow claim genuinely has a real path to its target
    through the marked hub, so it must now correctly REFUTE instead of falsely PROVE;
    fixture+test need correcting, not just the unit-level tests
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/strata/test_facts.py::TestClosure::test_utility_attr_does_not_stop_chaining_for_confidentiality_noflow
- tests/unit/strata/test_facts.py::TestClosure::test_krb_no_transit_still_terminal_for_confidentiality_noflow
- tests/unit/strata/test_facts.py::TestClosure::test_utility_attr_stops_chaining_past_that_hop
- tests/unit/strata/test_claims.py::TestNoFlow::test_real_leak_through_a_utility_hub_still_refutes
- tests/unit/strata/test_claims.py::TestNoFlow::test_utility_hub_with_no_further_edges_still_discharges
- tests/unit/strata/test_litmus_utility_hub.py::TestUtilityHubHardenedLitmus::test_marked_utility_hub_edge_lets_the_noflow_claim_prove
designated_repro_test: null
threat: null
component: null
---
docs/audits/strata.md G5 (MEDIUM), from T-0401. _facts.py:63,160: any flow carrying the surface attr utility (or synthetic krb_no_transit) is a TERMINAL edge -- taint does not chain past it -- honored on the security noflow side too (_eval_noflow uses the same reachable). A real exfiltration path transiting a hub edge marked utility is invisible to noflow, so any THREAT003 discharge built on it is vacuous; the marker is author-controlled with no compensating check. Repro: flow log_hub{src=secret_store,dst=logger,utility} then flow leak{src=logger,dst=foreign_sink}: noflow(secret_store,foreign_sink) PROVES despite the two-hop leak. Fix direction: forbid utility on flows whose payload label is above a floor, or exclude utility termination when evaluating confidentiality noflow specifically (keep it only for capacity/availability closures where T-0226 needed it).