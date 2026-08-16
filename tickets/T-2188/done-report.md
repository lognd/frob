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

**Action taken, not silent.** Filed T-draft-0bd874ac ("resolve_local_
import (frob.lang._nodes) does not resolve src-layout absolute python
imports, silently degrading every consumer of _local_imports_by_path to
zero cross-file imports"), raised to CRITICAL priority at the
coordinator's direction, attached two addenda widening scope (relative
import forms; the independently-reproduced `frob cycle` vacuous-green
control) and stating explicit acceptance criteria (positive cross-file
resolution cases for absolute/relative/parent-relative forms, a
regression guard for the one form that resolves today, and the
two-layout cycle control). Blocked T-2188 on it:
`frob ticket block T-2188 --by T-draft-0bd874ac`.

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
whoever picks up the wiring once T-draft-0bd874ac lands and is
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

Filed: T-draft-0bd874ac (critical, blocks T-2188), two addenda attached
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
(`src/frob/lang/**`). `frob ticket block T-2188 --by T-draft-0bd874ac`
recorded.

### Changed
```
 tickets/T-2188/ticket.md                           | 11 ++-
 ...tion-repo-wide-t-2156-re-verification-needed.md | 48 +++++++++++
 ...and-fix-guidance-no-src-lexical-special-case.md | 48 +++++++++++
 tickets/T-draft-0bd874ac/ticket.md                 | 94 ++++++++++++++++++++++
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
