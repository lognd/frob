---
id: T-2188
title: callgraph.py's build_call_graph/build_reference_graph/build_ordered_call_graph
  resolve cross-file private candidates by bare short name, unverified against imports
  -- same T-2156 mechanism, three unfixed consumers (COV006, DEAD001, PROTO001-005)
state: done
kind: security
origin: human
created: '2026-08-16'
priority: high
blocked_by:
- T-2195
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
evidence:
- tests/test_graph.py::TestBuildCallGraphVerifyImports::test_cross_file_candidate_resolves_when_caller_imports_it
- tests/test_graph.py::TestBuildCallGraphVerifyImports::test_cross_file_candidate_dropped_when_caller_does_not_import_it
- tests/test_graph.py::TestBuildCallGraphVerifyImports::test_default_is_unverified_bare_short_name_match
- tests/test_graph.py::TestScopePrivateHelperGaps::test_flags_scoped_caller_of_unscoped_private_helper
- tests/test_graph.py::TestScopePrivateHelperGaps::test_only_used_by_scope_true_when_no_external_caller
- tests/test_graph.py::TestScopePrivateHelperGaps::test_flat_dir_genuine_cross_file_helper_still_fires
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
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

## Done report

STATUS: T-2188 is BLOCKED, not done. It cannot be safely completed as
scoped -- see below.

