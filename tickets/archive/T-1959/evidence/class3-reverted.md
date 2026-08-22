# T-1959 class-3 attempt: found unsound, reverted

## Method

Same harness and denominator as T-1881 (23 symbols at `bdb39bde3`,
`tickets/T-1881/evidence/denominator.md`). Reused the disposable repro
worktree, copied the candidate detector into it, re-ran the harness.

## What was implemented

A per-package fixed point (`_syntactically_live_symrefs`): seed a "dead"
set with every private-callable candidate that has ZERO callers anywhere
in `build_reference_graph`'s intra-package edge set, then repeatedly add
any remaining candidate whose EVERY caller is already in the dead set.
This is standard "propagate unreachability through the call graph" and,
against the SYNTHETIC unit-test shape the ticket described
(`_leaf` called only by `_mid`, `_mid`'s own only reference deleted),
it works exactly as intended -- both `_mid` and `_leaf` get flagged, and
a symbol with even one live caller stays unflagged (verified with
dedicated tests, both later reverted along with the fix -- see below).

Against the REAL repo, first pass: 14/23 -> 15/23 (`_require_merge_
driver_args` newly detected). A second refinement (treating a
`frob:tests`/`frob:describes`-referenced symbol as an ordinary
reachability-graph NODE rather than an automatic root, since
`_merge_driver` itself has a `frob:describes` doc anchor but zero real
callers after its dispatch entry was deleted) did not additionally
detect `_archived_ids_for_merge_driver` -- that symbol carries its OWN
direct `frob:tests` edges, so it is exempt from ever being flagged by
DEAD001's existing declared-reference rule regardless of any call-graph
change; not a propagation gap, a structural (and arguably correct)
exemption.

## Why it was reverted: a false-positive explosion, measured

`frob check --only dead_symbols` on the CURRENT, UNMODIFIED live tree
(the same check T-1881 used to certify no new findings) went from
0 errors / 3 warnings / 41 waived to 0 errors / 117 warnings / 42 waived
-- 114 NEW findings, on code that has not changed. Severity is WARN so
this did not fail a build, but every one of these findings names a
private symbol as dead when it is, in fact, called.

Root cause, verified by hand on one example
(`src/frob/_cli_parsers/_check.py`): `_add_check_skip_args_python` is
called from `_add_check_parser` (line 54, confirmed with `git grep`).
`_add_check_parser` itself is called only from `src/frob/__main__.py`'s
central dispatch table -- a DIFFERENT directory, invisible to
`build_reference_graph`'s intra-package (same-directory) scan. This is
NOT a new discovery -- it is the SAME cross-package blind spot this
gate's own ~41 pre-existing waivers already document (`_add_*_parser`
functions dispatched from `__main__.py` are the dominant waived shape in
this repo's own `gate:DEAD` output).

The critical realization: from a SINGLE per-package scan,
`_add_check_parser` (a live, cross-package-dispatched CLI handler) and
`_merge_driver` (the ticket's own denominator case, a GENUINELY deleted
dispatch entry) are STRUCTURALLY INDISTINGUISHABLE -- both are private
functions with zero intra-package callers, called only from a different
directory's dispatch table. The only reason `_merge_driver` is
"provably dead" in this ticket's controlled scenario is that we KNOW,
from the commit history, that its dispatch entry was deleted -- the
detector itself has no way to tell "was called from elsewhere, still is"
apart from "was called from elsewhere, no longer is" using only
same-directory information. Propagating "dead" status through ANY
zero-intra-package-caller symbol therefore does not distinguish the
genuine denominator case from the dozens of already-known-and-waived
false positives -- it amplifies the existing blind spot instead of
fixing a gap.

## Disposition

REVERTED in full: `git checkout bfb6fa26c -- src/frob/gates/_dead_symbols.py
tests/test_gates.py` restores the exact T-1881-landed state (verified
clean diff against main, `frob check --only dead_symbols` back to
0 errors / 3 warnings / 42 waived -- the +1 waived vs T-1881's 41 is an
unrelated pre-existing count drift, not from this ticket).

Ratio against the T-1881 denominator: UNCHANGED at 14/23. No regression,
no improvement. Classes 1 (multi-hop propagation) and 2 (boolean-
composition hop) were not attempted -- the dispatch instruction was to
take them only if class 3 landed cleanly, and it did not.

## What class 3 actually needs

Not a bigger fixed point over the SAME per-package information -- a
WHOLE-REPO (or at minimum, cross-directory-aware) call graph, so a
caller's "zero callers" verdict is trustworthy before anything
propagates through it. That is a materially bigger change than this
ticket's day-scope (a new architecture for `build_reference_graph`'s
`paths` restriction, `frob.graph.callgraph`'s own module docstring
already documents this as a deliberate per-package bound, not an
oversight) and is NOT attempted here. Recommend either: (a) a genuinely
whole-repo call graph pass reserved for a dedicated ticket that can
absorb its cost/complexity, or (b) leave class 3 as a permanently
disclosed miss and rely on this repo's existing waiver mechanism for the
individual cases (as it already does for the ~41 cross-package
`_add_*_parser`-shaped findings).
