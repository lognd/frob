# strata kernel -- primitives, facts, claims, verdicts

<!-- frob:ticket T-0048 -->

One sentence: the kernel is the six-primitive fact language the prover
operates on; every surface construct elaborates to kernel facts, and the
prover never learns a domain word (law 1 in `charter.md`).

## The six primitives

| Primitive | Definition | Attributes |
|---|---|---|
| **Node** | a place that holds state or runs computation | id, trust level, clearance (max data label), capabilities (`may` set), capacity (service rate, replica range), residence (host/zone/region) |
| **Flow** | directed movement between two nodes | src, dst, payload label, rate, size, age, transport properties, condition (see below) |
| **Boundary** | the only legal site of label/trust change on a flow | direction (endorse/declassify), predicate, phase contract, obligations |
| **Bound** | numeric constraint | `metric(target) <= value`, metric in {age, rate, latency, size, utilization, cardinality, lag} with units |
| **Claim** | assert or assume | body (noflow / bound / reach / frame / set-equality), required rung, owner+expiry (assume only) |
| **Scenario** | model rewrite | rewrite ops (remove node, scale rate, reassign trust), nested claims |

Kernel types are frozen pydantic models (T-0055); the fact base is a tuple
store with a semi-naive Datalog fixpoint over it (T-0056).

## Conditional flows (the one extension beyond plain graphs)

A flow may carry a condition: an outcome (`on Ok`, `on Err`) or a phase
(`in parse`, `in commit`). Frames desugar to conditional flow permissions:
"modifies X on Ok, nothing on Err" is two permission sets over write-flows
to stores. Boundary phases (`boundary.md`) and failure atomicity both
reduce to this; no other kernel extension exists or is planned.

## Lattice semantics

Two lattices (trust for nodes, labels for payloads), both user-extensible
partial orders with the built-in cores `foreign < authenticated < trusted`
and `Public < Internal < Pii < Secret`. Rules the closure enforces:

- A payload may rest at a node only if `label <= clearance(node)`.
- A flow crossing trust levels must pass through a boundary; endorse moves
  the flow's effective trust up (with predicate + obligations), declassify
  moves its label down (with justification + obligations).
- A flow over a link with observers at trust T carrying label above what T
  may read is a flow to those observers unless transport encryption is
  declared; metadata (size, timing) leakage always generates a residual
  assumption unless shaping is declared.

## Claim forms and their decision procedures

| Form | Meaning | Procedure |
|---|---|---|
| `noflow(A -> B)` | no path in the taint/reach closure | Datalog fixpoint; complete over the model; REFUTED yields the path |
| `bound(metric(x) <= v)` | propagated quantity respects v | interval/unit arithmetic along paths (age accumulates, rates multiply by fanout and skew, latencies sum); z3 only for nonlinear cases |
| `reach(A -> B)` | a required path exists (e.g. audit, revocation) | same closure, positive polarity |
| `frame(op)` | writes within declared frame per outcome/phase | conditional-flow conformance (tier 2 joins code effects) |
| `readers(x) == S` | exact-set closure equality | closure + set compare; used by std.secrets |
| `independent(p, n)` | path p shares no node with n | closure over path support sets; recovery-path independence |

Verdicts: `PROVED` (checker, forall over the model), `EVIDENCED` (bound
artifact at some ladder rung, see `evidence.md`), `ASSUMED` (ledger entry),
`REFUTED` (with counterexample path or number). Every verdict records its
quantifier. Scenario claims re-run the same procedures on the rewritten
fact base.

## Soundness boundaries (what "complete over the model" means)

Tier-1 closure is sound and complete over declared facts. Tier-2 joins
code-derived facts (imports, effects, directives from the frob graph);
soundness there is conditional on the `std.policy.analyzable` pack, and
that dependency is tracked explicitly: policies declare `enables`, and
waiving one downgrades every dependent PROVED verdict to ASSUMED
automatically (`evidence.md`). Tier-3 evidence (tests, perf stamps, tool
attestations) is digest-stamped and drift-checked like every frob
artifact.

## Data models

