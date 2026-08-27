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
  component design). REQUIRES a `code_ref` attr (below).
- `test` -- a right-side verification artifact at a paired level. REQUIRES
  a `runnable` attr (below).
- `decision` -- a decision record; the source of a `decides`/`supersedes`
  edge (T-3004 section 8: change justification is a typed edge, never
  inline prose). Carries no required attr of its own -- T-3049 owns
  normalizing the decision/invariant/review-record SHAPE as one canonical
  schema, and this ticket deliberately does not invent a second one.

## Node/edge payload (T-3044 H3)

Before this ticket a `test` node was an id with nothing runnable behind
it, an `artifact` node bound to no code, and a `supersedes` edge could not
carry a change reason -- the graph could be fully closed and mean
nothing. The kernel (`graph::model`) now supports a generic, caller-typed
attribute payload on every node/edge (`attrs: BTreeMap<String, String>`),
enforced the SAME way kind/level already are: `GraphSchema::
declare_required_node_attrs`/`EdgeKindSchema::require_attrs` name which
keys a kind must carry, and `Graph::add_node_with_attrs`/
`add_edge_with_attrs` refuse construction (`GraphError::MissingNodeAttr`/
`MissingEdgeAttr`) if one is missing. `add_node`/`add_edge` are thin
empty-attrs wrappers, so any kind with no required attrs is unaffected.

The V-model schema declares three required keys:

- `ATTR_CODE_REF` (`"code_ref"`) on every `artifact` node -- a
  `path[:symbol]` reference into the repo the artifact binds to.
- `ATTR_RUNNABLE` (`"runnable"`) on every `test` node -- the runnable
  evidence it binds to, in the same `path::Class.method` (or
  `path::function`) qualname form `frob:tests`/pytest collection use.
- `ATTR_REASON` (`"reason"`) on every `supersedes` edge -- the change
  justification, free-text but mandatory.

The kernel stays domain-agnostic: it does not know what a "runnable" or a
"code_ref" IS, only that the schema says the key must be present. Giving
these keys MEANING is entirely `graph::vmodel`'s job (this module).

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

## The five closure rules (T-3004 section 2)

Checked in BOTH directions, over a graph that has already passed the
kernel's construction-time type checks. Each rule below is STRUCTURAL
CLOSURE, never a quality judgment -- a bad-but-complete spec passes, a
brilliant-but-dangling one fails, by design (T-3004 section 2).

1. `check_no_orphan_requirements` -- every `artifact` node other than the
   innermost level (`component-design`, which has nothing more detailed
   to satisfy it) must have a backward closure over `satisfies` that
   actually REACHES a real innermost-level node -- a non-empty closure is
   not enough (T-3043): a set of peer nodes satisfying each other with
   nothing grounded underneath them used to pass this rule and no longer
   does. Catches an orphan requirement nobody's design traces to, and the
   peers-with-nothing-underneath escape T-3043 closed.
2. `check_no_unjustified_design` -- every `artifact` node other than the
   outermost level (`requirements`, which has nothing above it to trace
   to) must have a forward closure over `satisfies`/`refines`/`allocates`
   that actually REACHES a real outermost-level (requirements) node --
   again, a non-empty closure is not enough (T-3043): a mutual-satisfies
   pair tracing only to each other, with zero real requirements behind
   it, used to pass and no longer does. Catches unjustified code: a
   design element tracing to nothing real.
3. `check_no_untested_artifact` -- every `artifact` node must have >=1
   incoming `verifies` edge. Because the kernel already refuses a
   wrong-level `verifies` edge at construction, any surviving incoming
   `verifies` edge is necessarily at the paired level -- this rule only
   needs to confirm at least one exists. Catches an untested requirement.
4. `check_no_orphan_test` -- every `test` node must have >=1 outgoing
   `verifies` edge. Catches an orphan test verifying nothing.
5. `check_no_trace_cycle` -- the trace subgraph (`satisfies`/`refines`/
   `allocates`) must be acyclic, checked via the kernel's existing
   `find_cycle` (T-3043 wired it into `check_closure`; it previously
   existed but nothing called it from here). A cycle produces one
   `ClosureViolation::TraceCycle` carrying the witness path `find_cycle`
   returned, rather than a bare pass/fail. Catches a trace loop -- e.g. a
   satisfies/refines/allocates ring with no real requirements or design
   grounding it, the same escape rules 1 and 2's closure-reachability fix
   targets from the opposite direction.

`check_closure(&graph)` runs all five in order (1, 2, 3, 4, 5) and
concatenates their `ClosureViolation`s; an empty result means the graph is
structurally closed.

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
    nodes: list[tuple[str, str, str | None, dict[str, str]]],
        # (id, kind, level, attrs)
    edges: list[tuple[str, str, str, dict[str, str]]],
        # (kind, src, dst, attrs)
) -> tuple[list[str], list[tuple[str, str]]]
    # (construction_errors, [(rule_name, node_id), ...])
