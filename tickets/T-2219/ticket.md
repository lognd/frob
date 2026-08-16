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