**Diagnosis (which side was broken, established by measurement).**
Implemented the ticket's requested mechanism: cross-file candidate
resolution in `build_call_graph`, `build_reference_graph`, and
`build_ordered_call_graph` (plus their shared `_resolve_edges`/
`_resolve_edges_python`/`_ordered_private_callees` helpers) now requires
the caller's file to locally import the candidate's file
(`_local_imports_by_path`, T-2156/T-2174's own proven mechanism),
gated behind a new opt-in `verify_imports: bool` parameter (default
`False` on every function).

Measured before wiring `verify_imports=True` into any real consumer
(baseline, this repo's own tree, `frob check --only dead_symbols --only
coverage --only protocol_summary`): DEAD001=46, COV006=30, PROTO001-5=0.

Wired `build_reference_graph`'s DEAD001 consumer to `verify_imports=True`
as a trial and re-measured: DEAD001 46 -> 241, COV006 30 -> 622. A
findings-count delta this large demanded per-finding judgement, not
just counting (this ticket's own instruction) -- sampling the new
findings showed the cause was NOT genuine dead code or genuine
unreachable tests: `frob.lang._nodes.resolve_local_import`'s python
branch resolves an absolute specifier (`frob.gates._models`) only
against `root` directly (`root / "frob/gates/_models.py"`), never
`root/src/frob/gates/_models.py` -- this repo (and any src-layout repo)
therefore returns `None` for essentially every real intra-repo python
import, which does not narrow cross-file resolution, it nearly
eliminates it. `_local_imports_by_path` degrades to an EMPTY set per
file, which (correctly, by this ticket's own fail-closed design) drops
every cross-file candidate -- but the primitive feeding it is broken, so
"drop everything" fires almost universally rather than only on genuine
name-coincidence collisions.

The coordinator independently confirmed and WIDENED this finding: every
relative import form (`._land`, `..lang._nodes`) ALSO fails, not only
absolute src-layout forms, so `_local_imports_by_path` yields
essentially ZERO cross-file imports for the entire `src/frob/**`
production tree -- and by the same mechanism, T-2156's already-landed
`build_reference_graph_module_scoped` never accepts a cross-file
candidate at all (it eliminated the T-2156 false-attribution incident
by disabling cross-file attribution outright, not by making it
accurate -- the certifying `frob verify explain` evidence could not
distinguish the two outcomes, since the one case that still attributed
did so via a same-file path). I independently reproduced the
coordinator's `frob cycle` positive control (an identical two-file
import cycle, top-level vs. `src/`-prefixed): `frob cycle` finds the
cycle at top level and reports "no cycles found" for the byte-identical
src-layout copy -- confirming the blast radius extends to `frob.app.
cycle_runner`/`frob.arch._layering`/`frob.arch._python`, not just
`frob.graph.callgraph`.

**Action taken, not silent.** Filed T-2195 ("resolve_local_
import (frob.lang._nodes) does not resolve src-layout absolute python
imports, silently degrading every consumer of _local_imports_by_path to
zero cross-file imports"), raised to CRITICAL priority at the
coordinator's direction, attached two addenda widening scope (relative
import forms; the independently-reproduced `frob cycle` vacuous-green
control) and stating explicit acceptance criteria (positive cross-file
resolution cases for absolute/relative/parent-relative forms, a
regression guard for the one form that resolves today, and the
two-layout cycle control). Blocked T-2188 on it:
`frob ticket block T-2188 --by T-2195`.

**Why the code changes here are safe to land anyway.** Every new
`verify_imports` parameter defaults to `False` -- zero behavior change
for any of the three named consumers (COV006, DEAD001, PROTO001-005),
which remain on the pre-T-2188 bare-short-name match exactly as before.
The mechanism itself is implemented, documented, and covered by real
positive AND negative tests (`TestBuildCallGraphVerifyImports` in
`tests/test_graph.py`: a genuine cross-file import resolves under
`verify_imports=True`; an unrelated same-named helper in a
non-importing file does NOT fabricate an edge under `verify_imports=
True`; the default stays the old unverified behavior) -- ready for
whoever picks up the wiring once T-2195 lands and is
re-verified with a real positive control (not just "no new false
positives"), per the coordinator's own corrected methodology.

One existing consumer needed an explicit opt-out, not a blanket
tightening: `scope_private_helper_gaps` (T-0998/T-1012) intentionally
resolves by directory co-location, independent of any import
relationship (its own T-1012 docstring). Tightening it broke 3 of its
own tests (`test_flags_scoped_caller_of_unscoped_private_helper`,
`test_only_used_by_scope_true_when_no_external_caller`,
`test_flat_dir_genuine_cross_file_helper_still_fires`) until I passed
it `verify_imports=False` explicitly with a comment explaining why --
exactly the epic's own allowed shape ("two consumers with genuinely
different correctness requirements... provided the difference is
deliberate and documented"), not a silent regression.

Changed:
src/frob/graph/callgraph.py::build_call_graph
src/frob/graph/callgraph.py::build_reference_graph
src/frob/graph/callgraph.py::build_ordered_call_graph
src/frob/graph/callgraph.py::_resolve_edges
src/frob/graph/callgraph.py::_resolve_edges_python
src/frob/graph/callgraph.py::_ordered_private_callees
src/frob/graph/callgraph.py::_permissive_imports_by_path (new)
src/frob/graph/callgraph.py::scope_private_helper_gaps
tests/test_graph.py::TestBuildCallGraphVerifyImports (new)
tests/test_graph.py::TestResolveCallEdgesNative (both tests updated for
  the new `_resolve_edges_python` signature, permissive imports map)

Evidence:
- `uv run pytest tests/test_graph.py -o addopts="" -q` -> 131 passed
  (128 pre-existing + 3 new `TestBuildCallGraphVerifyImports` cases,
  positive cross-file, negative non-importing, default-unchanged).
- `uv run pytest tests/test_gates.py -o addopts="" -q` -> 726 passed,
  unchanged from pre-ticket baseline (verified via `git show main:...`
  parity check before editing).
- Baseline measurement (this repo's own tree, `verify_imports` unwired
  anywhere): DEAD001=46, COV006=30, PROTO001-5=0 -- UNCHANGED after
  this ticket's code lands, because no consumer opts in yet (confirmed
  by re-running the same `frob check` after the final code state).

Filed: T-2195 (critical, blocks T-2188), two addenda attached
widening its scope and acceptance criteria per the coordinator's own
two escalations.

Gates: `frob check --ticket T-2188` not run to closure (ticket is
blocked, not closing); targeted pytest evidence above is the acceptance
evidence for the code that IS landing (the defused, opt-in, unwired
mechanism).

Blocked: T-2188 cannot be completed as originally scoped (wiring COV006/
DEAD001/PROTO001-005 to import-verified resolution) until T-draft-
0bd874ac's `resolve_local_import` fix lands AND T-2156's own landed fix
is re-verified with a genuine positive cross-file control -- both
explicitly out of this ticket's own declared scope
(`src/frob/lang/**`). `frob ticket block T-2188 --by T-2195`
recorded.

### Changed
```
 tickets/T-2188/ticket.md                           | 11 ++-
 ...tion-repo-wide-t-2156-re-verification-needed.md | 48 +++++++++++
 ...and-fix-guidance-no-src-lexical-special-case.md | 48 +++++++++++
 tickets/T-2195/ticket.md                 | 94 ++++++++++++++++++++++
 4 files changed, 200 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_graph.py::TestBuildCallGraphVerifyImports::test_cross_file_candidate_resolves_when_caller_imports_it` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestBuildCallGraphVerifyImports::test_cross_file_candidate_dropped_when_caller_does_not_import_it` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestBuildCallGraphVerifyImports::test_default_is_unverified_bare_short_name_match` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestScopePrivateHelperGaps::test_flags_scoped_caller_of_unscoped_private_helper` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestScopePrivateHelperGaps::test_only_used_by_scope_true_when_no_external_caller` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestScopePrivateHelperGaps::test_flat_dir_genuine_cross_file_helper_still_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2188/src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2188/src/frob/graph/callgraph.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2188, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
