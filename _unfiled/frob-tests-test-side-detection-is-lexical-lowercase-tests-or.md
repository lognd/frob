+++
id = "01M3DG64DA3GX9H2CQ9T4NMJK5"
title = "frob:tests test-side detection is lexical (lowercase tests/ or test_*.py): Unity Assets/Tests NUnit files are read as production and correct bindings are reported redundant"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
reporter = "agent"
created = "2026-09-26T00:00:00Z"
updated = "2026-09-26T00:00:02Z"
aliases = ["T-6570"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/graph/dsl.py", "src/frob/graph/__init__.py", "src/frob/testing/_collect_csharp.py", "docs/modules/graph.md"]
+++

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
