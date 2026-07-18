# strata surface language -- grammar, vocabularies, refinement

<!-- frob:ticket T-0048 -->

One sentence: the surface language reads like a programming language --
modules, imports, typed declarations, a pure expression sublanguage with
units as types -- and every construct is sugar that a vocabulary elaborates
to kernel facts.

## Design rules

- **No security defaults.** Anything security-relevant left unstated is a
  parse-adjacent error with a remedy, never a silent default (law 2).
- **Units are types.** `5 req/s`, `4 KiB`, `250 ms`, `15 %/month`, `24 h`.
  Unit mismatch is a type error. Numbers without units are dimensionless
  multipliers only.
- **One meaning per name.** Every reference resolves uniquely; shadowing is
  an error; there is no inheritance/override maze -- refinement (below) is
  the only hierarchy.
- **Everything addressable.** Every declaration has a qualname
  (`payments::Ingress`) usable by claims, docs anchors, directives, and
  tickets. In phase 4 these become frob graph symbols with digests, acks,
  and drift (T-0077).

## Grammar sketch (normative shape; finalized in T-0059)

```
module      := "module" ident
use         := "use" dotted ("{" ident ("," ident)* "}")?
decl        := lattice | principal | host | link | component | store
             | cache | queue | cdn | balancer | boundary | flow | secret
             | deploy | operation | policy | scenario | claim | refine
component   := "component" ident ":" trust "{" comp_item* "}"
comp_item   := "runs" "on" ref | "code" glob+ | "may" capability
             | "state" state_decl | "errors" "total"
             | "panics" "contained" "by" ref | "on" "crash" block
             | "observe" block | "abstract" | "managed"
claim       := "assert" claim_body ("require" "proof" ">=" rung)?
             | "assume" ident string "owner" ident "review" date
claim_body  := "noflow" "(" ref "->" ref ")" | bound_expr
             | "reach" "(" ref "->" ref ")" | "isolate" ...
             | "independent" "(" ref "," ref ")"
refine      := "refine" ref "into" "{" decl* bind* "}"
bind        := "binds" ref "=" ref
bound_expr  := metric "(" ref ")" "<=" quantity
quantity    := number unit | number
```

Comments are `//`; docs attach with `///` and are drift-checked once
`.strata` joins `frob.lang` (T-0077).

## The elaborator contract

A vocabulary is a pure function `surface construct -> kernel facts`
(T-0060). Only the elaborator knows what a "cache" or "secret" is; the
prover consumes kernel facts exclusively. Adding vocabulary never touches
the prover. Planned vocabularies and their owning tickets:

| Vocabulary | Contents | Ticket |
|---|---|---|
| `std.trust` | lattices, principals, components, channels, endorse/declassify boundaries | T-0060 |
| `std.infra` | store/cache/queue/cdn/balancer, delivery semantics, managed | T-0064 |
| `std.policy` | the five policy forms + packs | T-0067, T-0068 |
| `std.err` | errors total, panics contained, crash contracts, observe | T-0070, T-0074 |
| `std.secrets` | credentials as cache-of-authority | T-0082 |
| `std.deploy` | endorsement pipelines, canary, rollback | T-0083 |
| `std.incident` | breach scenarios, blast radius, containment | T-0076 |

User-defined vocabularies (custom desugaring) are deferred until the std
set proves the mechanism.

## Key construct semantics (normative summaries)

- **component / store**: nodes. `code` globs bind to source (legal only on
  refinement leaves); `managed` marks external infrastructure (no tier-2
  conformance; obligations shift to config evidence or assumes).
  Unclassified code is foreign (law 2).
- **cache X of Y**: derived view. Requires source of truth, keyed-by,
  policy, an invalidation edge for every mutating flow of Y, a staleness
  bound, and a hit ratio (declared or `measured perf:<stamp>`). Staleness
  propagates along read paths.
- **queue**: carries `delivery at_least_once|at_most_once` and ordering;
  at-least-once into a consumer without a declared idempotency key is an
  error.
- **flow**: end-to-end path with rate (+ growth, burst), transaction size,
  freshness requirement, and latency budget. Budgets and freshness are
  proved by path arithmetic.
