# Scenario kinds

<!-- frob:describes src/frob/strata/_scenarios.py::ScenarioResult -->

## What it is and where it lives

A `Scenario` is a named counterfactual rewrite of a strata model (node
loss, rate surge, trust downgrade) under which every claim is re-checked
(`docs/strata/kernel.md#scenario`). The rewrite variants are pydantic
models in `src/frob/strata/_models.py`'s `Rewrite` union: `RemoveNode`,
`ScaleRate`, `SetTrust`, `AddFlow`. Each rewrite kind has a matching `_apply_<kind>`
function in `src/frob/strata/_scenarios.py` (e.g. `_apply_remove`, which
cascades deletions and logs at INFO). Claim re-evaluation after a rewrite
is delegated to `_claims.py::evaluate_claims` -- `_scenarios.py` owns only
the rewrite step, never a parallel claim-checking path, so a scenario's
claims are proved/refuted/assumed identically to ordinary claims.

## Add-an-entry recipe (new rewrite kind)

1. Add the new rewrite's pydantic model to the `Rewrite` union in
   `src/frob/strata/_models.py` (frozen).
2. Add an `_apply_<kind>` function in `_scenarios.py` that takes
   `(model: KernelModel, rewrite: <Kind>) -> KernelModel` and returns the
   rewritten model -- never mutates the input (`KernelModel` is frozen).
3. Wire the new `_apply_<kind>` into the dispatch that walks a
   `Scenario.rewrites` tuple applying each in order.
4. Add surface grammar support in `strata-core/src/parse/grammar_policy.rs`
   (post-T-1006 split out of the old monolithic parse.rs/mod.rs) for the new
   rewrite's `.strata` syntax (see
   `docs/guides/extending/strata-surface-grammar.md`).
5. Add a litmus-style fixture pair or a direct `test_scenarios.py` case
   exercising the new rewrite against both a claim that should still hold
   and one that should now refute.
6. Document the new rewrite kind in `docs/strata/kernel.md#scenario`.

## Drift-locks that fire

- Same gap as prover claim kinds: no gate enforces "every `Rewrite` union
  member has an `_apply_<kind>` function" -- an unhandled rewrite variant
  fails at scenario-evaluation time, not at `frob check` time. Filed as a
  drafted follow-on (see `docs/guides/extending/README.md`).
- **TEST00x** applies normally to the new `_apply_<kind>` function and any
  new public model.
- **DOC001/DOC002** apply normally for the `frob:doc` edge into
  `docs/strata/kernel.md#scenario`.

## Worked example

`ScaleRate` (an existing rewrite, used as the worked example) required:
`_models.py` gained the frozen `ScaleRate` model (`flow_id`, `factor`);
`_scenarios.py` gained `_apply_scale`, which looks up the named
`Flow`, multiplies its declared `rate` by `factor`, and returns a new
`KernelModel` with that one `Flow` replaced (frozen-model "replace one
field" convention, `model_copy(update=...)`); LINT003 (design-lint-rules
guide) specifically requires any `Scenario` carrying a `ScaleRate` to nest
a `BoundClaim` targeting the scaled flow or either endpoint, so
`ScaleRate`'s addition also touched the lint guide's cross-reference.

## Common mistakes

- Mutating the passed-in `KernelModel` in place inside `_apply_<kind>`
  instead of returning a new one -- `KernelModel` fields are frozen
  pydantic tuples specifically so a scenario rewrite can never leak back
  into the base model other scenarios (or the un-rewritten claims pass)
  also evaluate against.
- Applying rewrites in an order-dependent way without documenting the
  order -- `Scenario.rewrites` is a tuple applied in declaration order;
  a rewrite kind whose effect depends on what has already been rewritten
  (e.g. `ScaleRate` on a flow a prior `RemoveNode` already deleted) must
  define what happens (skip vs. error) rather than leave it implicit.

## See also

- `docs/strata/kernel.md#scenario` -- scenario semantics and the charter
  citation ("Zone failure, load surge, and component compromise are one
  operation").
- `docs/guides/extending/prover-claim-kinds.md` -- the claim evaluation a
  scenario re-runs after rewriting.
- `docs/guides/extending/design-lint-rules.md` -- LINT003 specifically
  binds to `ScaleRate`.