```

Builds a `Graph` against `v_model_schema()` from the flattened tuples.
Every node/edge that the kernel refuses at construction (unknown kind,
dangling endpoint, wrong endpoint kind, wrong paired level, T-3044 H3's
missing required attr) is collected as a debug-formatted string in the
first return slot -- collected rather than raising, so a caller sees every
malformed input in one call instead of stopping at the first. `attrs` is
`{}` for a kind with no required payload. The second slot is every
`check_closure` violation as `(rule_name, node_id)`, where `rule_name` is
one of
`orphan_requirement`/`unjustified_design`/`untested_artifact`/`orphan_test`.

A broader PyO3 export (raw `Graph`/`GraphSchema` bindings, arbitrary
`KindFilter` queries) is deliberately NOT built here -- T-3008/T-3009/
T-3010 are Rust-API consumers of this crate, not necessarily new PyO3
surface; add more only when a concrete caller needs it.

## Authoring the graph: `vmodel_node`/`vmodel_edge` (T-3042)

Before this ticket, `vmodel_check` had ZERO callers anywhere outside
strata-core's own tests and there was no way for a human to write a
requirement/spec/design/test graph at all -- the exact shipped-but-not-
reachable failure class this repo has hit before at gate scale (H1 in the
Fable design audit that opened this ticket). Two new, purely additive
top-level strata statements close that gap, following the T-3006
entity/architecture precedent (same additive-migration discipline: every
existing `.strata` file, `design/frob.strata` included, keeps parsing to
exactly empty `vmodel_nodes`/`vmodel_edges` arrays --
`existing_bare_module_files_parse_unchanged_with_no_vmodel_statements`,
`tests/unit/strata/test_vmodel_authoring.py::TestVmodelAuthoringFormat::test_designs_own_frob_strata_still_parses`):

```
vmodel_node req_1 kind "artifact" level "requirements" code_ref "src/x.rs:Req1";
vmodel_node design_1 kind "artifact" level "component-design" code_ref "src/y.rs:Design1";
vmodel_edge kind "satisfies" src design_1 dst req_1;
```

- `vmodel_node NAME kind "..." [level "..."] [runnable "..."] [code_ref
  "..."];` declares one node. `kind` and `level` are plain strings here,
  NOT validated against `KIND_ARTIFACT`/`KIND_TEST`/`KIND_DECISION` or the
  ten V-model levels at parse time -- that validation is the KERNEL's job
  (`Graph::add_node_with_attrs`), so it can never drift from the schema's
  actual source of truth. `level` is optional (a `decision` node has
  none). `runnable`/`code_ref` (T-3044 H3) are likewise optional AT THIS
  GRAMMAR LAYER, in either order -- the kernel is what refuses a `test`/
  `artifact` node missing the one its kind actually requires, once
  `frob.gates._vmodel` builds the real graph; a fixed pair of clauses
  rather than a general attr syntax is a deliberate choice, matching the
  two concrete keys the schema needs right now (a general authoring
  syntax for arbitrary record shapes is T-3049's canonical-schema scope,
  not this ticket's). Only a same-file duplicate NAME is refused at parse
  time.
- `vmodel_edge kind "..." src NAME dst NAME [reason "..."];` declares one
  edge. `src`/`dst` are deliberately NOT resolved against declared nodes
  at parse time, unlike `architecture`'s `of ENTITY`/`binds MODULE` -- a
  real V-model spans MANY files (a requirement in one, its verifying test
  in another), so per-file existence checking would be actively wrong for
  any legitimate cross-file edge. The kernel's own `DanglingEndpoint`
  refusal is what catches a genuinely undeclared endpoint, once every
  file's declarations are aggregated into one graph (next section).
  `reason` (T-3044 H3) is optional here for the same reason
  `runnable`/`code_ref` are -- the kernel refuses a `supersedes` edge
  missing it.

## Wired into `frob check`: VMOD001 (T-3042)

`frob.gates._vmodel.vmodel_gate` is the missing wire: it walks every
`.strata` file under the repo's design dir (same opt-in-on-design-dir-
existing posture as `sys_gate`, T-0135), merges every file's
`vmodel_node`/`vmodel_edge` statements into ONE graph (this is what makes
the cross-file case above resolve correctly), and runs `vmodel_check`
against it. Registered in `frob.gates._ALL_GATES` and `frob check`'s
`gates-fast` stage group, so `frob check --only vmodel` (or `--only
gates-fast`) genuinely runs it and reports a real count -- proven the
T-3014 way: a gate present in code but absent from the stage-group table
is worth nothing, the exact defect this repo has paid for before.

Every VMOD001 finding is **WARN, not ERROR** -- a deliberate owner
decision (T-3042's ticket body): frob has no V-model graph of its own yet,
so an ERROR-severity closure rule would red the tree immediately and get
waived away wholesale, the exact LARGE001-with-87-waivers failure this
repo has already recorded. Promoting to ERROR is real follow-up work, once
a genuine V-model graph exists somewhere and burn-down is plausible
(the TICK011 burn-then-promote pattern).

Doubly opt-in, both silent (not a finding of their own, same as `sys_gate`
seeing no design dir): no design dir at all, or a design dir whose
`.strata` files declare zero `vmodel_node`s. `strata_core` is imported
only once at least one node is known to exist, so neither opt-out pays
the native-extension import cost.

A file that fails to parse is skipped by this gate (logged at DEBUG) --
`sys_gate`'s SYS004 already reports a malformed `.strata` file as its own
finding; `vmodel_gate` does not duplicate that report under a second rule
id.

## Deferred (owner decision, T-3004 section 9)

- The waterfall GATE (no implementation until spec closure) is explicitly
  saved for later.
- Ticket-ledger migration onto this graph is deferred and must not be
  first (T-3004 section 9's five-failure-modes note).
