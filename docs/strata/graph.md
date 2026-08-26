# strata-core::graph -- generic typed-graph kernel

Status: kernel only (T-3005). No consumer wires a real schema onto this yet
-- ticket/architecture/spec instances are deferred to sibling tickets
T-3006/T-3007 by owner decision (T-3004 section 9), specifically so the
kernel is proven before the ticket ledger (the most contended machinery in
the system) is migrated onto it.

## Why this exists (T-3004 section 4)

`strata-core::parse` is the strata language front-end (lexer, grammar,
`parse_source`) -- syntax only, no semantic graph. `frob-core` is a
source-code kernel (call graphs, near-duplicate detection, capability
scanning) -- a spec graph there would be a category error. This module is a
new, independent layer beside the parser: a generic typed graph that a
caller configures via a `GraphSchema`, not a set of Rust enums naming
`requirement`/`test`/`decision`. That genericity is what lets future
ticket/architecture/spec instances share ONE graph kernel instead of three
bespoke stores that desync (the exact failure class T-3004's redesign is
meant to close).

## Model (`strata-core/src/graph/model.rs`)

- `NodeId` / `Kind` / `Level` -- plain `String` aliases. Kind and level
  VALUES are caller-supplied data, declared once in a `GraphSchema`, never
  hardcoded in this crate.
- `GraphSchema` -- the vocabulary a `Graph` type-checks against:
  `node_kinds`, `levels`, and per-edge-kind `EdgeKindSchema` contracts
  (`declare_node_kind`/`declare_level`/`declare_edge_kind`, additive).
- `EdgeKindSchema` -- one edge kind's construction-time contract: allowed
  src/dst node kinds (empty set = unconstrained) and a `LevelRelation`.
- `LevelRelation` -- `Any` (no constraint), `Same` (both endpoints must
  carry the identical level), or `Paired(map)` (endpoints must satisfy an
  explicit `src_level -> required_dst_level` mapping). This is how a
  consumer expresses the V-model pairing from T-3004 section 1 generically
  -- the kernel has no idea the pairing exists, it only enforces whatever
  map the caller declares.
- `Graph` -- a schema plus the nodes/edges added against it.
  `add_node`/`add_edge` are the ONLY way to mutate a graph, and both are
  `Result<(), GraphError>`: every malformed edge is refused AT
  CONSTRUCTION, never left for a later checker to discover.

### Construction-time refusals (`GraphError`)

| Variant | Refused because |
|---|---|
| `UnknownNodeKind` | node kind not declared in the schema |
| `DuplicateNodeId` | node id already present in the graph |
| `UnknownLevel` | node's level not declared in the schema |
| `UnknownEdgeKind` | edge kind not declared in the schema |
| `DanglingEndpoint` | edge names a node id with no such node |
| `WrongEndpointKind` | endpoint node exists but its kind is not in the edge kind's allowed src/dst set |
| `LevelConstraintViolation` | endpoints' levels do not satisfy the edge kind's `LevelRelation` |

Every variant is named and carries the data needed to explain the refusal
(`strata-core/src/graph/model.rs` tests exercise each one with both a
must-fail and, where relevant, a must-pass fixture over the identical
schema).

## Queries (`strata-core/src/graph/query.rs`)

- `KindFilter` -- `Any` or `Only(&BTreeSet<Kind>)`, applied by every
  traversal below. This is the "generic, cheap to express" half of T-3004
  section 2: a consumer's four closure rules restrict traversal to
  specific edge kinds (e.g. `refines`+`satisfies` for requirement-closure)
  without this crate knowing what those kinds mean.
- `Graph::forward_closure(start, filter)` / `Graph::backward_closure(start,
  filter)` -- BOTH directions of closure, per T-3004 section 2's doctrine
  that closure rules are checked both ways (the same doctrine frob already
  applies to scope: doc+code edge closure both directions).
- `Graph::reachable(from, to, filter)` -- boolean reachability built on
  `forward_closure`.
- `Graph::find_cycle(filter)` / `Graph::has_cycle(filter)` -- DFS-based
  cycle detection returning the actual cycle path as a witness, not just a
  bool. Every cycle test in this module is paired: a planted-cycle fixture
  and the IDENTICAL layout with the closing edge removed, so a "clean"
  verdict is backed by a must-fail sibling rather than a checker that has
  only ever seen one shape (the failure class recorded in
  docs/guides/agent-playbook.md's positive-control lesson).

## Deferred (not this ticket)

- No PyO3 surface yet -- `strata-core::graph` is Rust-internal until a
  consumer ticket needs to cross the Python boundary; `lib.rs`'s existing
  `#[pymodule]` wiring is untouched.
- No instance schema (requirements/tests/decisions) lives here. T-3006/
  T-3007 build those against this kernel's `GraphSchema`/`Graph` API.
- No waterfall GATE (blocking implementation on spec closure) -- T-3004
  section 9 defers that explicitly until the kernel and a real instance
  both exist.
