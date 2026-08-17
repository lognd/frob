---
id: T-2219
title: 'verify_imports=True call-graph gap: transitive re-export chain + call-site
  collision/attribution (residue of T-2211)'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/graph/callgraph.py
- tests/test_graph.py
evidence_scope:
- tests/test_graph.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_graph.py
  reason: repro + must-still-pass controls for multi-hop re-export reachability fix
  actor: logan
  at: '2026-08-16'
evidence:
- tests/test_graph.py::TestVerifyImportsTransitiveReachability::test_reference_graph_resolves_a_two_hop_reexport_chain
- tests/test_graph.py::TestVerifyImportsTransitiveReachability::test_call_graph_resolves_a_two_hop_reexport_chain
- tests/test_graph.py::TestVerifyImportsTransitiveReachability::test_unrelated_file_two_hops_away_still_does_not_resolve
- tests/test_graph.py::TestVerifyImportsTransitiveReachability::test_module_scoped_attribution_stays_single_hop
designated_repro_test: tests/test_graph.py::TestVerifyImportsTransitiveReachability::test_reference_graph_resolves_a_two_hop_reexport_chain
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed while verifying T-2211's fix (from-X-import-Y submodule resolution)
against the exact DEAD001/verify_imports=True measurement T-2205 used.

T-2211 fixed `_python_import_specifiers` dropping imported NAMES for
`from X import Y[, Z, ...]`. Re-measuring DEAD001 with
`build_reference_graph(..., verify_imports=True)` after that fix (same
temporary local wiring T-2205 used, not landed): baseline (verify_imports
default False) is 46 findings; with the fix, 51 (was 60 before the fix,
14 new/0 disappeared). 9 of the 14 original false positives are gone:
all of `frob.arch._python`, `frob.arch._cpp`, `frob.arch._patterns`, and
`frob.app.ticket_runner`'s cases named in T-2211's own body.

5 findings remain new relative to the 46 baseline, in two distinct
classes T-2211's scope (_extract.py's specifier extraction) does not
cover:

1. `src/frob/arch/_abstraction.py::_extract_signatures`/
   `_collect_file_dispatch_refs`/`_check_abstraction_opportunities` (3
   findings) -- a TRANSITIVE re-export chain, not a from-import-submodule
   gap: `frob/arch/_python.py` re-imports these three names FROM
   `frob.arch._abstraction` (`from frob.arch._abstraction import (X as
   X, ...)`, itself now correctly resolved by T-2211's fix -- the file
   edge `_python.py -> _abstraction.py` exists in the graph). But the
   actual CALLER is `frob/arch/__init__.py`, which calls
   `_python._check_abstraction_opportunities(...)` -- an attribute access
   through `_python`, which `__init__.py` DOES import directly, but
   `__init__.py` never imports `_abstraction.py` itself. `verify_imports`
   requires a direct file-level import edge from caller to the symbol's
   OWN defining file; it does not walk transitively through an
   intermediate re-exporting module. Needs either transitive reachability
   in the import-edge check (BFS through `_local_imports_by_path`, not a
   single-hop lookup) or callee-resolution that follows the re-export
   chain to the file that actually imports the intermediate module. Out
   of T-2211's scope (`_local_imports_by_path`'s consumer logic in
   `frob/graph/callgraph.py`, not `_extract.py`'s specifier extraction).

2. `tests/unit/strata/test_litmus_cwe.py::_repo_root` and
   `tests/unit/test_coordinator_scripts.py::_load` (2 findings) -- NOT
   caused by T-2211's change at all. `_repo_root` in this file has zero
   callers anywhere in the file (verified: grep finds only the
   definition); under `verify_imports=False` this was masked by a
   same-named `_repo_root` defined in ANOTHER test file matching
   loosely (the exact "same-named collision across python test files"
   gap this gate's own docstring already discloses as a known,
   deliberately out-of-scope narrower gap). `_load` in
   test_coordinator_scripts.py IS called, but only at module top level
   (`check_summary = _load("check_summary")`), not from inside another
   def -- suggests `build_reference_graph`'s call-site attribution may
   not record a module-top-level statement as a "call" belonging to any
   symbol at all under the stricter verify_imports path. Both need
   their own investigation; likely two separate, smaller defects in
   `frob.graph.callgraph`'s call-site/collision handling, unrelated to
   python import-specifier extraction.

Net for T-2205 (still blocked on landing verify_imports=True into
DEAD001/COV006/PROTO001-005): the remaining gap is materially smaller
(5 findings, 2 distinct known classes) than before T-2211 (14, systemic
and unexplained), but wiring verify_imports=True into DEAD001 as-is would
still introduce these 5 as new findings needing waivers or a further fix
first.

## Done report

Fixed T-2205's own residue: verify_imports=True's cross-file import
check (T-2188) was single-hop -- a candidate resolved only when it sat
directly in the caller's own import set. The real repo shape T-2205
measured and left as residue: frob/arch/__init__.py calls
_python.check(...), an attribute access through _python (which
__init__.py imports directly) resolving to a symbol _python.py
re-exports via "from frob.arch._abstraction import (check as check,
...)" -- a genuine Python re-export chain, not a coincidence.
__init__.py never imports _abstraction.py directly, so the single-hop
check could not see this reachability at all, even though it is real
(accessing _python.check genuinely reads _abstraction.py::check at
runtime, because the from-import binds check into _python's own
namespace).

