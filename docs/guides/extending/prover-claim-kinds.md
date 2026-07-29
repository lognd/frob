# Prover claim kinds

<!-- frob:describes src/frob/strata/_claims.py::evaluate_claims -->

## What it is and where it lives

A strata `Claim` is a typed assertion the prover proves, refutes, or
accepts as assumed. The claim variants live as pydantic models in
`src/frob/strata/_models.py`'s `ClaimBody` union (`NoFlow`, `Reach`,
`BoundClaim`, `Independent`, `SetEquality`; `Metric` is a StrEnum of
metric names and `Quantity` a value type, not claim variants
themselves), tagged with a `Quantifier`
(`Rung.L1`-`L5` evidence ladder, `docs/strata/evidence.md`). Dispatch lives
in `src/frob/strata/_claims.py::evaluate_claims`, which switches on the
claim variant and delegates to a `FactBase` closure query
(`_facts.py::build_facts`) -- claims never re-derive facts themselves.

## Add-an-entry recipe (new claim kind)

1. Add the new claim's pydantic model to the `ClaimBody` union in
   `src/frob/strata/_models.py` (frozen, `model_config = ConfigDict(frozen=True)`).
2. Add a dispatch arm in `evaluate_claims` that evaluates the new kind
   against the `FactBase`, returning a `ClaimResult` (verdict + witness on
   refutation -- charter law 4: never a vibe, always a witness path or
   number).
3. Add surface grammar support for the new claim shape in
   `strata-core/src/parse/grammar_policy.rs` (post-T-1006 split out of the
   old monolithic parse.rs/mod.rs; parser must accept the new claim's syntax)
   -- see `docs/guides/extending/strata-surface-grammar.md`.
4. Add fixtures under `tests/unit/strata/` exercising both a refuted and a
   proved case (mirrors the litmus vuln/hardened pairing convention, see
   `docs/guides/extending/litmus-fixtures.md`, even though claim-kind unit
   tests are not litmus fixtures themselves).
5. Document the new claim kind's semantics in
   `docs/strata/kernel.md#claim-forms-and-their-decision-procedures`.

## Drift-locks that fire

- No dedicated gate rule enforces "every claim kind has a dispatch arm" --
  `evaluate_claims` is a plain Python match/if-chain; a claim kind added to
  the model union but never dispatched fails at evaluation time with an
  unhandled-variant error (a runtime failure, not a `frob check` gate).
  This is a genuine coverage gap this ticket's inventory surfaced --
  see `docs/guides/extending/README.md` "Known gaps" and the filed ticket
  below.
- **TEST00x** (unit test gates) apply normally to any new public dispatch
  function or model added.
- **DOC001/DOC002** apply normally: the new model/function needs a
  `frob:doc` edge into `docs/strata/kernel.md`.

## Worked example

Adding `SetEquality` (an existing kind, used here as the worked example
since it is the newest claim variant with a clean paper trail) required:
`_models.py` gained the frozen `SetEquality` model; `_claims.py::
evaluate_claims` gained an `isinstance(claim, SetEquality)` arm computing
both sides' node sets from the `FactBase` and comparing; `_secrets.py::
elaborate_secret` was updated to auto-generate a `SetEquality` claim (the
"auto-instantiated obligation" pattern `_compliance.py` and `_pii.py` both
reuse); `docs/strata/kernel.md#claim-forms-and-their-decision-procedures` gained
a subsection.

## Common mistakes

- Forgetting the parser side (`strata-core/src/parse/grammar_policy.rs`): a claim kind
  that exists in the Python model but has no grammar production is
  unreachable from `.strata` source -- it can only ever be constructed by
  Python code (e.g. an auto-instantiated obligation), never authored
  directly. This is sometimes intentional (auto-instantiated-only claims)
  but must be a deliberate choice, not an oversight.
- Evaluating a claim kind against a `FactBase` query that does not exist
  yet and hand-rolling ad hoc graph traversal inside `_claims.py` instead
  of adding the query to `_facts.py::FactBase` -- this duplicates traversal
  logic that belongs in one place (the "closure is complete over the
  model" contract every other claim kind relies on).

## See also

- `docs/strata/kernel.md#claim-forms-and-their-decision-procedures` -- claim
  semantics and the verdict lattice.
- `docs/guides/extending/scenario-kinds.md` -- scenarios re-check the same
  claims under a rewritten model; a new claim kind is automatically
  scenario-compatible once `evaluate_claims` handles it, since
  `_scenarios.py` delegates back to the same function.
