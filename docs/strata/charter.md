# strata -- charter

<!-- frob:ticket T-0048 -->

One sentence: strata is a deny-by-default system-design language, checked
like code, in which every claim about a system -- security, freshness,
capacity, deployment integrity, breach containment -- is a statement about
flows between nodes, constrained by lattices and numeric bounds, and every
claim is either proved by the checker, discharged by tracked evidence, or
held as a named, owned, expiring assumption. Nothing else is permitted to
exist.

This is the umbrella document for the strata effort (epic ticket T-0047).
Component designs:

- `docs/strata/kernel.md` -- the six primitives, conditional flows, claim
  semantics, verdicts
- `docs/strata/surface.md` -- the surface language: grammar, vocabularies,
  refinement hierarchy, module system
- `docs/strata/evidence.md` -- the evidence ladder L1-L5, quantifiers, the
  enables soundness cascade
- `docs/strata/policy.md` -- the five universal policy forms and policy
  packs
- `docs/strata/boundary.md` -- the six-phase boundary contract and
  outcome-conditioned frames (failure atomicity)
- `docs/strata/roadmap.md` -- phases 0-5 with exit criteria, the litmus
  program, and the ticket map (T-0047..T-0086)

## Why strata exists

frob makes unaccounted-for *work* a build failure. strata extends the same
philosophy one level up: it makes unaccounted-for *architecture* a build
failure. Audit/fix cycles are there-exists reasoning (we looked and found
nothing); strata is for-all reasoning (no such path exists, and here is why,
or here is the counterexample). The tool that owns the obligation graph is
the only tool that can close the loop both ways: the design constrains the
code (an undeclared effect is a gate failure) and the code attests the
design (an unimplemented boundary is drift).

## The six laws

1. **One kernel, many vocabularies.** The prover knows exactly six
   primitives (see `kernel.md`). Every surface construct must desugar to
   them via the elaborator. If a proposed feature cannot desugar, either
   the feature is wrong or the kernel grows -- deliberately, recorded here,
   never by accident.
2. **Deny by default, at every layer.** The model starts with nothing
   permitted; declarations add permissions. Code not covered by any
   component's `code` glob is foreign. Undeclared flows are forbidden.
   Security-relevant properties have no defaults: an unstated transport on
   a cross-trust channel is an error, not an assumption.
3. **Three-way closure.** Every claim ends PROVED (checker), EVIDENCED
   (tracked, digest-stamped artifact), or ASSUMED (named, owned, expiring
   ledger entry). Overdue assumptions are gate failures. The trusted
   computing base is a reviewable ledger, never an unstated hope.
4. **Counterexamples always, quantifiers recorded.** Every failed claim
   yields a path or a number, never a score or a vibe. Every verdict
   carries its quantifier; exists-evidence (an example test) may never
   satisfy a forall-claim without an expiring assumption.
5. **Two-way binding.** Tier-2 conformance joins the model against the
   frob obligation graph in both directions: design constrains code, code
   attests design.
6. **The model is load-bearing.** The same declarations compile to runtime
   enforcement (network policy, seccomp, IAM) and generated documentation,
   so the model physically cannot rot into a diagram.

## The three collapses (why one kernel suffices)

- **Age.** Cache TTL, credential rotation, session expiry, replica
  staleness/RPO, certificate lifetime, and assumption review dates are one
  bound -- `age(x) <= t` -- applied to data, authority, and belief. A
  credential is a cache of an authorization decision: its lifetime is a
  TTL, its revocation path is the invalidation edge, and the rule "no
  cache without an invalidation edge" is the rule "no credential without a
  revocation path".
- **Endorsement.** Input validation, code review, build attestation,
  signature verification, and `frob vet`'s allowlist are one boundary
  form: something low-integrity crosses into high-integrity through a
  declared, obligated checkpoint. Payloads differ; the construct, proof,
  and gate are identical.
- **Scenario.** Zone failure, load surge, and component compromise are one
  operation: rewrite part of the model (remove a node, multiply a rate,
  downgrade a trust assignment), re-check every claim, report what breaks.
  Blast radius is reachability under the rewrite.

## Security model (normative)

Two orthogonal lattices, never merged:

- **Trust** (principals and code): `foreign < authenticated < trusted`,
  user-extensible.