<!-- frob:describes src/frob/strata/_errors.py::StrataError -->
<!-- frob:describes src/frob/strata/_models.py::Lattice -->
<!-- frob:describes src/frob/strata/_models.py::Quantity -->
<!-- frob:describes src/frob/strata/_models.py::Capacity -->
<!-- frob:describes src/frob/strata/_models.py::Node -->
<!-- frob:describes src/frob/strata/_models.py::Outcome -->
<!-- frob:describes src/frob/strata/_models.py::FlowCondition -->
<!-- frob:describes src/frob/strata/_models.py::Flow -->
<!-- frob:describes src/frob/strata/_models.py::BoundaryDirection -->
<!-- frob:describes src/frob/strata/_models.py::Boundary -->
<!-- frob:describes src/frob/strata/_models.py::Metric -->
<!-- frob:describes src/frob/strata/_models.py::NoFlow -->
<!-- frob:describes src/frob/strata/_models.py::Reach -->
<!-- frob:describes src/frob/strata/_models.py::BoundClaim -->
<!-- frob:describes src/frob/strata/_models.py::Rung -->
<!-- frob:describes src/frob/strata/_models.py::Claim -->
<!-- frob:describes src/frob/strata/_models.py::RemoveNode -->
<!-- frob:describes src/frob/strata/_models.py::ScaleRate -->
<!-- frob:describes src/frob/strata/_models.py::SetTrust -->
<!-- frob:describes src/frob/strata/_models.py::Scenario -->
<!-- frob:describes src/frob/strata/_models.py::KernelModel -->
<!-- frob:describes src/frob/strata/_models.py::Verdict -->
<!-- frob:describes src/frob/strata/_models.py::Quantifier -->
<!-- frob:describes src/frob/strata/_models.py::ClaimResult -->

Frozen pydantic models (T-0055), identity-of-value like `frob.lang`:

- `StrataError` -- the one closed ErrorSet; its enumerability is what makes
  fault injection exhaustive (`evidence.md`).
- `Lattice` (+ `TRUST`, `LABELS` built-in cores) -- finite partial orders
  from covering pairs; `leq` errors on unknown levels rather than
  silently denying.
- `Quantity` -- number + unit; cross-dimension comparison is an error.
- `Node`, `Capacity` -- places with trust, clearance, `may` capability
  atoms, opaque attrs, service rate/replicas, residence.
- `Flow`, `FlowCondition`, `Outcome` -- edges with payload label, rate,
  per-hop age, size, transport atoms, attrs, and the conditional-flow
  extension.
- `Boundary`, `BoundaryDirection` -- endorse/declassify on exactly one
  flow, with predicate + obligations.
- `Claim` bodies `NoFlow`/`Reach`/`BoundClaim` (+ `Metric`), the `Rung`
  ladder, and `assumed` with owner/review.
- `Scenario` + rewrites `RemoveNode`/`ScaleRate`/`SetTrust`.
- `KernelModel` -- the whole elaborated design.
- `ClaimResult`, `Verdict`, `Quantifier` -- how claims close (laws 3-4).

## Fact base

<!-- frob:describes src/frob/strata/_facts.py::build_facts -->
<!-- frob:describes src/frob/strata/_facts.py::FactBase -->
<!-- frob:describes src/frob/strata/_facts.py::FactBase.nodes_at -->
<!-- frob:describes src/frob/strata/_facts.py::FactBase.reachable -->
<!-- frob:describes src/frob/strata/_facts.py::FactBase.worst_age -->
<!-- frob:describes src/frob/strata/_facts.py::FactBase.demand -->

The tier-1 engine (T-0056). `build_facts` fails closed on structural
errors (duplicate ids, dangling references, unknown lattice levels,
cyclic lattices) and records non-fatal deny-by-default findings as
`FactBase.diagnostics` (at-least-once delivery into a non-idempotent
consumer; payload label above destination clearance).

- `FactBase.nodes_at` -- node ids at an exact trust level (deterministic
  order for reproducible counterexamples).
- `FactBase.reachable` -- the influence closure with witness paths; flows
  carrying a boundary stop taint (endorsement semantics) unless the
  caller asks to pass through barriers (positive `reach` claims do).
- `FactBase.worst_age` -- longest-path staleness accumulation in seconds;
  a positive-age cycle yields `inf` plus the cycle as witness, never a
  silent clamp.
- `FactBase.demand` -- declared inbound rate sum in base units.

## Claim evaluation

<!-- frob:describes src/frob/strata/_claims.py::evaluate_claims -->

`evaluate_claims` (T-0057) walks the model's claims in declaration order
and returns exactly one `ClaimResult` per claim -- a report can never
silently drop one. Semantics as implemented in phase 0:

