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

Performance: pure Python through phase 2; fixpoint and propagation kernels
move to `strata-core` (independent Rust/PyO3 crate, T-0071) when the
litmus models make them slow. No pure-Python fallback after adoption
(matches the frob-core decision).
