---
id: T-4221
title: 'frob:invariant time-stable kind: discharge a wall-clock-dependent predicate
  by re-running its bound test with the clock advanced across a declared horizon'
state: in-progress
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
- tests/unit/graph/test_dsl.py
- tests/gates_suite/test_invariant.py
- docs/modules/gate-time-stable-invariant.md
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
    doc go in a new standalone doc file instead, folded into gates.md later via T-draft-9a4eb7be
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer F-362/H4-1 (T-4166): a check comparing a committed-artifact-derived value against wall-clock time passes today and fails tomorrow; every existing test supplies now and the artifact's timestamp from the same instant, so the whole class of 'passes today, fails tomorrow' is invisible. Add an invariant kind (e.g. frob:invariant time-stable horizon="180d") discharged by re-running the bound test with the clock advanced across the declared horizon; failing that, a narrower lint flagging a comparison between a committed-artifact value and new Date()/now() with no test that varies now. High value: ask what in frob's OWN tree is a function of wall-clock time and tested only at a single instant. Fixture-testable: YES, with a synthetic time-dependent function in frob's own tree.