- `noflow` -- REFUTED with the first witness path through the barrier-
  respecting closure; PROVED forall otherwise. Endpoints may be node ids
  or trust levels (expanded to every node at that level); anything else
  fails the whole evaluation closed.
- `reach` -- PROVED carries quantifier EXISTS and its witness path; the
  refutation of an exists is a forall ("no path"), tagged accordingly.
- `bound` -- AGE compares `worst_age` against a time limit (a positive-age
  cycle refutes as unbounded); RATE compares `demand`; UTILIZATION
  compares demand against `service_rate x replicas_max` with a percent
  limit, refusing nodes with no declared capacity (deny by default);
  SIZE compares a flow's declared size; LATENCY always refutes in phase 0
  because flows do not yet declare latency (path budgets arrive with the
  phase-2 surface `flow` construct). Wrong-dimension limits fail closed.
- `assume` -- closes ASSUMED with owner and review date in the detail;
  an overdue or malformed review date is flagged there for the phase-5
  gate to escalate.

## Verdict report

<!-- frob:describes src/frob/strata/_report.py::render_report -->
<!-- frob:describes src/frob/strata/_report.py::summarize -->

The human-facing report `frob sys check` prints (later phases) and the
machine-facing count summary, both over the flat `evaluate_claims` output.
Pure formatting only -- no new evaluation happens here.

- `render_report` -- one line per claim (verdict tag, id, quantifier,
  detail), an indented witness-path line under a refutation, a summary
  count line, then -- only when the run has an assume -- an
  `## Assumption ledger` section. Listing order is REFUTED first (most
  severe), then ASSUMED, then EVIDENCED, then PROVED, stable by claim_id
  within a group; law 3 (an assume never proves anything) demands a
  refutation can never hide behind proofs. `color=True` wraps tags with
  ANSI via `frob.logging.color`; default `False` keeps JSON/log output
  byte-stable.
- `summarize` -- per-`Verdict` counts as a plain dict, all four keys
  always present so a caller never has to guard a missing key.

Sample layout (`color=False`):

```
REFUTED  c1 [forall] -- influence path foreign -> db with no boundary
  path: evil -> api -> db
PROVED   c2 [forall] -- no unendorsed influence path exists
ASSUMED  c3 [forall] -- assumed by alice; review by 2026-08-01

3 claim(s): 1 proved, 1 refuted, 1 assumed, 0 evidenced

## Assumption ledger
  c3: assumed by alice; review by 2026-08-01
```

## strata-core

<!-- frob:describes strata-core/src/lib.rs::reachable -->
<!-- frob:describes strata-core/src/lib.rs::worst_age -->
<!-- frob:describes strata-core/src/lib.rs::demand -->
<!-- frob:describes strata-core/src/lib.rs::strata_core -->

The independent Rust/PyO3 kernel crate (T-0071; charter D2/D3). Data-in/
data-out only -- flattened graph tuples in, witness paths and numbers out;
validation and vocabulary stay in Python.

- `reachable` -- deterministic BFS closure over lexicographically sorted
  out-edges; barrier flag per edge implements endorsement semantics.
- `worst_age` -- memoized longest-path DFS; positive cycles return +inf
  plus the cycle witness.
- `demand` -- inbound-rate aggregation (grows fanout/skew in phase 2).
- `strata_core` -- the pymodule assembling the exported surface.

Build: `make core` (uvx maturin develop --release); ships a bundled
`.pyi` stub so ty sees typed signatures. Cargo tests run in CI beside
frob-core's.

## Prover pipeline

```
design/**/*.strata
   | parse        recursive descent -> pydantic AST (T-0059)
   v
elaborate         vocabularies desugar constructs -> kernel facts (T-0060)
   v
fact base         + frob graph facts (tier 2)  + evidence digests (tier 3)
   v
prove             lattice ops + Datalog fixpoint + interval arithmetic
   v
report            per-claim verdicts -> SYS gate violations with remedies
```

Performance (D3 as amended): the fixpoint and propagation kernels
(`reachable`, `worst_age`, `demand`) run in `strata-core`, the
independent Rust/PyO3 crate (T-0071) -- REQUIRED, no pure-Python
fallback; `make core` builds it into the venv alongside frob-core.
Python keeps validation, orchestration, and the pydantic interface, so
callers never see the boundary.
