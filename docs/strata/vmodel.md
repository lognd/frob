# The V-model spec graph (`strata-core::graph::vmodel`)

<!-- frob:waive REF002 reason="T-3007 is the FIRST consumer of strata-core::graph;
strata-core/src/lib.rs's vmodel_check frob:doc is the single inbound reference by
design until T-3008/T-3009/T-3010 (siblings blocked on this schema) land as the
intended second reference" -->

T-3004 sections 1-2's design decision, made concrete: the first consumer of
the generic typed-graph kernel (`strata-core::graph`, docs/strata/graph.md).
This module supplies the V-model's node kinds, levels, edge kinds, and the
paired-level relation that makes T-3004 section 1's pairing table checkable
by construction, plus the four structural closure rules from section 2.

Nothing here reaches into `graph::model`/`graph::query` to add spec-specific
knowledge -- the kernel still names no domain vocabulary. If a future ticket
needs to change kernel behavior to serve this module, that is a signal the
schema abstraction is wrong, not a reason to special-case this consumer in
the kernel.

## Node kinds

- `artifact` -- a left-side V-model artifact at some level (requirement,
  requirement specification, system specification, system design,
  component design).
- `test` -- a right-side verification artifact at a paired level.
- `decision` -- a decision record; the source of a `decides`/`supersedes`
  edge (T-3004 section 8: change justification is a typed edge, never
  inline prose).

## Levels: the V pairing (T-3004 section 1)

| Left (artifact)              | Right (test), PAIRED           |
|-------------------------------|---------------------------------|
| `requirements`                 | `customer-test`                 |
| `requirement-specification`    | `customer-test-plan`            |
| `system-specification`         | `system-integration-test-plan`  |
| `system-design`                 | `subsystem-integration-test-plan` |
| `component-design`             | `component-unit-test`           |

`v_model_schema()` declares all ten levels and builds the `verifies` edge
kind's `LevelRelation::Paired` map from this table (keyed by the right-hand
i.e. test level, mapping to the required left-hand artifact level -- the
kernel's `verifies` convention is src=test, dst=artifact). A `verifies` edge
whose test is not at its target artifact's paired level is refused at
CONSTRUCTION by the kernel itself (`GraphError::LevelConstraintViolation`),
never discovered later by a separate checker.

## Edge kinds

- `satisfies` (artifact -> artifact): a design element traces up to the
  requirement it justifies. Walked by closure rules 1 and 2.
- `verifies` (test -> artifact, level-paired): a test verifies an artifact
  at that artifact's paired level. Walked by closure rules 3 and 4.
- `refines` (artifact -> artifact): a finer artifact refines a coarser one.
- `allocates` (artifact -> artifact): a system-level artifact allocates
  responsibility to a component-level one.
- `decides` (decision -> artifact): a decision record resolves a question
  about an artifact.
- `supersedes` (unconstrained): a change justification edge, carrying the
  reason on the decision node (T-3004 section 8).
- `blocked_by` (unconstrained): pure scheduling fact, explicitly NOT the
  organising relation (T-3004 section 3) -- survives as one edge kind among
  the others rather than being removed.

### Schema assembly

`v_model_schema()` assembles the node kinds, the ten levels, and all seven
edge kinds above into one `GraphSchema` (`strata-core::graph::model`) --
the single function a caller invokes to get a `Graph::new(...)`-ready V-model
schema. `v_pairing()` is its building block: the five (left, right) level
pairs in T-3004 section 1's order, reused both to declare every level and
to build `verifies`'s `LevelRelation::Paired` map.

## The four closure rules (T-3004 section 2)

Checked in BOTH directions, over a graph that has already passed the
kernel's construction-time type checks. Each rule below is STRUCTURAL
CLOSURE, never a quality judgment -- a bad-but-complete spec passes, a
brilliant-but-dangling one fails, by design (T-3004 section 2).

1. `check_no_orphan_requirements` -- every `artifact` node must have >=1
   incoming `satisfies` edge (backward closure over `satisfies` is
   non-empty). Catches an orphan requirement nobody's design traces to.
2. `check_no_unjustified_design` -- every `artifact` node must have >=1
   outgoing edge among `satisfies`/`refines`/`allocates` (forward closure
   over that set is non-empty). Catches unjustified code: a design element
   tracing to nothing.
3. `check_no_untested_artifact` -- every `artifact` node must have >=1
   incoming `verifies` edge. Because the kernel already refuses a
   wrong-level `verifies` edge at construction, any surviving incoming
   `verifies` edge is necessarily at the paired level -- this rule only
   needs to confirm at least one exists. Catches an untested requirement.
4. `check_no_orphan_test` -- every `test` node must have >=1 outgoing
   `verifies` edge. Catches an orphan test verifying nothing.

`check_closure(&graph)` runs all four in order and concatenates their
`ClosureViolation`s; an empty result means the graph is structurally closed.

Every rule in `strata-core/src/graph/vmodel.rs` has both a must-fire fixture
(a graph genuinely violating it) and a must-stay-quiet fixture (a graph
satisfying it) over comparable layouts, per the positive-control lesson
already recorded for this kernel's cycle detector (docs/strata/graph.md).

## PyO3 surface: `vmodel_check`

The only Python-facing function this ticket added. `strata-core::graph` as
a whole stays Rust-internal (docs/strata/graph.md's now-superseded
"deferred" note) -- only this one operation crossed the boundary, because
it is the only one a Python caller needs right now:

```
vmodel_check(
    nodes: list[tuple[str, str, str | None]],   # (id, kind, level)
    edges: list[tuple[str, str, str]],          # (kind, src, dst)
) -> tuple[list[str], list[tuple[str, str]]]
    # (construction_errors, [(rule_name, node_id), ...])
```

Builds a `Graph` against `v_model_schema()` from the flattened tuples.
Every node/edge that the kernel refuses at construction (unknown kind,
dangling endpoint, wrong endpoint kind, wrong paired level) is collected as
a debug-formatted string in the first return slot -- collected rather than
raising, so a caller sees every malformed input in one call instead of
stopping at the first. The second slot is every `check_closure` violation
as `(rule_name, node_id)`, where `rule_name` is one of
`orphan_requirement`/`unjustified_design`/`untested_artifact`/`orphan_test`.

A broader PyO3 export (raw `Graph`/`GraphSchema` bindings, arbitrary
`KindFilter` queries) is deliberately NOT built here -- T-3008/T-3009/
T-3010 are Rust-API consumers of this crate, not necessarily new PyO3
surface; add more only when a concrete caller needs it.

## Deferred (owner decision, T-3004 section 9)

- The waterfall GATE (no implementation until spec closure) is explicitly
  saved for later.
- Ticket-ledger migration onto this graph is deferred and must not be
  first (T-3004 section 9's five-failure-modes note).
