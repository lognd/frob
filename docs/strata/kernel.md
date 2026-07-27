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
<!-- frob:describes src/frob/strata/_models.py::SetEquality -->
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

T-0972: `FactBase` (and its `aggregate_demand` method, docs/strata/
kernel.md#demand-declarations-t-0702 below) picked up `frob:ticket
T-0972` bindings for reasoned `frob:waive PERF003`/`PERF004` markers on
their own BFS-closure and per-node-set-formatting code -- no behavior
change.

- `FactBase.nodes_at` -- node ids at an exact trust level (deterministic
  order for reproducible counterexamples).
- `FactBase.reachable` -- the influence closure with witness paths; flows
  carrying a boundary stop taint (endorsement semantics) unless the
  caller asks to pass through barriers (positive `reach` claims do).
- `FactBase.worst_age` -- longest-path staleness accumulation in seconds;
  a positive-age cycle yields `inf` plus the cycle as witness, never a
  silent clamp.

  <!-- frob:invariant INV-028 -->
- `FactBase.demand` -- propagated inbound demand sum in base units
  (fanout-multiplied; see "Capacity semantics" below).
- `FactBase.propagated_demand` -- the same, plus a witness path/cycle.

### Age propagation semantics

<!-- frob:ticket T-0065 -->

One age metric, one propagation rule, four surface words. Precisely:

`age(target) = max over every flow-path P ending at target of sum(hop_age(e)
for e in P)`, where `hop_age(e)` is the flow's declared `age` (0 when
undeclared); when a positive-age cycle can reach `target`, the max is
unbounded and `worst_age` returns `+inf` with the cycle as witness (never a
silent clamp -- see `strata-core` below). This single bound family is what
cache `ttl`/`staleness`, CDN staleness, store `rpo` (replication/durability
lag), and -- in phase 5 -- credential rotation all desugar to: each is one
more flow declaring an `age`, not a separate metric with its own procedure.
An `AGE` bound claim (`evaluate_claims`) refutes with the accumulated
worst-case path, exactly like any other longest-path witness.

`store`'s `rpo NUM UNIT` property (docs/strata/surface.md#std-infra)
declares that store's own durability/replication lag; `_infra.py` folds it
into a `rpo=<seconds>` attr on the store's node (dimension-checked: a
non-time unit is `UnitMismatch`, fails closed). `rpo` does not itself
create a flow -- a store only participates in the age closure through
flows that already carry it. The pattern for a replica is to declare the
replication flow's own `age` directly:

```
store primary : trusted { rpo 5 min; }
store replica : trusted
flow repl : primary -> replica { age 5 min; }
assert bound age(replica) <= 10 min
```

Here `age(replica)` walks the single hop `repl` (5 min) -- the same
longest-path accumulation a cache's `ttl` or a CDN's `staleness` flow
produces; a design with a chain of replicas or a cache in front of a
replica composes for free, because the kernel never learns the words
"replica" or "cache", only flow ages (charter law 1).

**Non-negativity precondition (T-0065 reviewer round).** Every flow
age/rate/size must be `>= 0`; `_facts.py::build_facts` fails closed with
`StrataError.NegativeQuantity` otherwise (ERROR-logged). The surface
grammar cannot express a negative quantity, but the Python API can, so
this is enforced explicitly rather than assumed. Non-negativity is what
makes the `strata-core` algorithm below sound: it is the premise of the
"any intra-SCC edge lies on a cycle, so a positive edge makes that cycle
positive" argument -- with negative weights allowed, an edge could sit on
a cycle without making the cycle's *total* positive, and a positive-weight
edge inside an SCC would no longer guarantee unboundedness.

`strata-core`'s `worst_age` computes this via SCC condensation, not a
naive memoized DFS: with non-negative weights, (1) a pre-pass finds any
positive-weight cycle able to reach `target` and returns `+inf` with the
cycle as witness; (2) otherwise every intra-SCC edge among nodes that can
reach `target` is provably 0-weight, so condensing each SCC to one
supernode and running longest-path DP over the resulting DAG (topological
order) is exact. An earlier memoized-DFS version was rejected in review:
`best[node]` computed while a caller was mid-recursion (with that caller's
node on the "active" stack) got cached and wrongly reused by a *different*
caller with a different active set, silently undercounting the true
longest path -- the kind of bug that can make an `AGE bound claim <= v`
FALSELY PROVED. The counterexample (kept as a permanent regression, cargo
`worst_age_reviewer_regression_context_dependent_memo` and pytest
`TestReviewerRegression::test_context_dependent_memo_undercount`):

```
edges: B->A(0), B->T(0), A->T(3), A->B(0), C->B(1)   target: T
memoized-DFS (WRONG):  3.0  via A->T
SCC condensation (RIGHT): 4.0  via C->B->A->T
```

### Capacity semantics

<!-- frob:ticket T-0066 -->
<!-- frob:describes src/frob/strata/_facts.py::FactBase.propagated_demand -->
<!-- frob:describes src/frob/strata/_facts.py::_flow_fanout -->
<!-- frob:describes src/frob/strata/_claims.py::_node_skew -->
<!-- frob:describes src/frob/strata/_claims.py::_zipf_hottest_share -->
<!-- frob:describes src/frob/strata/_claims.py::_flow_growth -->
<!-- frob:describes src/frob/strata/_claims.py::_add_months -->
<!-- frob:describes src/frob/strata/_claims.py::_months_to_saturation -->
<!-- frob:describes strata-core/src/lib.rs::propagated_demand -->

Three surface words extend capacity arithmetic beyond the plain demand sum
without adding a kernel field (charter law 1): flow `fanout NUM`, node/store
`skew zipf NUM`, and flow `growth NUM %`. Each desugars straight to an attr
string at parse time (`fanout=<float>`, `skew=<alpha>`, `growth=<pct>`) --
`_facts.py`/`_claims.py` read them back out of `Flow.attrs`/`Node.attrs`.

**Demand propagation (sum over paths, not max).** `age` is a longest-path
(max) problem because staleness on a read path does not add across
alternate routes; demand is the opposite -- load converging from multiple
paths ADDS. `propagated_demand(target)`:

```
demand(n) = sum over inbound flows f of n of
              (f.rate if declared else demand(f.src)) * fanout(f)
```

A flow's own declared `rate` terminates recursion on that hop (it does not
also pull in its source's demand); an undeclared flow propagates the
source's own demand, scaled by `fanout` (default 1.0 when not declared).
`FactBase.demand` stays the metric RATE/UTILIZATION bounds read; it is now
a thin wrapper over `FactBase.propagated_demand`, which also returns a
witness.

**Unresolvable rate: propagates, does not drop.** A flow can declare a
`rate` that fails to resolve to a base value -- `Quantity.base_value()`
returns `Err` (e.g. an unknown unit). `FactBase.propagated_demand` treats
that hop exactly like a flow with no `rate` declared at all: it recurses
into the source's own propagated demand instead of contributing 0 or the
unresolvable number. This is a deliberate behavior shift (T-0066): an
earlier version silently dropped such flows from the demand sum, which
undercounts load through a model with a unit typo. The current rule fails
toward overcounting (propagating) rather than undercounting (dropping),
consistent with deny-by-default (charter law 2) -- a REFUTED verdict from
an inflated demand is recoverable (fix the unit, or the claim), a PROVED
verdict from a silently dropped flow is not. See
`tests/unit/strata/test_capacity.py::TestPropagatedDemand::test_unresolvable_rate_propagates_upstream_demand`
for the pinned example.

**Cycle rule (v0, deliberately conservative).** A cycle of *undeclared-rate*
flows is only a problem if something actually feeds it: `propagated_demand`
treats a cycle as `+inf` (with the cycle as witness) exactly when it is
reachable, forward, from some node with a declared outbound rate (a "rate
source") and the cycle also reaches `target`. An isolated cycle with no
source feeding it contributes 0 forever, not `+inf` -- it is inert, not
unbounded. This is the "honest v0 rule" from the ticket: it does not try to
multiply out fanout products around the cycle to distinguish a
sub-unity-gain loop (which would actually converge to a finite geometric
sum) from a growing one; ANY rate-fed cycle reaching the target is `+inf`,
deny-by-default (charter law 2). A future revision may compute the true
per-cycle fanout product and only flag `+inf` when it exceeds 1.0; until
then this is intentionally conservative, not incomplete.

**Zipf hottest-shard utilization.** A node marked `skew zipf ALPHA` is a
sharded resource where load is not evenly spread across its
`capacity.replicas_max` shards. The UTILIZATION bound then checks the
*hottest* shard's estimate, not the mean:

```
H(k, alpha)   = 1 / k^alpha
hottest_share = H(1, alpha) / sum_{k=1..replicas_max} H(k, alpha)
utilization_hot = 100 * demand(target) * hottest_share / service_rate
```

`service_rate` here is the *single-replica* rate (no `* replicas_max`,
unlike the unskewed ceiling) -- the hottest shard is served by exactly one
replica no matter how many total replicas exist. `alpha=0` degenerates to
an even split (`hottest_share = 1/replicas_max`, matching the unskewed
mean check); larger `alpha` concentrates load harder on rank 1. A
REFUTED verdict's detail always names the hottest-shard share and the zipf
exponent, never just a bare percentage, so the counterexample is
self-explanatory without re-deriving the formula. A node with no `skew`
attr keeps the original mean-based ceiling check (`demand / (rate *
replicas_max)`) unchanged.

**Growth horizons (saturation dating, not a new claim form).** Charter law
1 forbids a new claim kind for this, so growth-awareness lives inside the
existing UTILIZATION bound: when any flow feeding the target declares
`growth NUM %` (the largest declared growth percent among the target's
direct inbound flows, if more than one), a verdict that would otherwise be
PROVED is re-checked against compound monthly growth. Utilization at month
`t` is `utilization0 * (1 + growth/100)^t`; the saturation date is the
smallest `t` where that crosses `limit`. `GROWTH_HORIZON_MONTHS = 24`
(`_claims.py`, module-level constant) is the deny-by-default horizon: if
saturation falls within 24 months of `evaluate_claims`'s `today`, the
verdict flips from PROVED to REFUTED with detail `"saturates in N months
(YYYY-MM)"` -- a design that is fine today but will structurally fail
within two years is not a passing claim. No growth declared, or a
horizon beyond 24 months, leaves the verdict PROVED untouched.

### Demand declarations (T-0702)

<!-- frob:ticket T-0702 -->
<!-- frob:describes src/frob/strata/_facts.py::FactBase.aggregate_demand -->
<!-- frob:describes src/frob/strata/_facts.py::AggregateDemand -->

T-0972: `aggregate_demand`'s own BFS closure over incoming flows picked
up a reasoned `frob:waive PERF003` (one pass over incoming edges, not a
cross join) -- no behavior change.

The capacity-semantics propagation above (`propagated_demand`) sums demand
along flows whose OWN `rate` is declared -- but nothing in the model says
WHERE that load originates. A single `exclusive` lock (docs/strata/host.md
#resource-access-modes-t-0700) behind 500k concurrent users and the same
lock behind zero users are structurally identical without a notion of
entry-point LOAD -- this is the starvation-semantics prerequisite T-0700's
resource/access grammar needed.

Two new node/store clauses (T-0261 symmetry) declare entry demand:

- **`users NUMBER`** -- a steady population reaching this node (e.g. a
  concurrent-session count). A bare number, no unit (a headcount is
  dimensionless).
- **`rate NUMBER UNIT`** -- an arrival rate (same `QUANTITY` shape flow's
  own `rate` clause and `capacity`'s nested rate use, e.g. `rate 500
  req/s`). Top-level on node/store and independent of `capacity`'s own
  nested rate quantity (that's the node's own SERVICE ability; this is
  INBOUND load reaching it) -- the two do not collide syntactically since
  `capacity`'s rate is consumed immediately after the `capacity` keyword,
  never as a bare top-level clause.

A node may declare either, both (composing ADDITIVELY -- `users + rate`'s
base value, not exclusively), or neither. Elaborated straight onto
`Node.users: float | None` / `Node.rate: Quantity | None` (real kernel
fields, not an attr string -- `capacity`'s own precedent: numeric facts
consumed in arithmetic are typed fields, not opaque attrs).

**Propagation: `FactBase.aggregate_demand(node_id) -> AggregateDemand`.**
Reuses `propagated_demand`'s existing fanout-aware summation engine
UNCHANGED (no `strata-core/src/lib.rs` change) by seeding it with a
synthetic external-source flow per demand-declaring node (`__demand_
seed__<id>` from a synthetic `__demand_source__<id>`, declared rate =
`users + rate.base_value()`) alongside the model's real flows, then
calling `strata_core.propagated_demand` exactly as `FactBase.
propagated_demand` does. Demand SUMS at fan-in the same way flow-rate
demand already does (two entry nodes declaring `users 300000` and `users
200000` both flowing into one resource: aggregate demand at that resource
is `500000.0`).

**UNDECLARED is not the same as zero.** `AggregateDemand.declared: bool`
distinguishes "no `users`/`rate`-declaring node's demand reaches this
node at all" (`declared=False, value=0.0`) from a genuinely computed sum
(`declared=True`, even when that sum happens to be `0.0`) -- computed via
a plain reverse-BFS ancestor check over the same edges fed to
`propagated_demand`, not by comparing the result to `0.0` (which would
make a real declared-zero indistinguishable from "nothing declared at
all"). A resource with no demand-declaring node anywhere upstream reports
`demand-undeclared`, never a silent `0`.

Consumers (serialization-point utilization / writer-starvation / unbounded-
wait obligations over this demand, and the optional `capacity`/`holds`
hints on resources and arbiters this ticket's body mentions) are a
separate, sibling ticket -- this page documents the grammar and
propagation primitive only.

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

## Scenario

<!-- frob:describes src/frob/strata/_ast.py::RemoveDecl -->
<!-- frob:describes src/frob/strata/_ast.py::ScaleDecl -->
<!-- frob:describes src/frob/strata/_ast.py::TrustDecl -->
<!-- frob:describes src/frob/strata/_ast.py::ScenarioDecl -->
<!-- frob:describes src/frob/strata/_scenarios.py::ScenarioResult -->
<!-- frob:describes src/frob/strata/_scenarios.py::evaluate_scenarios -->

A scenario (T-0073) is a named counterfactual rewrite of the model: the
surface grammar is `scenario ID { rewrite* claim* }`, where `rewrite` is
`remove IDENT` (node loss), `scale IDENT by NUM` (rate surge/retry storm),
or `trust IDENT := IDENT` (compromise/trust downgrade), and `claim` reuses
the ordinary `assert`/`assume` productions verbatim -- a scenario's nested
claims are the same claim vocabulary re-checked under the rewritten fact
base, not a separate language.

Elaboration (`_elaborate.py::_validate_scenarios`) fails closed exactly
like every other cross-declaration check: a rewrite naming an undeclared
node/flow is `UnknownReference`; a `trust` reassignment to a level absent
from the trust lattice is `UnknownLevel`. There is no silent no-op
rewrite.

`evaluate_scenarios` (`_scenarios.py`, T-0073) applies each scenario's
rewrites to a COPY of the elaborated `KernelModel` -- the input model is
never mutated -- then runs the existing `evaluate_claims` machinery over
the rewritten model with the scenario's own nested claims:

- `RemoveNode` deletes the node and cascades: every flow touching it (as
  src or dst) is also deleted, and every boundary attached to one of
  those flows is deleted with it. Each cascade deletion is logged at
  INFO so a scenario's blast radius is auditable from the log alone.
- `ScaleRate` multiplies the named flow's declared `rate` by `factor`. A
  flow with no declared rate is `UnratedFlow` -- deny by default; a
  surge on a rate nobody declared is meaningless, not a silent 0 x N.
- `SetTrust` reassigns a node's `trust` field to the (already
  lattice-validated) new level.

Result shape: one `ScenarioResult(scenario_id, results)` per scenario, in
declaration order, `results` being the same `tuple[ClaimResult, ...]`
`evaluate_claims` would produce for that scenario's claims alone -- a
scenario never silently drops a claim any more than the base model does.

## Verdict report

<!-- frob:describes src/frob/strata/_report.py::render_report -->
<!-- frob:describes src/frob/strata/_report.py::summarize -->

The human-facing report `frob sys audit` prints (later phases) and the
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
<!-- frob:describes strata-core/src/lib.rs::propagated_demand -->
<!-- frob:describes strata-core/src/lib.rs::strata_core -->

The independent Rust/PyO3 kernel crate (T-0071; charter D2/D3). Data-in/
data-out only -- flattened graph tuples in, witness paths and numbers out;
validation and vocabulary stay in Python.

- `reachable` -- deterministic BFS closure over lexicographically sorted
  out-edges; barrier flag per edge implements endorsement semantics. A
  5th `transitive` flag per edge (T-0282) marks a TERMINAL edge when
  `false`: its `dst` is discovered (one hop always succeeds) but never
  enqueued for further expansion, so it cannot become a middle link in a
  longer chain. Two Python-side flow attrs feed this flag
  (`_facts.py::_NON_TRANSITIVE_ATTRS`): `std.krb`'s non-transitive domain
  trusts (docs/strata/krb.md#domain-trust-lattice), the first consumer,
  and the general-purpose surface marker `flow ... { utility; }` (T-0226)
  for a utility/hub edge -- e.g. a shared logging import -- whose relaying
  is not itself a meaningful transitive link, so a real `noflow` claim can
  survive it without weakening the closure for any edge that is NOT
  explicitly marked.
- `worst_age` -- SCC-condensation longest-path DP; positive cycles return
  +inf plus the cycle witness.
- `demand` -- plain declared inbound-rate aggregation (superseded by
  `propagated_demand` for fanout-aware bounds; kept for its own tests).
- `propagated_demand` -- fanout-weighted demand SUMmed over converging
  paths (see "Capacity semantics" above); rate-fed cycles return +inf plus
  the cycle witness, mirroring `worst_age`'s deny-by-default shape.
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
