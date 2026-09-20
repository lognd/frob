---
id: T-0172
title: managed marker for config-only infra nodes promised in surface.md but unimplemented
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- strata-core/src/parse.rs
- src/frob/strata/**
- docs/strata/surface.md
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense mitigation-kind-skip algorithm explanation into T-0501 body, doc
    lives in docs/strata/threat.md
  actor: logan
  at: '2026-09-19'
  old_length: 531
  new_length: 1751
evidence:
- tests/unit/strata/test_managed.py::TestManagedGrammar::test_node_managed_marker_elaborates_to_attr
- tests/unit/strata/test_managed.py::TestManagedGrammar::test_node_without_managed_is_not_managed
- tests/unit/strata/test_managed.py::TestManagedGrammar::test_store_managed_marker_elaborates_to_attr
- tests/unit/strata/test_managed.py::TestManagedDischargeFromParsedSurfaceSource::test_non_managed_node_with_mismatched_boundary_still_fires
- tests/unit/strata/test_managed.py::TestManagedDischargeFromParsedSurfaceSource::test_managed_node_with_same_shape_discharges
- tests/unit/strata/test_managed.py::TestManagedDischargeFromParsedSurfaceSource::test_managed_node_still_requires_a_discharging_claim
- tests/unit/strata/test_managed.py::TestManagedTier2ImportConformance::test_managed_node_owned_files_produce_no_violation
- tests/unit/strata/test_managed.py::TestManagedTier2ImportConformance::test_non_managed_node_with_same_shape_still_violates
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
logand.app pilot: docs/strata/surface.md names a planned managed marker for pure-config infrastructure nodes (e.g. a Caddyfile-configured edge) but the grammar does not implement it, so config-only nodes cannot be honestly modeled without fake code bindings. Same doc-grammar drift class as T-0166. Either implement managed (parse -> elaborate -> conformance treats the node as having no scannable code by declaration, with the audit reporting it as managed rather than unmodeled) or correct surface.md; doc and grammar must agree.

<!-- narrative-moved:src/frob/strata/_threat_discharge.py:519:T-0172 -->
The mitigation-kind check (`_mitigation_is_chokepoint`) is skipped for
an `assumed` claim, exactly like the REFUTED check above it: an assumed
claim is a human-owned TCB entry never run through the closure at all
(`_claims.py::evaluate_claims` short-circuits assumed claims to the
`ASSUMED` verdict before touching `_eval_noflow`), so there is no
closure-derived proof to inspect for boundary kind -- the owner/review
gate a few lines up is the only accountability an assume gets, same as
every other claim form in this module.

It is ALSO skipped when `node_id` names a `managed` node (T-0172,
`_code_binding.py::is_managed`): a managed node is external, pure-config
infrastructure declared to have no scannable code, so there is no
tier-2 code-modeled boundary for `_mitigation_is_chokepoint` to inspect
either -- "no tier-2 conformance; obligations shift to config evidence
or assumes" (docs/strata/surface.md#key-construct-semantics). The claim
still has to exist, prove a chokepoint shape (`_discharges_as_chokepoint`
above), and clear the catalog rung -- only the boundary-KIND proof is
exempted, same as an assume gets.
frob:ticket T-0501