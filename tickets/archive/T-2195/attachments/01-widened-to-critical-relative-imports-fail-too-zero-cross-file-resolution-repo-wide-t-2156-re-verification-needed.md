## Addendum (raised to CRITICAL, scope widened)

Coordinator's own probe (and mine, reproduced independently) shows the
defect is WORSE than this ticket's original title states: it is not only
src-layout absolute imports. `resolve_local_import`'s python branch fails
for EVERY intra-repo import form actually used in this codebase:

    scripts.fleet_status              -> scripts/fleet_status.py   OK (root-relative absolute)
    frob.tickets._land                -> None   (src-layout absolute)
    ._land                            -> None   (relative sibling)
    ..lang._nodes                     -> None   (relative parent)

Reproduced directly against `src/frob/tickets/_land_git_ops.py`'s own
real import list -- every single `frob.*` import resolves to `None`.
Only a module sitting directly under `root` (no `src/` prefix) ever
resolves. Since all of `src/frob/**` imports via absolute `frob.*` or
relative `.`/`..`, `_local_imports_by_path` yields ZERO cross-file
imports for the entire production codebase, not just a src-layout
subset.

Consequence for T-2156 (already landed): `build_reference_graph_module_
scoped`'s entire mechanism is "resolve a cross-file private candidate
ONLY when the caller's file imports the candidate's file" -- with this
primitive returning `None` for every intra-repo import, that condition
is never satisfiable in `src/frob/**`, so the function accepts NO
cross-file candidate at all. It eliminated the T-2156 false-attribution
incident by eliminating cross-file attribution outright, not by making
it accurate. The certifying evidence (`frob verify explain` on two
symbols, one UNATTRIBUTED and one correctly attributed) cannot
distinguish this from a working fix, because the one that attributed did
so via a SAME-FILE path -- consistent with both a correct fix and a
fully-disabled-cross-file one.

Acceptance for the fix must include a POSITIVE case, not only negatives:
a known-good cross-file import (e.g. `frob.tickets._land` imported from
`src/frob/tickets/_land_git_ops.py`, and the relative `._land` form from
the same file) must resolve to the real path
`src/frob/tickets/_land.py`, not just confirm bad imports still return
`None`.

Blocks T-2188 (extending this same import-verification pattern to
`build_call_graph`/`build_reference_graph`/`build_ordered_call_graph`,
which feed COV006/DEAD001/PROTO001-005) AND should trigger a
re-verification of T-2156's own landed fix once resolved (confirm a
real cross-file attribution edge exists post-fix, not just that the
false-positive case stays clean) -- filing that re-verification as a
separate follow-up is the coordinator's call, not folded into this
ticket's own scope.