- **Data labels** (information): `Public < Internal < Pii < Secret`,
  user-extensible.

Non-interference is expressed in one primitive, both directions:
integrity is `noflow(foreign -> state)`; confidentiality -- including
interception -- is `noflow(state -> foreign)`. A channel routed over a link
with foreign observers carrying data above Public is a flow to foreign
unless encrypted (AEAD, declared key management); even then size/timing
metadata still leaks, and the checker auto-generates a residual assumption
unless padding/shaping is declared. Trust changes happen only inside
declared boundaries: crossing up is endorsement, crossing down is
declassification, both with obligations.

## What is honestly not provable

Stated here and enforced as auto-generated or mandatory assumptions:
hardware and microarchitectural side channels; a compromised kernel (the
host OS is an assumption per `host`); correctness of cryptographic
implementations (assumed per `transport`/`proves` clause); and the static
extraction gap (reflection, `eval`, FFI) outside the analyzable subset --
which is why `std.policy.analyzable` is mandatory for `trusted` components
and why waiving it cascades (see `evidence.md`). A tool that claims more
than this is lying; strata states exactly this and tracks it.

## Decisions (all final unless superseded here)

| # | Decision |
|---|---|
| D1 | The language is named **strata**; files are `design/**/*.strata`; the CLI namespace is `frob sys` |
| D2 | strata is **completely independent of lithos**. It gets its own Rust/PyO3 crate, `strata-core/`, mirroring the frob-core maturin pattern. lithos may be read for inspiration; no code, crates, or schemas are shared |
| D3 | The engine lives in `src/frob/strata/` (parser, elaborator, prover, vocabularies); hot kernels move to `strata-core` when litmus models make pure Python slow, with no pure-Python fallback after adoption |
| D4 | Litmus models are tracked fixtures in `design/litmus/` with golden expected-findings files run in CI; they are the language's compiler test suite and documentation. In-repo until the language stabilizes, then possibly promoted |
| D5 | Phase order is 0..5 as in `roadmap.md`, strictly sequential at the phase level; scenarios land in phase 3, exporters in phase 5 |
| D6 | Per-repo `design/` directories; the std vocabulary ships with frob; a cross-repo design registry (one model spanning the sibling repos) is deferred until after phase 5, but the module system uses dotted paths so it extends without breakage |
| D7 | frob self-hosts: `design/frob.strata` declares frob's own architecture and frob gates on it (phase 4 exit criterion, T-0081). This work itself is tracked in frob tickets from day one (T-0047..T-0086) |
| D8 | Verdicts are quantifier-tagged; the minimum evidence rung per claim is declared or inherited from criticality; downgrades require an expiring assume |
| D9 | Boundaries are six-phase contracts with per-phase frames; frames are the kernel's only conditional-flow extension |
| D10 | `errors total` (recoverable errors are values, provably consumed) and `panics contained` (everything else provably reaches a declared crash boundary) are separate claims; no construct may blur them |

## Glossary (normative meanings; no synonyms in code or docs)

- **node** -- a place that holds state or runs computation (component,
  store, cache, host, principal, queue, vault, human).
- **flow** -- directed movement of anything (data, requests, code
  artifacts, credentials, log events) between nodes.
- **boundary** -- the only construct where a flow's label or trust may
  change.
- **bound** -- a numeric constraint `metric(x) <= value` (age, rate,
  latency, size, utilization, cardinality).
- **claim** -- an `assert` (must be proved/evidenced) or `assume` (owned,
  expiring TCB entry).
- **scenario** -- a counterfactual model rewrite under which claims are
  re-checked.
- **frame** -- the set of state a phase or operation may modify,
  conditioned on outcome (`on Ok` / `on Err`) or phase.
- **endorse / declassify** -- raise integrity / lower confidentiality of a
  flow, legal only inside a boundary.
- **refinement** -- decomposing an abstract component into concrete ones
  under faithfulness checks that preserve parent-level proofs.
- **vocabulary** -- an elaborator module (`std.trust`, `std.infra`, ...)
  that desugars surface constructs to kernel facts.
- **verdict** -- PROVED, EVIDENCED, ASSUMED, or REFUTED, plus a quantifier
  (forall/exists) and, for REFUTED, a counterexample.
