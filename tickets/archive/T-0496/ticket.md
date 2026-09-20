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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_facts.py
- tests/unit/strata/test_facts.py
- tests/unit/strata/test_claims.py
- tests/unit/strata/litmus/utility_hub_hardened.strata
- tests/unit/strata/litmus/utility_hub_vuln.strata
- tests/unit/strata/test_litmus_utility_hub.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
body_changes:
- mode: append
  reason: condense noflow/utility-exclusion narrative into T-0496 body
  actor: logan
  at: '2026-09-19'
  old_length: 872
  new_length: 2378
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
anchor: false
anchor_reason: null
land_commit: null
---
docs/audits/strata.md G5 (MEDIUM), from T-0401. _facts.py:63,160: any flow carrying the surface attr utility (or synthetic krb_no_transit) is a TERMINAL edge -- taint does not chain past it -- honored on the security noflow side too (_eval_noflow uses the same reachable). A real exfiltration path transiting a hub edge marked utility is invisible to noflow, so any THREAT003 discharge built on it is vacuous; the marker is author-controlled with no compensating check. Repro: flow log_hub{src=secret_store,dst=logger,utility} then flow leak{src=logger,dst=foreign_sink}: noflow(secret_store,foreign_sink) PROVES despite the two-hop leak. Fix direction: forbid utility on flows whose payload label is above a floor, or exclude utility termination when evaluating confidentiality noflow specifically (keep it only for capacity/availability closures where T-0226 needed it).

<!-- narrative-moved:src/frob/strata/_facts.py:91:T-0496 -->
: T-0496 (docs/audits/strata.md G5): the non-transitive attrs honored when
: `through_barriers=False` -- the confidentiality `noflow` closure
: (`_claims.py::_first_noflow_witness`, the ONLY caller that omits
: `through_barriers`). Deliberately EXCLUDES `utility`: T-0226 added
: `utility`-as-terminal specifically so an unrelated hub edge (e.g. a
: logging import) would not falsely refute a legitimate `noflow` claim --
: but this made the SAME marker a real, author-controlled way to hide a
: genuine downstream leak from the confidentiality check (repro: `flow
: log_hub{src=secret_store, dst=logger, utility}` then `flow leak{src=
: logger, dst=foreign_sink}` -- `noflow(secret_store, foreign_sink)`
: PROVED despite the two-hop leak, since `logger` was reached only via the
: terminal `utility` edge and so was never enqueued to explore its own
: `leak` edge). Per charter law 2 (deny-by-default): a false REFUTED that
: forces a human to add a real `Boundary`/discharge is an acceptable cost;
: a false PROVED that hides a real exfiltration path is not. `krb_no_
: transit` is NOT similarly excluded here -- no caller currently reaches
: it through this path (`_krb.py`'s synthesized flows feed the `through_
: barriers=True` movement/reach closures, `_krb_movement.py:388`), and
: T-0282's own fix was never claimed for confidentiality noflow the way
: T-0226's `utility` fix was, so there is no known equivalent gap to close
: for it.