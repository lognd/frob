---
id: T-draft-317270e0
title: 'frob:tests test-side detection is lexical (lowercase tests/ or test_*.py):
  Unity Assets/Tests NUnit files are read as production and correct bindings are reported
  redundant'
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
due: null
rank: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/graph/dsl.py
- src/frob/graph/__init__.py
- src/frob/testing/_collect_csharp.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/_tdd_order.py
  reason: T-3068 holds a live in-progress lease on this file; consolidating the duplicate
    _looks_like_test_path there collides with active work. Fix the graph-side collector-based
    predicate now (dsl.py, graph/__init__.py, testing/_collect_csharp.py) and file
    a follow-up ticket to fold _tdd_order.py's copy onto the shared implementation
    once T-3068 lands.
  actor: logan
  at: '2026-09-26'
body_changes:
- mode: set
  reason: 'DOC006 inline waivers: body names external or future-facing paths (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-26'
  old_length: 1594
  new_length: 1700
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by the project-hullbreach session (2026-09-26) on the Unity 6 game
repo: a correct
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->    // frob:tests Assets/Scripts/Hullbreach.Ship/ShipBody.cs::ShipBody.AppliedForcesThisStep
above an NUnit [Test] in Assets/Tests/EditMode/Hullbreach.Ship.Tests/
ShipBodyTests.cs is reported as "malformed directive: frob:tests on
production symbol ... is redundant (T-4710)" with the test and production
sides swapped; the bindings had to be removed to get malformed=0.
Verified on dev b41443f46d: `frob.graph.dsl.looks_like_test_path` (and its
near-duplicate `frob.gates._tdd_order._looks_like_test_path`) decide the
test side from a lowercase `tests` directory part or a `test_*.py` /
`*_test.py` leaf name, so `Assets/Tests/...` (capital T) and `*Tests.cs`
are production-shaped and `_reorient_test_edge` flips the edge.

Owner directive: token/grammar, never lexical. Deliver: the test side is
decided from the language collector, not the path: for C#/Unity a file is
test-side when the C# collector finds NUnit test attributes in it or its
asmdef references nunit.framework / carries UNITY_INCLUDE_TESTS; for
Python the collector's pytest discovery; keep the path rule only as the
fallback when no collector claims the file. Both predicates share one
implementation (the layering waiver in _tdd_order names why they were
split; resolve that rather than duplicating again). Positive control: the
hullbreach shape above in a fixture Unity repo binds cleanly and TDD001
sees an implementation -> test edge; a real production-side duplicate
still reports T-4710. Designated repro: that fixture test.