- **capacity**: per-node service rate (`measured` binds to frob.perf
  stamps; contradiction between declared and measured is a violation),
  replica range or `singleton`. A singleton on a population-proportional
  flow is flagged at the declared growth horizon.
- **boundary**: six-phase contract; see `boundary.md`.
- **operation**: frame-conditioned writes + atomicity; see `boundary.md`.
- **secret**: cache-of-authority; lifetime bound, mandatory revocation
  edge with SLA, exact `readers()` set claim.
- **deploy**: staged rate schedule on the artifact flow, abort predicate,
  rollback latency budget; upstream endorsement chain per `std.deploy`.
- **scenario**: named rewrite + nested claims; crash contracts desugar to
  auto-generated scenarios.

## Refinement (hierarchical models)

`abstract` components may omit internals and still participate in claims;
`refine X into { ... binds ... }` decomposes them. Faithfulness (T-0062) is
three decidable checks:

1. **No new external surface** -- the refined assembly's external flows map
   onto the abstraction's declared flows.
2. **No trust laundering** -- internals below the abstraction's trust
   require interposed boundaries, else the parent claims are re-refuted.
3. **Budget distribution** -- parent bounds cover the concrete paths.

Given faithfulness, parent-level proofs survive decomposition, so
verification is compositional: each level checks against its parent's
interface only. Policies inherit downward monotonically (strengthen-only;
weakening is a refinement error). Code binding is legal only on leaves, so
implementation cannot begin on an undecomposed box; the unrefined frontier
is exactly the planning frontier, and `frob sys plan` (T-0084) maps it
onto parent/child tickets.

### v0 semantics

<!-- frob:ticket T-0062 -->

`refine ID into { (node_stmt | flow_stmt)* binds ID = ID }` is parsed in
Rust (`strata-core/src/parse.rs::parse_refine`); exactly one `binds`
clause is required and its left-hand id must equal the refine target, both
enforced as parse errors with line/col, not defaults. The elaborator
(`_elaborate.py::elaborate` -> `_elaborate_refines`) then flattens each
block into the kernel model:

- **Target validity.** The refine target must already exist in the module
  and be declared `abstract`; otherwise `StrataError.RefinementViolation`.
- **No new external surface (faithfulness check 1).** Every inner flow's
  `src` and `dst` must both be inner node ids; an inner flow touching any
  id outside the refined assembly is a violation.
- **No trust laundering (faithfulness check 2).** Every inner node's trust
  must satisfy `abstract_trust <= inner_trust` in `TRUST` (kernel `std.trust`
  lattice, `_models.py::Lattice.leq`); a lower-trust inner node is a
  violation.
- **Budget distribution (faithfulness check 3) is DEFERRED to phase 2.**
  v0 performs no budget/latency coverage check between the abstraction's
  declared bounds and the concrete inner paths; this is a known gap, not
  an oversight, tracked for the phase-2 ticket that adds path-arithmetic
  budget propagation to refine blocks.
- **Flattening.** The abstract node is removed from the kernel model; all
  inner nodes and flows are added; every outer flow whose `src` or `dst`
  named the abstraction is rewired to `bind_to` (`bind_to` must be one of
  the inner node ids, else a violation); every claim endpoint or
  `bound`-claim target naming the abstraction is rewritten to `bind_to` the
  same way, logged at INFO per rewrite. This is exactly what keeps a proof
  made against the abstraction true after decomposition (the
  compositional-proof property above).
- **Unrefined frontier.** An `abstract` node with no matching `refine`
  block is left in the kernel model with its `"abstract"` attrs marker
  intact, and elaboration logs a WARNING ("unrefined frontier") -- this is
  the planning-frontier signal (`frob sys plan`, T-0084), not an error.

## Module system

Dotted module paths (`use base.labels { Pii }`); per-repo `design/`
directory; the std vocabulary ships with frob (decision D6). Cross-repo
registries are deferred but the path syntax already accommodates them.

## Parser

<!-- frob:ticket T-0059 -->

