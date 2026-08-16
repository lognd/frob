---
id: T-2188
title: callgraph.py's build_call_graph/build_reference_graph/build_ordered_call_graph
  resolve cross-file private candidates by bare short name, unverified against imports
  -- same T-2156 mechanism, three unfixed consumers (COV006, DEAD001, PROTO001-005)
state: queued
kind: security
origin: human
created: '2026-08-16'
priority: high
parent: T-1662
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/graph/callgraph.py
- src/frob/gates/__init__.py
- src/frob/gates/_dead_symbols.py
- src/frob/gates/_protocol_summary.py
- docs/modules/graph.md
- tests/test_graph.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1662 child. `frob.graph.callgraph`'s three general-purpose graph
builders -- `build_call_graph`, `build_reference_graph`,
`build_ordered_call_graph` -- resolve a CROSS-FILE candidate for a
private-symbol call/reference token purely by matching the token's BARE
SHORT NAME against a repo/package-wide `_short_name_index`, with no
verification that the caller's file actually imports the candidate's
file. This is the identical mechanism T-2156 found and fixed for exactly
ONE consumer (verify attribution) -- the fix landed as a NEW, separate
function, `build_reference_graph_module_scoped` (T-2156/T-2174,
docs/modules/graph.md#attribution-safe-reference-graph-t-2156), which
adds an import check via `_local_imports_by_path`. The three ORIGINAL
functions were deliberately left unchanged (`build_reference_graph`'s own
T-2174 docstring: "why build_reference_graph itself stays unchanged") --
correct for its ORIGINAL single consumer at the time (T-0422's dead-
symbol gate, which only needs a conservative "referenced somewhere"
signal), but every caller found below needs a caller-specific TRUTH
about whether symbol X actually calls/references symbol Y, and gets a
same-short-name GUESS instead.

T-2156's own incident: a test defining `_run`/`_commit_all` (18 files in
this repo define one or both) got graph edges to all 17/18 unrelated
same-named private helpers, fabricating attribution edges that raised a
fleet-wide quarantine for hours. That was the ATTRIBUTION consumer,
already fixed. The other three callers of the same lexical-name
mechanism, none fixed:

1. `src/frob/gates/__init__.py:3106` (COV006, the TEST family's
   "reachable by direct closure" rescue check) -- `paths = (test_file,
   target_file)`, exactly two files, `build_call_graph(root, paths)`. If
   the test file and target file each independently define a
   same-named private helper (unrelated to each other), COV006 will
   read a `frob:tests` edge as reachable via the FABRICATED edge and
   silently pass evidence that does not actually reach the target --
   the false-POSITIVE-coverage direction, the more dangerous one for a
   test-obligation gate.

2. `src/frob/gates/_dead_symbols.py:759` (DEAD001) -- `files =
   _package_files(root, record.id.path)`, every file in the symbol's
   OWN package, `build_reference_graph(root, files)`. A genuinely dead
   private symbol whose short name COINCIDES with an actually-called
   private symbol elsewhere in the same package reads as referenced and
   is never flagged -- the false-NEGATIVE direction (T-1683's
   symref-blast-radius ticket is adjacent but different: that one is
   about a live finding's waiver blast radius, not about a dead symbol
   escaping detection in the first place).

3. `src/frob/gates/_protocol_summary.py:1038,1049` (PROTO001-005) --
   `files = _package_files(root, sample_path)`, `build_call_graph(root,
   files, mark_unresolved=True)` and `build_ordered_call_graph(root,
   files)`. Same package-wide short-name index feeds both the plain and
   ordered summaries `compute_protocol_summaries` walks; a fabricated
   edge can poison a protocol-established-state computation the same
   way T-2156's fabricated edge poisoned attribution.

Every one of these three was classified (a) "semantic already" in
docs/design/gate-semantics-classification.md (T-1663) -- correctly, from
the SURVEY's own vantage point (each caller does consume `frob.graph`
snapshot/callgraph edges, not raw text). The defect is one level down:
the edges themselves are name-coincidence guesses for any candidate
outside the caller's own file, not verified reachability. This is
exactly the epic's own class-(c) definition ("decides from text/path/
name matching where a resolved symbol or graph edge exists ... and
would change the answer") -- it was just inside the shared substrate,
not visible to a per-gate-module audit.

WANTED, reusing the substrate T-2156/T-2174 already built (per this
epic's own item 2 -- do not build a second parallel analysis layer):

- Extend cross-file candidate resolution in `build_call_graph`,
  `build_reference_graph`, and `build_ordered_call_graph` (or their
  shared `_resolve_edges`/`_ordered_private_callees` helpers) to require
  the caller's file import the candidate's file for any candidate
  OUTSIDE the caller's own file -- reusing `_local_imports_by_path`,
  the exact mechanism `build_reference_graph_module_scoped` already
  proved out. A same-file candidate needs no import check (a symbol
  always "imports" its own file).
- Per this epic's item 3 (fail-closed): where import verification cannot
  determine a paths's local import set at all (a parse failure, an
  unsupported grammar), the affected candidates must not silently
  fall back to the unverified short-name match -- report UNRESOLVED
  or drop the candidate, matching `build_call_graph`'s existing
  `UNRESOLVED_CALLEE` sentinel convention (T-0809) rather than a silent
  pass.
- Re-verify COV006, DEAD001, and PROTO001-005 findings on this repo's
  own tree before/after (same-short-name collisions are common here --
  `_run`/`_commit_all` alone span 18 files) as the acceptance evidence,
  not just a passing unit test on a synthetic fixture.
- Update docs/modules/graph.md's `build_reference_graph` /
  `build_call_graph` sections and their docstrings once the cross-file
  guess is closed; the T-2174 "why build_reference_graph itself stays
  unchanged" note becomes stale once this lands and needs updating or
  removing.

Acceptance criteria must name the mechanism explicitly (import-edge
verification via `_local_imports_by_path`/`build_reference_graph_module_
scoped`'s own precedent), not "improve accuracy" or "reduce false
positives" -- vague language here is exactly how an implementer reaches
for `in`/`re.search` again instead of the graph.
