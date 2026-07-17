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

## Module system

Dotted module paths (`use base.labels { Pii }`); per-repo `design/`
directory; the std vocabulary ships with frob (decision D6). Cross-repo
registries are deferred but the path syntax already accommodates them.

## Parser

<!-- frob:ticket T-0059 -->

The grammar v0 subset (module/node/flow/boundary/assert/assume; no
`refine`, deferred to T-0062) is lexed and recursive-descent parsed in the
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

Python entry point (`src/frob/strata/_parse.py`):

- `parse_module(text: str) -> Result[Module, StrataError]` <!-- frob:describes src/frob/strata/_parse.py::parse_module -->
  calls the Rust parser, logs the line/col/message on failure at ERROR,
  and returns `Err(StrataError.ParseFailed)` or a validated `Module`.
