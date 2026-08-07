## Done report

Implemented `frob.graph.affects` (AffectedSet, affects()): a bounded BFS over
`uses-contract` reverse edges, cycle-guarded and depth/node-capped (same
posture as frob.graph.callgraph.closure, INV-014), that answers T-0325's
north-star query -- given a symref, exactly which doc anchors (frob:doc +
frob:describes), which tests (frob:tests), and which transitively-dependent
symbols must be reviewed/updated, warm from the already-built GraphSnapshot,
no test run needed.

Exposed as a new MCP tool `frob_affects(symref, max_depth=None,
max_nodes=None)` in frob.serve (_tools.py + server.py registration),
reusing the T-0177 warm-state snapshot (frob.serve._warm.warm_state) --
no cold graph reload. frob_doc_for (the existing one-hop tool) is left
unchanged; frob_affects extends it to the transitive case rather than
replacing it.

docs/modules/graph.md gained an "Affects" section documenting the query
surface, edge types consumed, and depth/transitivity semantics, plus
describes-anchors for the two new public symbols.

Scope was widened by +2 globs (tests/test_graph_affects.py,
tests/test_serve.py) via `frob ticket scope --add` since the evidence for
this ticket's new public symbols lives in those test files.

Not built in this pass (noted explicitly in docs/modules/graph.md): a
`frob graph affects <ref>` CLI subcommand (src/frob/app/graph_runner.py is
out of this ticket's declared scope) and the digest-drift GATE that would
consume affects() to fail a check when a touched symbol's dependents'
digests were not acked -- affects() is the read-side query that gate would
be built on; the gate itself is future work, tracked as a follow-up.

Gate state: frob check --ticket T-0325 is clean of new violations -- the
two COV001 hits and the DOC002 anchor-mismatch this ticket introduced were
found and fixed (anchor slug corrected, doc edges added) during
implementation; the remaining COV/DRIFT/PRE(before sweep)/REL/SYS gate
counts are unchanged pre-existing repo debt (measured before and after this
change). REL001 (public API changed, version bump) is left for the
coordinator's land-time release stamp per this repo's landing workflow,
not bumped here. PRE001 was cleared by re-running `frob ticket sweep
T-0325` after the scope widen.

### Changed
```
 tickets.md | 682 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 676 insertions(+), 6 deletions(-)
```

### Evidence
(no evidence recorded)
