# strata evidence ladder -- quantifiers, rungs, the enables cascade

<!-- frob:ticket T-0048 -->

One sentence: strata is proof-based, not test-based -- kernel claims are
for-all over the model, code-level obligations are discharged on a ladder
whose every rung records its quantifier, and an example test can never
silently stand in for a universal guarantee (law 4).

## The ladder

| Rung | Evidence | Quantifier | Examples |
|---|---|---|---|
| **L5 by-construction** | kernel proof over the model, or a host-language type embedding | forall, machine-checked | closure/arithmetic verdicts; a `TenantScopedSession` whose only constructor takes a tenant id; frozen models making parse purity structural |
| **L4 universal policy** | syntactic closure over every file in semantic scope | forall, syntactic | "no eval in trusted", "all writes via the tx handle", "every except arm logs or propagates" |
| **L3 leaf proof** | SMT/verifier on a small mediator or commit function | forall, bounded theory | z3 on the commit step; CrossHair/Kani/Prusti later |
| **L2 property test** | hypothesis / Arbitrary; includes generated fault injection | forall over sampled or enumerated domain | state-digest-unchanged under injected Err variants |
| **L1 example test** | a pytest case | exists | regression tripwires only |

Rules:

- Every claim declares `require proof >= Ln` or inherits a minimum rung
  from its criticality. Evidence weaker than the required rung fails the
  SYS gate.
- Every verdict records its quantifier; reports may never present
  exists-evidence as a guarantee.
- Dropping below the required rung is only possible via an `assume` --
  named, owned, expiring, reported.

## The semantic-to-syntactic reduction (the core strategy)

Rice's theorem forbids proving arbitrary semantic properties of arbitrary
code, so strata never tries. Instead the elaborator decomposes each
semantic for-all into obligations that are each universally checkable:
confinement makes the property syntactically local (L4), and the small
remaining mediator carries a real proof (L3/L5). Example: "all tenant
queries are scoped" (undecidable) becomes "only TenantScopedSession
touches the connection, everywhere" (L4 confinement) plus "its constructor
requires a tenant id" (L5 type embedding). The chokepoint policy form
(`policy.md`) is this reduction as one declarable construct.

## Exhaustive fault injection (L2 with teeth)

Because typani `ErrorSet`s are closed vocabularies, the fault space of an
operation is enumerable: for each fallible dependency, for each declared
Err variant, inject the failure and assert the observable-state digest is
unchanged. This is a bounded for-all that is complete over the declared
error model -- categorically stronger than sampled property testing -- and
the test skeletons are generated mechanically from `frame`/`atomic` claims
(T-0075).

## Tool attestations

Some L5/L4 evidence comes from external checkers rather than strata's own
machinery: ty's exhaustiveness for `errors total`, tsc's no-floating-
promises, rustc's must_use, cargo/clang stacks per language. These are a
distinct evidence source kind -- tool attestations -- digest-stamped like
coverage evidence (TEST006 pattern) so a silently-disabled checker cannot
keep discharging claims.

## The enables cascade (soundness dependencies, mechanized)

Some L4 policies are not hygiene but preconditions for other proofs:
import-closure conformance is meaningless if code can `eval`; detection
SLAs are meaningless if the error paths they watch stop logging. Policies
therefore declare what they `enable`:

```
policy NoDynamicCode on trust >= trusted {
  forbid call eval, exec, importlib.import_module
  enables extraction_soundness
}
```

The kernel tracks these edges. Waiving or weakening a policy automatically
downgrades every claim resting on it from PROVED to ASSUMED -- cascading
into the assumption ledger with owner and expiry. Exceptions remain
possible; silent exceptions do not. The mandatory `std.policy.analyzable`
pack (T-0068) is the root of most cascades: without it a component may not
claim `trusted` at all.

## The assumption ledger

`assume A-003 "RDS at-rest encryption covers disk theft" owner logan
review 2026-10-01`. Assumptions are the explicit trusted computing base:
auto-generated ones (host OS per `host`, crypto per `transport`, traffic
metadata per unshaped encrypted channel) plus hand-written ones. All are
listed in every report; an overdue review date is a gate failure. The
ledger is tracked text, diffable and reviewable, like every frob source of
truth.
