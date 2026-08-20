---
id: T-2700
title: Wire import_graph_gap_disclosure into frob.cycle.graph's real DependencyGraph/find_cycles
  output
state: done
kind: feature
origin: human
created: '2026-08-19'
priority: medium
blocked_by:
- T-2683
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/cycle/graph.py
- docs/modules/graph.md
- tests/test_graph.py
- docs/commands/cycle.md
- src/frob/cycle/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_graph.py
  reason: T-2700 own positive/negative control tests for DependencyGraph.degraded_languages
    / find_cycles wiring
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_graph.py
  reason: T-2700 own positive/negative control tests for DependencyGraph.degraded_languages
    / find_cycles wiring
  actor: logan
  at: '2026-08-20'
- op: add
  glob: docs/commands/cycle.md
  reason: 'AFFECT001: DependencyGraph/find_cycles affects()-closure includes this
    doc''s public-api anchor; T-2700 changes both symbols and must update it'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/cycle/__init__.py
  reason: 'land refused CloseFailed/LiveTrackerCited: the T-2683 WIRE001 waiver on
    import_graph_gap_disclosure cited follow_up=T-2700 as its open tracker; T-2700
    now wires it for real, updating that waiver in the same change per land''s own
    guidance'
  actor: logan
  at: '2026-08-20'
evidence:
- tests/test_graph.py::TestDependencyGraphDegradedLanguages::test_clean_tree_has_no_degraded_languages_and_no_log_noise
- tests/test_graph.py::TestDependencyGraphDegradedLanguages::test_known_gap_is_disclosed_on_degraded_languages_and_logged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 0f7517207b98a24ed7adda2e04e875316619fa5a
---
T-2683 built the self-disclosure primitive (frob.graph.callgraph.
capability_gap_disclosure) and wired it into build_call_graph's own
CallGraph.degraded_languages output, plus exposed frob.cycle.
import_graph_gap_disclosure as a thin pre-bound wrapper -- but T-2683's
own declared scope was src/frob/graph/callgraph.py, src/frob/cycle/
__init__.py (the re-export shim), and two docs -- NOT src/frob/cycle/
graph.py, where DependencyGraph/find_cycles's own real output type
lives. That means frob.cycle.import_graph_gap_disclosure exists and is
tested, but find_cycles's own return value does not yet self-disclose
an import_graph gap the way CallGraph.degraded_languages does.

Scope: wire import_graph_gap_disclosure into DependencyGraph (or
find_cycles's own return, whichever shape fits without breaking
existing callers) the same way T-2683 wired capability_gap_disclosure
into CallGraph -- add a degraded_languages-shaped field, populate it
from the languages present in find_cycles's own input, and confirm
frob.check's cycle-consuming gate(s) actually see it (not just that
the field exists on the model).