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

### `node` grammar (implemented; T-0132 closes the `code=`/`may` gap,
T-0136 adds `on deploy`, T-0154 adds `carries`, T-0172 adds `managed`)

The construct actually implemented by `strata-core/src/parse.rs::parse_node`
today is spelled `node`, not the future `component` shown in the sketch
above (T-0059 renames it once `runs on`/`state` land). Its
grammar, extended by T-0132 to admit `code`/`may`, by T-0136 to admit
`on deploy`, by T-0154 to admit `carries`, and by T-0172 to admit
`managed`:

```
node        := "node" IDENT ":" TRUST "abstract"? ("{" node_prop* "}")?
node_prop   := "clearance" IDENT | "attr" ATTRVAL | "residence" IDENT
             | "capacity" quantity "replicas" INT ".." INT
             | "skew" "zipf" NUMBER | "errors_total"
             | "panics_contained_by" IDENT | "observe" observe_block
             | "code" STRING+ | "may" STRING | "on" "deploy" deploy_block
             | "carries" STRING+ | "managed"
deploy_block  := "{" deploy_prop (";" deploy_prop)* "}"
deploy_prop   := "canary" "{" canary_stage ("," canary_stage)* "}"
                | "endorsed_by" IDENT ("," IDENT)*
                | "rollback" "within" quantity
canary_stage  := IDENT "for" quantity
ATTRVAL     := IDENT ("=" IDENT)?
STRING      := '"' char* '"'   // no escapes in v0; '"' and newline forbidden
```

