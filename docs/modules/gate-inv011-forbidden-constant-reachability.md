# INV011: forbidden-constant reachability (T-3962)

Standalone page for `frob.gates._design_invariants.inv011_violations`,
written here because `docs/modules/gates.md` (INV011's real home, next to
"INV007 and INV008 (T-0757)") was leased by another in-progress ticket
for this ticket's whole duration -- see T-draft-9a4eb7be's body for the
fold-in note that tracks moving this section into `docs/modules/gates.md`
(plus the `INV011` row in that file's rule table and `frob:enumerates`
directive) once the lease clears.

## INV011 (forbidden-constant reachability)

F-175's actual incident this generalizes: a security-relevant frozenset
(`EXCLUDED_TABLES`/`FORBIDDEN_COLUMNS`) was consulted on three write
paths and skipped on the fourth (`revert_change`) -- a bug class that,
before this gate, only a reviewer's own memory of "did every caller
check the denylist" could catch.

`frob:invariant INV-### guards="*_FORBIDDEN/*_EXCLUDED/*_ALLOWED"
entrypoints="path::qual[,path::qual2,...]"`, anchored on the guarded
SINK symbol (`edge.src`), declares that every call-graph path from each
declared entrypoint to that sink must pass through at least one node
that references the named frozenset (`guards=`'s value must match the
`FORBIDDEN`/`EXCLUDED`/`ALLOWED` naming convention as a prefix or suffix
component -- a differently-named constant is simply not an INV011
obligation, not a malformed one).

`frob.gates._design_invariants.inv011_violations` reuses
`frob.graph.callgraph`'s existing BFS substrate rather than a second
call-graph traversal engine (T-3962 widens `closure` with an `exclude`
parameter for exactly this): it builds `build_call_graph` scoped to the
sink's and each entrypoint's own files, computes the set of nodes in
that graph that reference the guard (`callgraph.references_name`, a thin
wrapper over `frob.lang`'s existing broad-recall `_referenced_names`
extractor -- the same one DEAD001 already uses), and asks whether the
sink is still reachable from the entrypoint once those guard-referencing
nodes are excluded from further expansion. If it is, that is a live path
that never consulted the guard -- an ERROR-severity finding naming the
unguarded entrypoint. A sink that references the guard itself, or an
entrypoint that references it before calling anything downstream, is
inherently guarded for that path and produces no finding.

Same posture as INV007/INV008: an explicitly declared obligation only,
never a bare-vocabulary heuristic, so there is no first-turn-on debt
corpus to phase in against.
