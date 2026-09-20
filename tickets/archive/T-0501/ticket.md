---
id: T-0501
title: 'strata audit G2/G7: vacuous NoFlow discharge when foreign->sink flow is un-modeled
  or no foreign-trust node exists'
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
- src/frob/strata/_threat.py
- src/frob/strata/_claims.py
- tests/unit/strata/test_threat.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_threat.py
  reason: T-0501's litmus/regression tests for the G2/G7 flow-completeness fix live
    here
  actor: logan
  at: '2026-07-22'
body_changes:
- mode: append
  reason: condense chokepoint-quantifier algorithm explanation into T-0501 body, doc
    lives in docs/strata/threat.md
  actor: logan
  at: '2026-09-19'
  old_length: 1187
  new_length: 4713
evidence:
- tests/unit/strata/test_threat.py::TestFlowCompletenessGap::test_foreign_node_present_but_no_flow_to_sink_fails_closed
- tests/unit/strata/test_threat.py::TestFlowCompletenessGap::test_foreign_node_present_and_connected_elsewhere_still_fails_closed
- tests/unit/strata/test_threat.py::TestFlowCompletenessGap::test_no_foreign_node_anywhere_still_discharges_by_absence
- tests/unit/strata/test_threat.py::TestDischargeChokepointShape::test_noflow_from_a_specific_foreign_trust_node_discharges
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
docs/audits/strata.md G2+G7 (HIGH/MEDIUM), from T-0401. _mitigation_is_chokepoint's first branch (_threat.py:1196) returns True when NoFlow holds with EVERY boundary removed -- i.e. the sink is simply unreachable from foreign in the model, so an incomplete/attacker-authored .strata discharges a real capability with NO mitigation modeled at all (G2). Same root cause as G7: _discharges_as_chokepoint's src=foreign expansion (_claims.py _expand) yields an empty source set when the model declares no foreign-trust node at all, so NoFlow proves vacuously (nothing to walk from) and every obligation on that model discharges with no adversary present. Fix direction: require at least one modeled path from a foreign source to the firing node (and at least one foreign-trust node in the model) before accepting the vacuous short-circuit as a discharge; otherwise emit a distinct 'obligation fires but sink unreachable / no adversary modeled -- model likely incomplete' diagnostic instead of silent PROVED. High-risk core-engine change (this family has the highest REJECT rate in repo history) -- build the counterexample litmus FIRST, confirm it currently discharges vacuously, THEN harden.

<!-- narrative-moved:src/frob/strata/_threat_discharge.py:383:T-0501 -->
Whether the boundaries carrying `entry`'s EXACT required mitigation
(`_matching_boundary_ids`) are, by themselves, sufficient to make
`claim`'s `NoFlow` hold -- i.e. the catalog-correct mitigation is a
genuine chokepoint, not merely one boundary among several (of possibly
unrelated kinds) that happen to also block a path (docs/strata/
threat.md#phasing item C, review round 2). This comment (not the
docstring) carries the explanation so frob-arch's long-function line
count reflects the code, not the essay (same pattern as gates/
__init__.py's `_match_waiver`).

Vacuous-path short-circuit FIRST: if `claim` already holds with EVERY
boundary removed (`_restricted_to_boundaries(model, frozenset(),
claim)`), no path from the claim's source to its sink exists in the
closure AT ALL -- the `NoFlow` is proved by absence of a flow, not by
any boundary. T-0501: the caller (`_check_discharge_mitigation_kind`)
now runs `_flow_completeness_gap` BEFORE this function and rejects the
G2 mixed-model case (a foreign node exists elsewhere but this
obligation's own flow was never modeled) with a distinct violation, so
by the time this branch is reached the vacuous case is EITHER the
sound T-0223 library-mode discharge (no foreign-trust node anywhere in
the model) OR a model with genuinely no flows/boundaries declared at
all (the pre-T-0113 fixtures this branch was written to keep passing) --
both legitimately proved by absence, so accepting them here is correct,
not the reviewer-flagged gap.

Otherwise, re-evaluates the SAME claim (`_claim_holds`, so the SAME
`_eval_noflow`/`reachable` closure walk `_discharges_as_chokepoint`'s
round-1 shape check already leans on) over a model copy with every
OTHER boundary removed (`_restricted_to_boundaries`) -- no new closure
primitive, no new `strata_core` call. G1 (docs/audits/strata.md):
`_matching_boundary_ids` additionally requires each candidate boundary's
`obligations` to resolve to a real in-model `Claim.id`
(`_obligations_resolve`) -- a matching `predicate` string alone is no
longer sufficient; a chokepoint boundary with no evidence ref (or a
dangling one) is excluded from `matching` and so cannot satisfy this
check, even if its bare predicate name happens to equal
`entry.mitigation`.

Quantifier: this is "the matching boundaries alone cut the closure the
SAME `NoFlow` walk already computes" -- sound (a PROVED result here
means the matching boundaries really do interpose on every path
`reachable` traverses, since removing MORE boundaries can only ADD
reachability, never remove it) but not maximal: a path blocked ONLY by
a non-matching boundary (with no matching boundary anywhere on it) is
invisible to per-path attribution, since `FactBase.reachable` reports
reachability, not which specific boundary blocked which specific path
(docs/strata/kernel.md#fact-base). If EVERY path happens to carry a
matching boundary, this proves True exactly; if only SOME paths do
while others are saved solely by a non-matching boundary, this proves
False (the restricted-model NoFlow is REFUTED, since removing the
non-matching boundary that had been covering that path reopens it) --
which is the conservative, deny-by-default direction (charter law 2).
No unsound acceptance is possible; the disclosed gap is precision, not
soundness: a model needing a per-path (rather than per-model)
mitigation-kind proof is out of v0's scope, noted here and in
threat.md rather than silently assumed away.