**`managed` (T-0172):** a bare marker, same shape as `errors_total` --
external, pure-config infrastructure (e.g. a Caddyfile-configured edge)
declared to have no scannable code, so it needs no fake `code=` glob to be
honestly modeled. `store` (below) accepts the identical bare `managed`
marker for the same reason (`strata-core/src/parse.rs::parse_store`) --
"component / store: nodes" (#key-construct-semantics), so both get it.
Elaboration (`_elaborate.py::_elaborate_node`, `_infra.py::
_elaborate_store`): one `"managed"` node attr, the same bare-marker
convention `errors_total`/`abstract` already use (`_code_binding.py::
is_managed` reads it back). Semantically: `check_import_conformance`
(`_code_binding.py`) skips a managed node's owned files the same way it
skips `FOREIGN` files -- "no tier-2 conformance" -- and a fired THREAT003
weakness obligation on a managed node (`_threat.py::_check_one_discharge`)
still needs a discharging claim proving a chokepoint shape and clearing the
catalog rung, but is exempt from the boundary-KIND (`_mitigation_is_
chokepoint`) proof a code-modeled node needs, the SAME exemption an
`assume` claim already gets -- "obligations shift to config evidence or
assumes."

**`carries` (T-0154, docs/strata/threat.md#pii-declarations-std-pii-t-0154):**
`STRING+` (tag+, at least one -- a bare `carries;` is a parse error,
matching `code`'s glob+ requirement, per law 2), same STRING-not-IDENT
reasoning as `code`/
`may` (a `<category>.<field>` PII tag carries `.`, not a valid ident
char). `strata-core/src/parse.rs::parse_store` accepts the identical
`carries STRING+` clause -- a store is the most common PII resting place.
Elaboration (`_elaborate.py::_elaborate_node`, `_infra.py::
_elaborate_store`): each tag becomes one `pii=<tag>` attr, the same
per-atom desugar convention `code` established (`_pii.py::
node_pii_tags` reads it back).

**`code`/`may` on `store` (T-0166):** the identical `code STRING+` /
`may STRING` clauses `node` has, now also accepted by
`strata-core/src/parse.rs::parse_store` -- "component / store: nodes"
(#key-construct-semantics), the same reasoning `managed`/`carries` above
already document for this construct. Before T-0166, `parse_store` had no
`code`/`may` branch at all (a real, narrow grammar gap this ticket found:
the `store_prop := node_prop | ...` grammar line above implied support
that did not exist -- T-0150 worked around it by folding a store's owning
code into a neighboring `node` instead, see `design/frob.strata`'s
`tickets_ledger` history). Elaboration (`_infra.py::_elaborate_store`) is
byte-for-byte the same desugar `_elaborate.py::_elaborate_node` gives
`node`: `code` globs become one `code=<glob>` attr per glob (the SAME
`_code_binding.py::_node_code_globs` convention `code` on `node`
established), and `may` capability atoms land directly on the elaborated
`Node`'s `may` field. Both consumers read `Node.may`/`code=` attrs
generically off any elaborated `Node` with no store/node distinction, so
a store with `code`/`may` participates in tier-2 import conformance
(`_code_binding.py::check_import_conformance`) and auto-instantiates
THREAT003 weakness obligations (`_threat.py::check_discharge_completeness`)
exactly the way a code-modeled node's would -- no new join, no new
exemption.

**Design choice (T-0132): STRING-quoted values, not a new token class.**
`code=<glob>` globs (`src/frob/**`) and `may` capability atoms
(`net.out:stripe.com`) both need characters -- `*`, `/`, `.`, `:` -- that
`is_ident_cont` never accepted and that would each need their own
lexer special-case if given a dedicated atom token. The lexer already had
a general-purpose `TokKind::Str` (used by `boundary ... when "predicate"`
and `assume ... review "date"`); reusing it needs zero new `TokKind`
variants, imposes no new escaping rules, and generalizes to any future
value that needs non-ident characters, at the cost of quotes the ATTRVAL
IDENT form doesn't need. A dedicated glob/capability atom token was
rejected: two bespoke character classes (one permitting `/`+`*`, one
permitting `.`+`:`) for two constructs is exactly the "grow a token per
vocabulary" trap law 1 warns against, whereas STRING is already
general-purpose parser furniture.

`code` is `STRING+` (glob+, at least one -- a bare `code;` is a parse
error, not a silent zero-glob no-op, per law 2). `may` is a single
`STRING` per statement; multiple capabilities are written as repeated
`may "...";` statements, matching the repeatable-statement shape `attr`
already uses. Elaboration (`_elaborate.py::_elaborate_node`): each `code`
glob becomes one `code=<glob>` node attr, the same convention
`_code_binding.py::_node_code_globs` already reads (T-0078); `may` atoms
copy straight into `Node.may` (`_models.py`), which has carried this field
since the kernel model was defined but had no surface syntax to write it
until now.

### `secret` grammar (implemented; T-0136)

`strata-core/src/parse.rs::parse_secret` implements the surface grammar
`std.secrets` (below) previously only had as a Python-API vocabulary:

```
secret      := "secret" IDENT "{" secret_prop (";" secret_prop)* "}"
secret_prop := "issued_by" IDENT | "audience" "{" IDENT ("," IDENT)* "}"
             | "lifetime" quantity | "revoke" quantity
```

`issued_by` and `lifetime` are mandatory (parse errors if absent, per law
2 -- a credential with no issuer or no rotation cadence is a dangling
promise, not a legal declaration); `audience`/`revoke` are grammar-optional
and default to `()`/`None`. `revoke` staying optional at the grammar layer
(rather than a third mandatory clause) matches `_secrets.py::SecretSpec`'s
own typing (`revoke: Quantity | None = None`) -- the mandatory-revocation
rule is enforced once, in `_secrets.py::_validate_secret_bounds`
(`StrataError.MissingRevocation`), not duplicated as a parser-level
requirement (charter law 1: a vocabulary's rule lives in one place).
`_elaborate.py::_elaborate_secrets` builds a `SecretSpec` straight from
each parsed `SecretDecl` and calls the landed `elaborate_secret` (T-0082)
unchanged -- no validation logic is duplicated at the surface-syntax layer.

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

<a id="key-construct-semantics"></a>
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

<a id="std-secrets"></a>
## std.secrets: credentials as cache-of-authority (T-0082)

<!-- frob:ticket T-0082 -->
<!-- frob:describes src/frob/strata/_secrets.py::SecretSpec -->
<!-- frob:describes src/frob/strata/_secrets.py::SecretExpansion -->
<!-- frob:describes src/frob/strata/_secrets.py::elaborate_secret -->
<!-- frob:describes src/frob/strata/_secrets.py::SECRET_LABEL -->

A credential is modeled as exactly one more cache-of-authority
(docs/strata/kernel.md#age-propagation-semantics): `issued_by` is the
source of truth, `lifetime` is the same TTL bound a cache's `ttl`/
`staleness` is, and the mandatory revocation edge is the same
deny-by-default rule `std.infra`'s `invalidate_on` already enforces --
"no cache without an invalidation edge" and "no credential without a
revocation edge" are one rule, not two (docs/strata/charter.md). No new
kernel primitive or age metric is added (charter law 1).

`elaborate_secret(spec, known)` (`_secrets.py`) desugars a `SecretSpec` to:

- a `Node` for the credential itself, at `Secret` clearance;
- an **issue** flow (`issued_by -> secret`, `age = lifetime`) -- the same
  age-bearing hop a cache's `fill` flow is;
- a mandatory **revocation** edge (`issued_by -> secret`,
  `attrs=("revocation",)`) -- absent, elaboration fails closed with
  `StrataError.MissingRevocation`, mirroring `MissingInvalidation`;
- one **reads** flow per `audience` member (`secret -> reader`) -- the
  substrate the auto-generated `readers(secret) == audience` claim
  (`SetEquality`, docs/strata/kernel.md#claim-forms-and-their-decision-
  procedures) closes over, reusing the same forward closure `reach`
  claims already use (`_claims.py::_eval_set_equality`).

A caller wanting a bound on the credential's own age (`age(secret) <=
some_limit`) asserts an ordinary `AGE` `bound` claim with
`target=spec.id` -- no new claim form, per the same reasoning
docs/strata/kernel.md#growth-horizons-saturation-dating-not-a-new-claim-
form already documents for growth-awareness.

**Secret-in-logs / secret-in-repo / secret-in-artifact** need no bespoke
check: each is a `Secret`-labeled flow resting at a node whose
`clearance` is below `Secret`, which `_facts.py::_structural_diagnostics`
already flags generically for every label in the `Public < Internal <
Pii < Secret` lattice (it was written for `Pii`; `Secret` is simply the
lattice's top). This is the CWE-798/256 hardcoded/plaintext-credential
precondition from docs/strata/threat.md's catalog, discharged by
machinery that already existed before this ticket.

**Surface grammar implemented (T-0136).** The `.strata` grammar's `secret X
{ issued_by Y; audience { ... }; lifetime T; revoke T' }` syntax (see the
"`secret` grammar (implemented)" section above) is now wired end to end:
`strata-core/src/parse.rs::parse_secret` -> `_ast.py::SecretDecl` ->
`_elaborate.py::_elaborate_secrets` -> this module's `elaborate_secret`,
unchanged. `std.secrets` is no longer a Python-API-only vocabulary.

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

## Code binding (tier 2, v0 implementation)

<!-- frob:ticket T-0078 -->
<!-- frob:describes src/frob/strata/_code_binding.py::bind_code -->
<!-- frob:describes src/frob/strata/_code_binding.py::check_import_conformance -->
<!-- frob:describes src/frob/strata/_code_binding.py::CodeBinding -->
<!-- frob:describes src/frob/strata/_code_binding.py::ConformanceReport -->
<!-- frob:describes src/frob/strata/_code_binding.py::ImportViolation -->

The surface grammar's `code glob+` comp_item (`comp_item` above) is not
yet lexed by `strata-core/src/parse.rs` -- v0 binds code the same way
`skew`/`fanout`/`growth` desugar (`kernel.md#capacity-semantics`): a node
declares one or more `code=<glob>` attrs directly in the kernel model
(Python API today; a first-class `code` keyword is a parser follow-up,
not a kernel change, since the fact stays an opaque node attr either
way). `bind_code` glob-matches every `.py` file under a scan root against
every node's `code=` attrs:

- A file matched by exactly one node's glob is bound to that node.
- A file matched by zero nodes is `FOREIGN` (charter law 2: "unclassified
  code is foreign by default").
- A file matched by more than one node's glob is `StrataError.
  AmbiguousCodeBinding` -- ownership must partition the tree, since
  two-way binding (law 5) needs exactly one node to attest for any given
  file.

`check_import_conformance` then walks every bound file's python imports
(stdlib `ast`, so line numbers are exact, including relative imports --
see below) and resolves each specifier to an in-repo file via
`frob.lang.resolve_local_import`; unresolved specifiers (third-party,
stdlib) are not tracked -- only in-repo crossings are a design concern.

**Direction is exact, not either-way (normative, T-0078 review round).**
`Flow` is a DIRECTED primitive (`kernel.md`'s primitive table: "Flow --
directed movement between two nodes"); a declared `Flow(src=A, dst=B)`
authorizes an import from A's bound code into B's bound code and NOTHING
else -- it does not also authorize a B -> A import, exactly as it would
not license a B -> A data flow. Charter law 2 ("undeclared flows are
forbidden") is enforced per direction, not per unordered pair: an import
whose (importer's owner, imported file's owner) pair, IN THAT ORDER, has
no matching `(Flow.src, Flow.dst)` in the `KernelModel` is an
`ImportViolation` (`file`, `line`, `spec`, `src_component`,
`dst_component`) -- "undeclared cross-component import" (this ticket's
one-line spec). An earlier draft of this module authorized either
direction from one declared `Flow` (justified, incorrectly, by charter law
5 -- which is about the two-way *conformance join*, design constrains code
and code attests design, not about one edge licensing both directions of
traffic); that was a REJECT-worthy soundness hole, fixed before this
ticket closed. A future revision MAY relax this if a bidirectional
channel construct is ever added to the surface grammar (RPC request/reply,
say) -- that would be a new kernel-model shape, recorded here when it
lands, not a silent default.

This is the tier-2 half of `kernel.md`'s `frame(op)` / soundness-
boundaries note that "tier-2 joins code-derived facts (imports, effects,
directives from the frob graph)". It is reflexion-model conformance
(declared architecture vs. as-built dependency graph): the kernel model
is the "declared" side, `bind_code` + real imports are the "as-built"
side, and `check_import_conformance` is the join.

**Relative imports resolve to their absolute in-repo equivalent.**
`from . import x` and `from ..pkg import y` (`ast.ImportFrom.level >= 1`)
are the dominant intra-package import style, including strata's own
source tree, and are resolved against the importing file's own package
position (standard python relative-import semantics: level 1 is the
importing file's own package; each further level walks up one more
directory) rather than skipped. `from . import x[, y]` (no `module`)
treats each imported name as a candidate submodule of the target package,
mirroring python's own name-resolution order; a name that is not actually
a submodule (a plain attribute import) simply fails to resolve in-repo
downstream (`resolve_local_import` returns None) and is not tracked,
consistent with third-party/stdlib specifiers.

**Not yet wired / v0 scope cuts (explicit, not oversights):**

- `frob check` SYS-gate surfacing of `ConformanceReport` (T-0080's SYS
  gate family).
- Non-Python languages: C/C++ `#include` resolution already exists in
  `frob.lang.resolve_local_import`, but v0 only reads import lines for
  python via `ast`, since a general per-language "import statement -> line
  number" walk lives in `frob.lang` and is out of this ticket's scope.
- `FOREIGN -> bound` imports (a file matched by no node's `code=` glob
  importing a file that IS bound to a node) are not checked: the outer
  walk in `check_import_conformance` only iterates over bound (non-
  `FOREIGN`) files, so an unclassified script importing into a component
  is silent today. Rationale for the cut, not an oversight: `FOREIGN`
  names no kernel node, so there is no `Flow.src` id to require a
  declaration against, and "every unclassified file in the repo" is a much
  larger and noisier surface than "every declared component's own code" --
  the same asymmetry the surface grammar's `managed` marker already
  encodes (nodes opt out of tier-2 conformance explicitly; unclassified
  code was never opted in). A future revision could still flag these as a
  softer "undeclared foreign dependency" diagnostic once `FOREIGN` also
  attaches to a synthetic node id in `bind_code`'s output.

<a id="directives-t-0080"></a>
## Directives: frob:channel / frob:boundary / frob:secret (T-0080)

<!-- frob:ticket T-0080 -->
<!-- frob:describes src/frob/strata/_design_load.py::load_design_ids -->
<!-- frob:describes src/frob/strata/_design_load.py::DesignIds -->
<!-- frob:describes src/frob/strata/_design_load.py::DesignLoadError -->
<!-- frob:describes src/frob/strata/_design_load.py::DEFAULT_DESIGN_DIR -->
<!-- frob:describes src/frob/gates/__init__.py::sys_gate -->

Three `frob:` comment directives (`frob.graph.dsl`'s verb table) bind a
code symbol to a design construct id, the same shape as `frob:ticket`/
`frob:invariant` binding code to a ticket/invariant id:

- `frob:channel <flow-id>` -- the enclosing symbol implements (sends or
  receives on) the named `Flow`.
- `frob:boundary <boundary-id>` -- the enclosing symbol enforces the named
  `Boundary`'s endorse/declassify contract.
- `frob:secret <node-id>` -- the enclosing symbol handles the named
  Secret-clearance `Node`'s cache-of-authority. The kernel has no
  dedicated secret construct yet (`std.secrets` is T-0082 future work), so
  a node whose elaborated `clearance == "Secret"` is the standing proxy
  for "this id names a secret" until `std.secrets` lands.

`frob.gates.sys_gate` (opt-in: runs only when a `design/`, or
`[strata].design_dir`, directory of `.strata` files exists, same posture
as `decisions_gate`) loads every non-excluded file under that directory
via `frob.strata.load_design_ids` -- parse (`parse_module`) + elaborate
(`elaborate`) each file, then merge every `Flow.id`, `Boundary.id`, and
Secret-clearance `Node.id` into one id surface -- and checks four rules.
`load_design_ids` walks through `frob.excludes.load_exclude_globs`/
`is_excluded` exactly as `frob.graph._walk_source_files` does (T-0080
REJECT round 1: an earlier version rglobbed `design_dir` directly, so a
repo's own `[graph].exclude`-d example models -- e.g. `design/litmus/**`,
excluded by T-0130 precisely so they carry no obligations -- re-acquired
SYS002 obligations anyway; a file-walking surface that does not consult
`frob.excludes` is exactly the desync that module exists to prevent).

- **SYS001** (error): a `frob:channel/boundary/secret` directive names an
  id absent from that merged surface -- a dangling reference, same
  severity posture as DRIFT002's dangling edge endpoint. Suppressed for
  the whole run whenever any `.strata` file failed to load (see SYS004):
  ids are merged across every design file with no per-file provenance, so
  a failed sibling's would-be ids are indistinguishable from a genuinely
  dangling reference (reviewer-caught, T-0080 REJECT round 1) -- SYS004
  alone reports the real problem until every design file loads clean.
- **SYS002** (warn): a `Boundary` or Secret-clearance `Node` in the model
  has no directive anywhere binding code to it. Channels (`Flow` ids) are
  deliberately NOT required to carry a binding: most flows are pure data
  movement with no single enforcing call site, whereas a boundary or
  secret is exactly the surface language's own "site of a security-
  relevant obligation" (`## Key construct semantics` above: boundary is
  "the only legal site of label/trust change"; secret is "cache-of-
  authority" with a mandatory revocation edge) -- the construct kinds a
  human reviewer would most want attested by real code, not just the
  model.
- **SYS003** (warn): tier-2 `bind_code` + `check_import_conformance`
  (`## Code binding (tier 2, v0 implementation)` above), run once per
  elaborated design model and surfaced as gate violations -- the "not yet
  wired" cut noted in that section is now closed. An ambiguous binding
  within one model is logged and skipped for that model only, never fatal
  to the whole gate. WARN, not ERROR, on landing (T-0080 REJECT round 1,
  severity item): every other gate in this family starts warn-first and is
  flipped to error only by a deliberate, tracked decision once a repo's
  design/code pairing has stabilized (COV001's history is the precedent).
  Tier-2 conformance is new and unproven at repo scale; the intended future
  state is `SYS003 = "error"` via `[gates.severity]` once a repo has run it
  clean for a while, not a default that can break a build on day one.
- **SYS004** (error): a `.strata` file under the design directory failed
  to parse or elaborate. Distinct from SYS001 on purpose -- a load failure
  and a dangling reference are different problems with different fixes
  (fix the design file vs. fix the directive), and collapsing them would
  misdirect whoever reads the message.

`frob:waive` can suppress any of these per the usual waiver-boundary rules
(`docs/modules/gates.md#waive-boundary`); all four rule ids are registered
in `frob.gates`' known-rule set so a waiver targeting them is never
flagged WAIVE002.

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
  owner, review. **Claim id (T-0138):** the claim-id position (only) also
  accepts a STRING-quoted id alongside the bare IDENT form, so a discharge
  claim naming a catalog obligation (`assert "weakness:CWE-79:web"
  noflow(...)`) can carry the `:`/`-` characters IDENT cannot lex; no
  other IDENT position in the grammar is loosened.
- `RefineDecl` <!-- frob:describes src/frob/strata/_ast.py::RefineDecl -->
  -- target, nodes, flows, bind_to; see "Refinement" above for v0 semantics.

**Capacity attrs (T-0066).** Three more flow/node properties desugar
straight to an `attrs` entry inside `parse.rs` itself, with no dedicated
AST or kernel field (charter law 1; docs/strata/kernel.md#capacity-
semantics):

- flow `fanout NUM` -> flow attr `fanout=<float>` (demand-propagation
  multiplier).
- flow `growth NUM %` -> flow attr `growth=<pct_per_month>` (compound
  monthly growth, read by UTILIZATION bound claims for saturation dating).
- node/store `skew zipf NUM` -> node/store attr `skew=<alpha>` (zipf
  hottest-shard exponent).

Because these are just more `attrs` entries, `FlowDecl`/`NodeDecl`/
`StoreDecl` need no new fields and `elaborate`/`elaborate_infra` need no
new mapping code -- `attrs` already passes through field-for-field.

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

queue   ID (":" TRUST)? "{" queue_prop* "}"?
queue_prop := "delivery" IDENT | "ordering" IDENT | "attr" ATTRVAL
            | "clearance" IDENT

cdn     ID "of" ID "{" cdn_prop* "}"?
cdn_prop := "provider" IDENT ":" TRUST | "staleness" (QUANTITY | "unlimited")
          | "hit" NUM "%" | "tls_terminates_at_provider"

balancer ID (":" TRUST)? "{" balancer_prop* "}"?
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
| `queue X [: T] { ... }` | `Node` X at trust T if declared, else `"trusted"` (see deviation below); `delivery=<x>`/`ordering=<x>` attrs; every outbound flow from X gains `delivery=<x>` |
| `cdn X of Y { ... }` | `Node` X at the declared provider's trust, Y's clearance; flow `X__fill` (Y -> X, age = staleness, or no age when `unlimited` over an `immutable` Y); `provider=<x>`/`hit=<v>` attrs; `tls_terminates_at_provider` adds boundary `X__declassify` (declassify, Y's clearance -> `Public`, predicate `"tls_terminates_at_provider"`) on `X__fill` |
| `balancer X [: T] { ... }` | `Node` X at trust T if declared, else `"trusted"`; `policy=<x>`/`sticky` attrs |

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

### Deviation: queue/balancer trust defaults to `"trusted"` when undeclared

`store`/`cache`/`cdn` have always had an explicit or inherited trust.
`queue` and `balancer` gained an *optional* `TRUST` clause in T-0093
(`queue X : T { ... }` / `balancer X : T { ... }`); when the clause is
omitted, `_infra.py::_elaborate_queue`/`_elaborate_balancer` still default
to `"trusted"`. This is a deliberate, documented default (not a silent
one) -- the clause is optional rather than mandatory so every pre-T-0093
`.strata` source keeps parsing and elaborating identically.

## std.deploy

<!-- frob:ticket T-0083 -->
<!-- frob:describes src/frob/strata/_deploy.py::evaluate_deploy_contracts -->
<!-- frob:describes src/frob/strata/_deploy.py::DeployContractReport -->
<!-- frob:describes src/frob/strata/_models.py::DeployContract -->
<!-- frob:describes src/frob/strata/_models.py::CanaryStage -->

A node's `on deploy { canary { ... }; endorsed_by X, Y; rollback within t }`
contract (T-0083) is, like `on crash` and `on breach`, pure sugar over the
kernel's existing scenario/rewrite machinery -- no new primitive, no new
prover code path. The kernel-level fields (`_models.py::DeployContract`,
`Node.deploy`) and the evaluator (`_deploy.py::evaluate_deploy_contracts`)
are load-bearing today; the surface grammar to write `on deploy { ... }`
in `.strata` source text is now implemented (T-0136, see the `node`
grammar section above) -- `parse_node`'s `on deploy` branch parses the
canary-stage list and endorsement-chain id list as comma-separated blocks
(neither needed STRING-quoting; `IDENT for quantity` and repeated `IDENT`
were sufficient), then `_elaborate.py::_elaborate_deploy` maps the parsed
`DeployDecl` onto `DeployContract`/`CanaryStage` field for field. `on
crash`/`on breach` remain unimplemented surface syntax -- this ticket's
scope was `on deploy` only.

Two joined validations, both failing closed (crash-contract precedent,
T-0074 -- a missing or incompatible bound is a model error, never a
silent pass):

- **Endorsement chain.** `endorsement_chain` names upstream `Boundary`
  ids (review/build/admit, docs/strata/boundary.md) an artifact must have
  already crossed. Every named id must exist (`MissingEndorsement`) and
  be `endorse`-directed (`IncompatibleEndorsement`) -- a `declassify`
  boundary, or no boundary at all, cannot stand in for the endorsement a
  deploy requires.
- **Canary levels.** Every `CanaryStage.level` must be a real level in
  the model's trust lattice (`Lattice.leq`'s existing `UnknownLevel`,
  reused rather than re-derived).

Once both pass, `evaluate_deploy_contracts` generates and evaluates two
kinds of auto-generated scenario via the existing `evaluate_scenarios`
(never a parallel evaluator):

- **Canary = staged trust escalation.** One `SetTrust` scenario per
  declared stage, in order (`<node>__canary_<index>_<level>`), re-checking
  every claim declared on the model exactly like a crash contract's
  auto-generated node-loss scenarios.
- **Rollback budget = bounded recovery scenario.** One `RemoveNode`
  scenario per deploying node (`<node>__rollback`) -- a rollback and a
  crash are both "this node's current state is gone, does the rest of
  the model still hold," so the same total-loss rewrite `on crash` uses
  is reused rather than a parallel rewrite kind. `rollback_budget` is a
  required `Quantity` field (pydantic-enforced at construction, mirroring
  `CrashContract.restart`); the kernel does not yet compare it against a
  measured recovery time (no live-metric feed into the prover in v0,
  the same limitation `CanaryStage.max_error_rate` and
  `Boundary.predicate` share) -- it documents the budget and gates the
  bounded-recovery scenario's existence.
