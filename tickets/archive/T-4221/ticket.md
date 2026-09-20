---
id: T-4221
title: 'frob:invariant time-stable kind: discharge a wall-clock-dependent predicate
  by re-running its bound test with the clock advanced across a declared horizon'
state: done
kind: feature
origin: agent
created: '2026-09-07'
priority: high
parent: T-4166
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_inv.py
- src/frob/graph/dsl.py
- tests/gates_suite/test_invariant.py
- docs/modules/gate-time-stable-invariant.md
- tests/unit/graph/test_dsl_invariant_property.py
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/graph/dsl.py
  reason: the frob:invariant kind=/horizon= attribute grammar (T-4221's own 'grammar
    in the token parser') lives in frob.graph.dsl's _attrs_verb_error_invariant, the
    same validator that already shapes no_import=/establishes= for this verb; the
    runner itself and its tests stay in src/frob/gates/_inv.py per declared scope,
    but the grammar cannot be added without touching its one existing home
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/unit/graph/test_dsl.py
  reason: the frob:invariant kind=/horizon= attribute grammar (T-4221's own 'grammar
    in the token parser') lives in frob.graph.dsl's _attrs_verb_error_invariant, the
    same validator that already shapes no_import=/establishes= for this verb; the
    runner itself and its tests stay in src/frob/gates/_inv.py per declared scope,
    but the grammar cannot be added without touching its one existing home
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/gates_suite/test_invariant.py
  reason: the frob:invariant kind=/horizon= attribute grammar (T-4221's own 'grammar
    in the token parser') lives in frob.graph.dsl's _attrs_verb_error_invariant, the
    same validator that already shapes no_import=/establishes= for this verb; the
    runner itself and its tests stay in src/frob/gates/_inv.py per declared scope,
    but the grammar cannot be added without touching its one existing home
  actor: logan
  at: '2026-09-19'
- op: add
  glob: invariants/
  reason: the frob:invariant kind=/horizon= attribute grammar (T-4221's own 'grammar
    in the token parser') lives in frob.graph.dsl's _attrs_verb_error_invariant, the
    same validator that already shapes no_import=/establishes= for this verb; the
    runner itself and its tests stay in src/frob/gates/_inv.py per declared scope,
    but the grammar cannot be added without touching its one existing home
  actor: logan
  at: '2026-09-19'
- op: remove
  glob: invariants/
  reason: over-broad glob per scope-add warning; not needed -- the fixture is a synthetic
    time-dependent function+test in the gate's own test file, not a real invariants/*.md
    entry
  actor: logan
  at: '2026-09-19'
- op: add
  glob: docs/modules/gate-time-stable-invariant.md
  reason: docs/modules/gates.md is leased by T-4111 (same conflict as T-4114/T-4115
    this sprint); INV010's frob:doc anchor and the frob:invariant kind=/horizon= grammar
    doc go in a new standalone doc file instead, folded into gates.md later via T-4602
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/unit/graph/test_dsl_invariant_property.py
  reason: this repo's existing home for frob:invariant obligation-attr grammar tests
    (no_import=/establishes=, T-0757); kind=/horizon= belongs alongside them, not
    in tests/unit/graph/test_dsl.py which carries no invariant-attr cases at all
  actor: logan
  at: '2026-09-19'
- op: remove
  glob: tests/unit/graph/test_dsl.py
  reason: not needed -- frob:invariant attr-grammar tests belong in tests/unit/graph/test_dsl_invariant_property.py
    instead (added above)
  actor: logan
  at: '2026-09-19'
- op: add
  glob: design/frob.strata
  reason: T-4111 lease released
  actor: logan
  at: '2026-09-19'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: T-4111 lease released
  actor: logan
  at: '2026-09-19'
body_changes:
- mode: append
  reason: condense narrative into cited ticket body per T-4691 C5 sweep
  actor: logan
  at: '2026-09-19'
  old_length: 787
  new_length: 1986
evidence:
- tests/gates_suite/test_invariant.py::TestTimeStableGate::test_fails_once_clock_advances_past_horizon
- tests/gates_suite/test_invariant.py::TestTimeStableGate::test_stays_quiet_when_still_passing_at_horizon
- tests/gates_suite/test_invariant.py::TestTimeStableGate::test_baseline_failure_is_skipped_not_double_reported
- tests/gates_suite/test_invariant.py::TestTimeStableGate::test_no_time_stable_anchor_is_silent
- tests/unit/graph/test_dsl_invariant_property.py::TestTimeStableAttrs::test_valid_kind_and_horizon_always_parses_together
- tests/unit/graph/test_dsl_invariant_property.py::TestTimeStableAttrs::test_kind_with_no_horizon_is_malformed
- tests/unit/graph/test_dsl_invariant_property.py::TestTimeStableAttrs::test_horizon_with_no_kind_is_malformed
- tests/unit/graph/test_dsl_invariant_property.py::TestTimeStableAttrs::test_unknown_kind_is_malformed
- tests/unit/graph/test_dsl_invariant_property.py::TestTimeStableAttrs::test_malformed_horizon_is_rejected
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer F-362/H4-1 (T-4166): a check comparing a committed-artifact-derived value against wall-clock time passes today and fails tomorrow; every existing test supplies now and the artifact's timestamp from the same instant, so the whole class of 'passes today, fails tomorrow' is invisible. Add an invariant kind (e.g. frob:invariant time-stable horizon="180d") discharged by re-running the bound test with the clock advanced across the declared horizon; failing that, a narrower lint flagging a comparison between a committed-artifact value and new Date()/now() with no test that varies now. High value: ask what in frob's OWN tree is a function of wall-clock time and tested only at a single instant. Fixture-testable: YES, with a synthetic time-dependent function in frob's own tree.

<!-- narrative-moved:src/frob/graph/dsl.py:246:T-4221 -->
: `frob:invariant`'s optional `kind="time-stable" horizon="<N><unit>"`
: obligation attr pair (T-4221, F-362/H4-1): a check comparing a
: committed-artifact-derived value against wall-clock time passes today
: and fails tomorrow, and every existing test supplies "now" and the
: artifact's timestamp from the SAME instant, so that whole class is
: invisible until it actually rots. `kind="time-stable"` declares the
: invariant's bound test must still pass with the clock advanced across
: `horizon`; `frob.gates._inv.time_stable_gate` is the runner that
: actually re-executes the bound test under an advanced-clock env var
: and reports a finding if it fails at any sampled point. The two attrs
: are required TOGETHER: `kind=` with no `horizon=` has no horizon to
: advance across, and `horizon=` with no `kind=` (or a different kind)
: has no declared discharge mechanism to apply it to. Only one `kind`
: value exists so far (`"time-stable"`) -- `_INVARIANT_KIND_VALUES` is a
: closed set, not a free-text field, so a typo'd kind fails loudly at
: parse time instead of silently never being picked up by any runner.
frob:ticket T-4221