The grammar v0 subset (module/node/flow/boundary/assert/assume/refine,
T-0062) is lexed and recursive-descent parsed in the
`strata-core` Rust extension (charter D3, amended 2026-07-17); Python only
validates the resulting JSON into frozen pydantic AST models and never
re-implements the grammar. Every malformed input yields a `{"line",
"col", "message"}` diagnostic instead of a panic or a Python exception.

Rust (`strata-core/src/parse.rs`, exposed as `strata_core.parse_source`):

- `parse_source(text: &str) -> String` <!-- frob:describes strata-core/src/lib.rs::parse_source -->
  lexes and parses one source file, returning `{"ok": <module JSON>}` or
  `{"err": {"line", "col", "message"}}`.

Python AST models (`src/frob/strata/_ast.py`), one frozen pydantic model
per grammar production:

- `Module` <!-- frob:describes src/frob/strata/_ast.py::Module -->
  -- name, nodes, flows, boundaries, claims.
- `NodeDecl` <!-- frob:describes src/frob/strata/_ast.py::NodeDecl -->
  -- id, trust, is_abstract, clearance, attrs, capacity, residence.
- `Capacity` <!-- frob:describes src/frob/strata/_ast.py::Capacity -->
  -- the parsed `capacity RATE UNIT replicas MIN..MAX` node property.
- `FlowDecl` <!-- frob:describes src/frob/strata/_ast.py::FlowDecl -->
  -- id, src, dst, label, age/rate/size, attrs, transport.
- `BoundaryDecl` <!-- frob:describes src/frob/strata/_ast.py::BoundaryDecl -->
  -- id, kind (endorse/declassify), flow_id, from_level, to_level, predicate.
- `ClaimDecl` <!-- frob:describes src/frob/strata/_ast.py::ClaimDecl -->
  -- id, kind (noflow/reach/bound), src/dst or metric/target/limit, assumed,
  owner, review.
- `RefineDecl` <!-- frob:describes src/frob/strata/_ast.py::RefineDecl -->
  -- target, nodes, flows, bind_to; see "Refinement" above for v0 semantics.

Python entry point (`src/frob/strata/_parse.py`):

- `parse_module(text: str) -> Result[Module, StrataError]` <!-- frob:describes src/frob/strata/_parse.py::parse_module -->
  calls the Rust parser, logs the line/col/message on failure at ERROR,
  and returns `Err(StrataError.ParseFailed)` or a validated `Module`.

## Elaborator

<!-- frob:ticket T-0060 -->
<!-- frob:describes src/frob/strata/_elaborate.py::elaborate -->

`std.trust` is the first vocabulary (see the table above): the elaborator
contract's pure function `surface construct -> kernel facts`, implemented
in Python (`src/frob/strata/_elaborate.py`) rather than Rust -- vocabulary
mappings are cheap and change often, unlike the parser and closure kernels
(charter D3, amended).