FIRST DRAFT REJECTED ITSELF: a first attempt closed the import graph
transitively via a blind file-level BFS (any file reachable through any
chain of import edges, regardless of what each hop actually imported).
This FAILED its own must-still-pass control
(test_unrelated_file_two_hops_away_still_does_not_resolve): two files
merely import-CONNECTED (caller imports mid; mid imports leaf for
unrelated reasons, no re-export) fabricated an edge to leaf's own
same-named-but-unrelated private symbol -- resurrecting the exact
T-2156 bare-short-name collision this whole mechanism exists to close,
one hop further out. Caught by running the must-still-pass control
BEFORE committing, not after.

Real fix: `_named_reexports_by_path` (path -> {name: file it is
re-exported FROM}) derived from the same public
frob.lang.extract_imports/resolve_local_import surface
_local_imports_by_path already calls (no frob.lang change, staying
inside this ticket's own src/frob/graph/callgraph.py-only scope) --
recovers exactly which NAME each per-name import specifier represents
by checking whether "module.name" resolves as a file itself (T-2211's
submodule case, already handled) vs only "module" resolving (a genuine
symbol re-export). `_reexport_reachable` then chases this map PER NAME
being looked up, starting from the caller's own direct import set --
name-scoped, not a blind file BFS. Threaded through
_resolve_edges/_resolve_edges_python/_one_caller_edges and wired into
build_call_graph/build_reference_graph's verify_imports=True path only.

build_reference_graph_module_scoped (T-2156's attribution-safe
consumer, deliberately single-hop per its own
test_does_not_cross_wire_same_named_helpers_in_unrelated_files
contract) is explicitly UNCHANGED -- widening its candidate set is a
different consumer's decision with a different safety requirement, out
of this ticket's scope. Verified via
test_module_scoped_attribution_stays_single_hop (the same 2-hop
re-export fixture the reference-graph tests now resolve must still NOT
resolve through this function).

Repro: tests/test_graph.py::TestVerifyImportsTransitiveReachability::
test_reference_graph_resolves_a_two_hop_reexport_chain, committed
alone at 5a36124b2, watched FAIL against the pre-fix code
(--check-repro reported FAILED_AT_PARENT: KeyError on the caller
symref, meaning no edge was recorded at all). Fix committed separately
at a1bc73abe.

Must-still-pass controls (all bound as evidence):
- test_unrelated_file_two_hops_away_still_does_not_resolve: a file
  import-CONNECTED two hops out but never re-exporting the looked-up
  name must NOT resolve -- caught the first draft's regression.
- test_module_scoped_attribution_stays_single_hop:
  build_reference_graph_module_scoped's T-2156 attribution-safety
  contract stays single-hop, unaffected by this fix.
- (pre-existing, unaffected) TestBuildCallGraphVerifyImports's own
  T-2188 controls (cross-file resolves when imported directly, drops
  when not, default stays permissive) all still pass, confirming the
  single-hop base case is untouched.

DEAD001 delta (temporary local wiring of the measurement, same
technique T-2205/T-2211 used -- DEAD001 is ALREADY wired for real via
T-2205's own land, not a scope change here): with this fix applied,
48 findings (5 warnings + 43 waived) vs T-2205's own post-land
measurement of 51 (8 warnings + 43 waived) -- 3 resolved, 0 new. All 3
resolved findings are exactly the src/frob/arch/_abstraction.py
symbols T-2205's Done report named as this ticket's residue
(_extract_signatures, _collect_file_dispatch_refs,
_check_abstraction_opportunities). The 2 remaining findings
(tests/unit/strata/test_litmus_cwe.py::_repo_root,
tests/unit/test_coordinator_scripts.py::_load) are exactly the ones
already characterized in this ticket's own body as pre-existing/
unrelated to import verification (a same-named-collision unmasking
and a possible module-top-level call-attribution gap) -- confirmed
still true, NOT fixed here per the coordinator's explicit instruction
not to widen scope onto them.

frob check --only cycle: unmoved at 3 errors, 1 warning (T-2202's
tracked debt), measured on this worktree after the fix.

frob test --base main: python exit=0, 21 outcomes recorded, all green.

pytest tests/test_graph.py -o addopts="" -q: 135 passed, 0 failed (was
131 before this ticket's 4 new tests).

Gates: frob check --only lint shows ty clean, no ruff-check error in
callgraph.py/test_graph.py (the touched files); frob check --only
dead_symbols/drift show pre-existing repo-wide findings in files this
ticket did not touch (confirmed via git status).

### Changed
```
 src/frob/graph/callgraph.py | 153 ++++++++++++++++++++++++++++++++++++++++++--
 tests/test_graph.py         | 129 +++++++++++++++++++++++++++++++++++++
 tickets/T-2219/ticket.md    |  18 +++++-
 3 files changed, 292 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_graph.py::TestVerifyImportsTransitiveReachability::test_reference_graph_resolves_a_two_hop_reexport_chain` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestVerifyImportsTransitiveReachability::test_call_graph_resolves_a_two_hop_reexport_chain` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestVerifyImportsTransitiveReachability::test_unrelated_file_two_hops_away_still_does_not_resolve` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestVerifyImportsTransitiveReachability::test_module_scoped_attribution_stays_single_hop` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, AFFECT001@src/frob/graph/callgraph.py, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2219/src/frob/lang/_nodes.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2219, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