- `elaborate(module: Module) -> Result[KernelModel, StrataError]` <!-- frob:describes src/frob/strata/_elaborate.py::elaborate -->
  maps every `Module` declaration onto its kernel counterpart:
  - `NodeDecl` -> `Node`: `id`/`trust`/`clearance`/`attrs`/`residence` pass
    through; `Capacity` maps `rate` -> `service_rate` and carries
    `replicas_min`/`replicas_max`; `is_abstract=True` appends an
    `"abstract"` entry to `attrs` and logs at DEBUG; `RefineDecl` entries
    are then flattened into the model by `_elaborate_refines` -- see
    "Refinement -> v0 semantics" above for the full faithfulness/flattening
    contract, including the deferred budget-distribution check and the
    unrefined-frontier warning.
  - `FlowDecl` -> `Flow`: `id`/`src`/`dst`/`label`/`age`/`rate`/`size`/
    `attrs`/`transport` pass through field-for-field.
  - `BoundaryDecl` -> `Boundary`: `kind` ("endorse"/"declassify") maps onto
    `BoundaryDirection`; `flow_id`/`from_level`/`to_level`/`predicate`
    pass through.
  - `ClaimDecl` -> `Claim`: `kind` selects the kernel claim body --
    `"noflow"` -> `NoFlow(src, dst)`, `"reach"` -> `Reach(src, dst)`,
    `"bound"` -> `BoundClaim(metric, target, limit)` with `metric` mapped
    onto the `Metric` enum; `assumed`/`owner`/`review` pass through
    unchanged.

  Elaboration adds exactly the validation the parser cannot make because
  it spans multiple declarations, each failing closed with a logged
  `StrataError`:
  - `DuplicateId` -- two nodes, or two flows, share an id.
  - `UnknownReference` -- a boundary names a flow id that is not declared,
    or a `bound` claim names a target id that is not declared.
  - `RefinementViolation` -- a `refine` block fails target validity or
    either implemented faithfulness check (T-0062, see "v0 semantics"
    above).

  `noflow`/`reach` claim endpoints are left unvalidated here: they may
  name either a node id or a trust level, and only the kernel's
  `FactBase` (docs/strata/kernel.md#fact-base) can expand a trust level
  into its member nodes, so checking them early would duplicate that
  logic. The metric-name vocabulary is closed by the parser's grammar, so
  there is no defensive "unknown metric" branch in the elaborator.

## std.infra

<!-- frob:ticket T-0064 -->
<!-- frob:describes src/frob/strata/_infra.py::elaborate_infra -->
<!-- frob:describes src/frob/strata/_infra.py::InfraExpansion -->
<!-- frob:describes src/frob/strata/_ast.py::StoreDecl -->
<!-- frob:describes src/frob/strata/_ast.py::CacheDecl -->
<!-- frob:describes src/frob/strata/_ast.py::QueueDecl -->
<!-- frob:describes src/frob/strata/_ast.py::CdnDecl -->
<!-- frob:describes src/frob/strata/_ast.py::BalancerDecl -->

The second vocabulary: `store`/`cache`/`queue`/`cdn`/`balancer` are all
pure sugar over `Node`/`Flow`/`Boundary` (charter law 1) -- the prover
never learns any of these five words. Grammar (`strata-core/src/parse.rs`,
`parse_store`/`parse_cache`/`parse_queue`/`parse_cdn`/`parse_balancer`):

```
store   ID ":" TRUST "{" store_prop* "}"?
store_prop := node_prop | "engine" IDENT | "immutable" | "append_only"
            | "rpo" QUANTITY

cache   ID "of" ID "{" cache_prop* "}"?
cache_prop := "keyed_by" IDENT | "ttl" QUANTITY | "staleness" QUANTITY
            | "hit" NUM "%" | "policy" IDENT | "invalidate_on" IDENT

queue   ID "{" queue_prop* "}"?
queue_prop := "delivery" IDENT | "ordering" IDENT | "attr" ATTRVAL
            | "clearance" IDENT

cdn     ID "of" ID "{" cdn_prop* "}"?
cdn_prop := "provider" IDENT ":" TRUST | "staleness" (QUANTITY | "unlimited")
          | "hit" NUM "%" | "tls_terminates_at_provider"

balancer ID "{" balancer_prop* "}"?
balancer_prop := "policy" IDENT | "sticky"
```

Elaboration seam (`src/frob/strata/_elaborate.py::elaborate`): after the
`std.trust` mapping builds the base `Node`/`Flow`/`Boundary`/`Claim`
tuples, `_infra.py::elaborate_infra(module, nodes, flows, boundaries)` is
called with those tuples and returns an `InfraExpansion` -- the *full,
merged* replacement tuples (not an appendix), because queue delivery
propagation patches attrs on flows `std.trust` already produced. This
keeps `_elaborate.py::elaborate` the single orchestrator: it owns calling
order (std.trust, then std.infra, then refine flattening) and owns
logging `InfraExpansion.diagnostics` at WARNING. `KernelModel` (a kernel
type) gains no new field for these diagnostics -- see the seam note below.

### Desugar table

| Construct | Kernel facts produced |
|---|---|
| `store X : T { ... }` | `Node` X at trust T; `engine=<x>`/`immutable`/`append_only` become attrs; `rpo QUANTITY` becomes `rpo=<seconds>` (a time unit, or `UnitMismatch` -- docs/strata/kernel.md#age-propagation-semantics) |
| `cache X of Y { ... }` | `Node` X at Y's trust/clearance; flow `X__fill` (Y -> X, age = the ttl/staleness bound); flow `X__inval_<F>` (Y -> X, age 0) per `invalidate_on F`; `hit=<v>`/`policy=<v>`/`keyed_by=<v>` attrs |
| `queue X { ... }` | `Node` X (trust defaults to `"trusted"` -- see deviation below); `delivery=<x>`/`ordering=<x>` attrs; every outbound flow from X gains `delivery=<x>` |
| `cdn X of Y { ... }` | `Node` X at the declared provider's trust, Y's clearance; flow `X__fill` (Y -> X, age = staleness, or no age when `unlimited` over an `immutable` Y); `provider=<x>`/`hit=<v>` attrs; `tls_terminates_at_provider` adds boundary `X__declassify` (declassify, Y's clearance -> `Public`, predicate `"tls_terminates_at_provider"`) on `X__fill` |
| `balancer X { ... }` | `Node` X (trust defaults to `"trusted"`); `policy=<x>`/`sticky` attrs |

### The age collapse, applied

`ttl` and `staleness` are the same bound (charter "the three collapses");
a cache declaring only one uses it, declaring both requires they agree
(equal after unit conversion), and declaring neither is
`StrataError.MissingBound` -- deny by default, a cache with no staleness
bound is illegal, not defaulted to unbounded.

### Mandatory invalidation

"No cache without an invalidation edge": if Y (the cache's source of
truth) has *any* inbound flow at std.trust elaboration time and the cache
declares no `invalidate_on`, elaboration fails
`StrataError.MissingInvalidation`. Each `invalidate_on F` must name a
flow that both exists and writes to Y (`dst == Y`); either failure is
`UnknownReference` (F doesn't exist) or `MissingInvalidation` (F exists
but doesn't write to Y).

### The immutable-TTL pairing

`cdn ... { staleness unlimited; }` is legal only when the source (`of`)
node carries the `immutable` attr (typically via `store ... { immutable; }`).
Unbounded staleness over mutable data is `StrataError.MutableUnbounded`;
over immutable data the fill flow gets no `age` at all (immutable content
is exactly as fresh regardless of cache age, so 0 additional staleness is
correct, not a loophole).

### CDN termination is declassification

`tls_terminates_at_provider` adds a `declassify` boundary on the cdn's
fill flow, `from_level` = the source's clearance, `to_level` = `"Public"`,
`predicate = "tls_terminates_at_provider"` -- a CDN edge that terminates
TLS is where confidentiality control passes to a third party, which is
exactly what a declassify boundary means (charter security model), never
an unstated default.

### Queue delivery propagation

A `queue`'s `delivery=<x>` attr is copied onto every flow whose `src` is
the queue, so `_facts.py`'s existing at-least-once-into-non-idempotent
diagnostic (docs/strata/kernel.md#fact-base) fires on the queue's
consumers without `_facts.py` ever learning the word "queue" -- the attr
is the only channel, preserving law 1.

### Sticky-balancer contradiction

A `sticky` balancer routing to a downstream node carrying `state=none` is
a structural contradiction (sticky routing exists to pin a client to
state that, by declaration, does not exist). `elaborate_infra` reports
this as a non-fatal string in `InfraExpansion.diagnostics`;
`_elaborate.py::elaborate` logs each at WARNING. This diagnostic is not a
`KernelModel` field (kernel types may not grow a vocabulary-specific
field, per law 1) and is not folded into `FactBase.diagnostics` either,
since that would require editing `_facts.py` (a kernel file, out of
scope for T-0064) -- callers that need it programmatically call
`elaborate_infra` directly, as `tests/unit/strata/test_infra.py` does.

### Deviation: queue/balancer trust defaults to `"trusted"`

The grammar above gives `store`/`cache`/`cdn` an explicit or inherited
trust, but `queue` and `balancer` have no `TRUST` clause at all -- both
default to `"trusted"` in `_infra.py`. This is a deliberate, documented
default (not a silent one), tracked for a future grammar extension
(`frob ticket new`, filed as a T-0064 discovery) that would let `queue`/
`balancer` declare trust explicitly instead.
