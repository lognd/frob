# strata obligation catalog -- CWE/CVE + quality capability auditing

<!-- frob:ticket T-0109 -->

One sentence: strata makes it impossible to silently forget a class of
protection -- security, performance, reliability, or compatibility -- by
treating every known anti-pattern as a conditional obligation that FIRES
when the model exhibits its precondition and is DISCHARGED only by a
declared, cited, evidenced mitigation, with a three-part exhaustiveness
proof that the whole cited catalog baseline is covered, every capability
is classified, and every fired obligation is resolved.

Security weaknesses (CWE) are the first and best-specified family, but the
machinery is family-agnostic: a performance anti-pattern (uncompressed
payload, one-at-a-time writes) is the same "precondition pattern -> required
mitigation -> citation -> evidence rung" shape as an injection weakness.
The rest of this doc leads with security because it is the sharpest case;
the anti-pattern-families section generalizes it.

Umbrella for the threat-audit workstream (epic T-0109). This is a strata
vocabulary + claim family + gate; it adds no kernel primitive (charter
law 1). It reuses the closure engine, boundaries, the policy forms, the
label lattice, the evidence ladder, and the assumption ledger already
built in phases 0-2.

## The core reframe

A CWE is not a checklist item. It is a **conditional obligation
predicated on a capability being present in the model**:

- CWE-79 (XSS) applies only if foreign data reaches an HTML-render sink.
- CWE-89 (SQL injection) only if foreign data reaches a query sink.
- CWE-78 (OS command injection) only if foreign data reaches an exec sink.
- CWE-22 (path traversal) only if foreign data reaches a filesystem-path sink.
- CWE-918 (SSRF) only if foreign data reaches a network-request target.
- CWE-502 (unsafe deserialization) only if foreign data reaches a deserializer.
- CWE-922/312 (insecure/cleartext storage) only if sensitive-labeled data
  reaches a low-clearance store (client storage, logs, cache).
- CWE-352 (CSRF) only if a state-changing endpoint accepts ambient-authority
  requests.
- CWE-798/256 (hardcoded/plaintext credentials) only if a Secret-labeled
  value rests in source or a low-clearance node.

The precondition is a **flow pattern** the closure engine already detects.
The mitigation is a **boundary** (endorsement: sanitize/encode/parameterize)
or a **policy chokepoint** already expressible. So:

> A weakness obligation fires when the model matches its precondition and
> is discharged only by a declared mitigation with evidence at or above
> its required rung. A matching flow with no mitigation is a REFUTED
> obligation -- a build failure. Forgetting has nowhere to hide.

Many CWEs need NO new detection -- they already fall out of existing
machinery. Secrets in `localStorage` is `Secret` data resting at a
`Public`-clearance node: a clearance violation the lattice already
refutes. The catalog's job is to NAME, CITE, and prove EXHAUSTIVE
COVERAGE of these, not to re-detect each.

<a id="the-catalog-stdcwe"></a>
## The catalog (`std.cwe`)

A versioned vocabulary pack shipped with strata, pinned to a MITRE CWE
release and an OWASP release (staleness past a review bound is a gate
warning, like an overdue assume). Each entry:

```
weakness CWE-79 "Improper Neutralization of Input During Web Page Generation" {
  cite  cwe "https://cwe.mitre.org/data/definitions/79.html"
  view  owasp-top-10 = A03:2021, cwe-top-25
  when  flow(from trust <= foreign, to sink html_render)
  needs mitigation output_encoding at judge
  rung  >= L4
}
```

Entries are grouped into cited baseline VIEWS (`cwe-top-25`,
`owasp-top-10`, `owasp-asvs`, `cwe-1000`). Selecting a view in `frob.toml`
declares the baseline the exhaustiveness proof is measured against.

## Capabilities drag in obligations

A capability is a power the system wields, declared on a node and
(phase 4) verified against extracted code effects:

```
component Web : trusted {
  capability html_render, sql, client_storage
  code src/web/**
}
```

Declaring a capability auto-instantiates its weakness obligations
(`html_render` -> CWE-79/116; `sql` -> CWE-89; `client_storage` ->
CWE-922/312; `exec` -> CWE-78; `deserialize` -> CWE-502; `fetch_url` ->
CWE-918). The deny-by-default kicker (phase 4, T-0079 effect extraction):
**using a capability in code without declaring it is an error**, and an
extracted sink the catalog's patterns do not recognize is an error --
so a new `localStorage.setItem`, SQL client, or template renderer cannot
enter the codebase without either matching a weakness obligation or being
explicitly declared benign with a reason.

## The exhaustiveness proof (the point)

"Completely exhaustive" is not "protected against all attacks" (open-
ended, unprovable). It is a conjunction of three for-alls over CLOSED
sets, each decidable:

1. **Catalog completeness** (THREAT001): every CWE in the selected
   baseline view has a `weakness` entry, or an explicit `out-of-scope
   CWE-### reason="..."` -- an unaddressed baseline CWE is an error.
2. **Precondition/capability completeness** (THREAT002): every capability
   and every extracted code sink is classified against the catalog; an
   unclassified sink is an error (it might hide an unmatched weakness).
   This is the "never forget" mechanism.
3. **Discharge completeness** (THREAT003): every FIRED weakness obligation
   is PROVED / EVIDENCED / ASSUMED at or above its required rung; a
   dangling or under-evidenced obligation is an error; assumptions carry
   owner + expiry.

The exhaustiveness claim is the conjunction, reported as a matrix
(`frob sys audit`): applicable weakness -> precondition present? ->
mitigation -> evidence rung -> citation. It means exactly: exhaustive
relative to the cited baseline, with every gap named, owned, and
expiring. DOC002 (the claims audit) binds prose: a README claiming
"protected against the OWASP Top 10" must cite a PROVED exhaustiveness
result or it fails CI.

## Beyond security: the anti-pattern families

A catalog entry has a `family` -- `security` (CWE-cited), `performance`,
`reliability`, `compatibility`, `compliance` (regulatory; see the
compliance section below). Every family shares the structure
(precondition pattern, required mitigation, citation/rationale, evidence
rung); only the precondition vocabulary and the mitigation form differ.
The exhaustiveness proof is computed PER FAMILY against a cited baseline,
so "exhaustive on the OWASP Top 10 and the web-performance baseline" is a
conjunction of independently-checkable claims. The concrete anti-patterns
requested, mapped to their preconditions and mitigations:

| Anti-pattern | Family | Precondition (fires when...) | Discharge |
|---|---|---|---|
| Misused dynamic ORM condition | security | foreign data influences a query predicate that controls row/authorization scope (CWE-89 / CWE-639) | the tenant/authz-scoping chokepoint (evidence.md) at L4 + the scoping type at L5 |
| Loose backend URL rules | security | a foreign flow reaches an endpoint with no declared route-authorization boundary (CWE-862/863); or a redirect target is foreign-influenced (CWE-601) | an authz boundary per endpoint; an allowlist mediation on redirect targets |
| Stored XSS | security | a two-hop flow: foreign data reaches a store, and a later read path carries it to an `html_render` sink (CWE-79 persistent) | output-encoding boundary on the render path -- a reachability query with the store in the middle |
| Wide-open CORS | security | an ingress boundary declares `cors origin any` while the endpoint carries credentials or authenticated data (CWE-942) | an explicit origin allowlist; wildcard + credentials is refused |
| Uncompressed JSON | performance | a flow's `size` exceeds a threshold, payload is structured, and transport declares no `compressed` (nor an encoding boundary) | declare compression on the transport, or an assume for tiny payloads |
| One-at-a-time DB writes | performance | an operation writes a collection (cardinality > 1) to a store via a per-item flow rather than a declared `batch` write | declare batch/bulk write semantics; per-item over a large cardinality refutes the throughput bound |
| Single-dependency bottleneck (audit round-trip) | reliability | a flow on a latency-budgeted critical path is `synchronous` through a single-replica or external node whose round-trip is in the budget sum | declare async/fire-and-forget, a cache, or a fallback; else the budget arithmetic (T-0066) already refutes |
| Un-optimistic rendering | performance | a render flow has a synchronous `waits_for` edge to a network response before it may emit | declare optimistic/async render (emit, then reconcile), moving the response off the render's critical path |
| Non-statically-hosted content | performance | `Public`, `immutable` content is served from a compute/origin node instead of a `cdn` (reuses the std.infra immutable/cdn machinery) | route the content flow through a declared `cdn`; dynamic serving of static-eligible content refutes |

Three of these (dynamic ORM scope, single-dependency latency, static
hosting) discharge with NO new detection -- they are the existing
chokepoint, latency-budget, and cdn/immutable machineries, merely NAMED
and cited so coverage can be proven exhaustive. Stored XSS is a plain
multi-hop reachability query. Only a few (CORS wildcard, compression,
batch-write, optimistic-render, route-authz) add a small precondition
predicate or flow attribute.

## Compliance: regulatory obligations (`std.compliance`)

A fifth family, `compliance`, covers government/regulatory duties (COPPA,
GDPR, CCPA, HIPAA, and a privacy-policy self-consistency check). It adds
two precondition dimensions the security families do not need, and its
mitigations are frequently a declared PROCESS boundary or a cited
ARTIFACT rather than code -- but the obligation/discharge/exhaustiveness
structure is identical.

**Data-subject tags on labels.** A `Pii` datum carries tags: `child`
(under-13, COPPA), `health` (PHI, HIPAA), `biometric`, `financial`, and a
jurisdiction (`eu-resident`, `ca-resident`). Tags refine the precondition:
an obligation can fire on "Pii tagged `health`" without firing on ordinary
Pii.

**Jurisdiction scope.** A regulation entry declares the jurisdictions it
binds; it fires only when the model handles a matching data-subject.

Concrete regulatory obligations, and the machinery each reuses:

| Obligation | Fires when | Discharge |
|---|---|---|
| COPPA -- no data from underage users | a collection flow from a principal whose age class is `unknown` or `child` reaches a Pii store with no verifiable-parental-consent boundary | an age-gate endorsement boundary (`unknown-age -> adult`, or `child -> child-with-consent`); ungated collection is `noflow(child -> PiiStore)` refuted -- pure closure |
| GDPR right-to-erasure | an `eu-resident`-tagged Pii store has no declared deletion path | a `revoke via ... within t` edge -- THE SAME rule as "no cache without invalidation" and "no credential without revocation" (the age collapse) |
| Data-retention limit | Pii rests in a store past a declared maximum age | an `age(store) <= retention` bound -- the age collapse again |
| GDPR lawful basis | `eu-resident` Pii is collected with no declared `basis` (consent/contract/legitimate-interest) | a declared basis attribute on the collection boundary; absence refuses |
| HIPAA -- PHI to a non-covered party | `health`-tagged data flows to a `managed` external node without a declared BAA attestation | a cited BAA `assume` or a covered-party attribute; else it is a declassification-to-uncovered refusal |
| Data minimization | a collection flow gathers a Pii field never read by any downstream flow | drop the field, or justify -- a reachability check (collected-but-never-used) |

**Privacy policy as claims (the reverse audit).** A privacy policy is a
set of DECLARED data practices ("we collect email and usage; we retain 90
days; we share with no third parties"). Model each as an `assert`: the
design must not EXCEED the policy. A flow collecting a field the policy
does not list, a retention longer than stated, or a third-party share the
policy denies, all REFUTE -- so the published privacy policy and the
actual system provably agree, and DOC002 binds the policy document to that
proof. Overclaiming ("we never store X") and under-disclosing ("we share
with Y but the policy is silent") are both build failures.

Exhaustiveness for compliance is per-regulation against a cited statute
baseline: every obligation the selected regulations impose has an entry or
a cited `out-of-scope`, every data-subject/jurisdiction the model touches
is classified, every fired duty is discharged or assumed (with the assume
carrying legal ownership + a review date -- regulations change, so the
staleness bound matters more here than anywhere).

## CVE: threat intelligence joined to the proof

CWE is the design side; CVE is the dependency side, enriching `frob vet`.
A CVE against a dependency maps (via NVD) to one or more CWEs. So a vet
finding becomes: "this dep has CVE-XXXX, which is CWE-89; your design's
CWE-89 obligation is [discharged -> contained in depth / assumed / missing
-> LIVE exposure]." CVE ingestion rides vet's existing osv-scanner
adapter and 14-day cooldown; the join is the shared CWE id. A live CVE
whose CWE obligation is undischarged is a high-severity finding; one whose
obligation is discharged is defense-in-depth and reported as contained.

## What is honestly not covered

Stated and enforced as assumptions: zero-day weakness classes not yet in
any CWE view; business-logic flaws with no structural precondition
(CWE-840 -- these need hand-written `assert` claims, not catalog
matching); and the extraction gap outside the analyzable subset (same
`std.policy.analyzable` dependency and enables-cascade as every other
tier-2 result). The catalog proves coverage of the CITED baseline, not of
the unknown -- and says so.

<a id="phasing"></a>
## Phasing (epic T-0109)

- **A (catalog + design-level obligations)**: `std.cwe` pack, `weakness`/
  `capability`/`out-of-scope` grammar, baseline views, THREAT001/003 over
  the model, the OWASP-Top-10 subset as data. Depends only on phases 0-2.
- **B (capability completeness)**: THREAT002, sink taxonomy, the
  capability->obligation instantiation; the deny-by-default unclassified-
  sink error at the model level. SHIPPED (T-0112):
  `check_capability_completeness` checks every `may`-declared capability
  kind against the sink taxonomy (`WeaknessEntry.capability_kind`s the
  catalog already names) or an explicit `BenignCapability` excuse; the
  code-level half (joining `_effects.py`'s extracted net/fs/exec sinks
  against this same taxonomy) stays phase C, since it needs the finer
  capability grammar `_effects.py` itself defers.
- **C (code binding)**: effect extraction of CWE-relevant sinks (joins
  T-0079), the "undeclared capability in code" error, mitigation
  chokepoint verification via the policy forms. SHIPPED (T-0113):
  `check_effect_completeness` joins `_effects.py::extract_effects`'s
  observed net/fs/exec sinks into the SAME `_entries_by_capability_kind`
  taxonomy THREAT002 and `_fired_obligations` use -- THREAT004 (an
  observed sink whose owning node declares no matching `may` capability,
  reusing `check_capability_conformance`'s join rather than re-detecting
  it) and THREAT005 (a declared-and-conformant sink whose kind names no
  catalog `capability_kind`, unless a `BenignCapability` excuses it; `fs`
  is left unmapped on purpose since CWE-22's precondition is a flow
  pattern, not a capability kind, per its own `capability_kind=None`
  entry). Mitigation chokepoint verification tightens THREAT003 instead
  of adding a new rule, in two layers:

  (1) SHAPE: a discharging claim must be `NoFlow(src=<foreign-trust node
  or the "foreign" level>, dst=<firing node>)`, the exact form
  `_eval_noflow` already proves over the closure engine's boundary-aware
  `reachable` -- a `Claim` at the right id and rung but the wrong body no
  longer discharges.

  (2) KIND: review round 2 found that (1) alone is insufficient --
  `reachable`'s barrier test fires on ANY `Boundary` regardless of
  `direction`/`predicate`, so a PROVED `NoFlow` originally meant only
  "SOME boundary blocks every path", and a `declassify` boundary (or an
  `endorse` boundary with an unrelated `predicate`, e.g.
  `"legal_review_signed_off"` standing in for a CWE-79 `output_encoding`
  requirement) discharged exactly like the catalog's actual required
  mitigation. `_mitigation_is_chokepoint` closes this: it isolates the
  boundaries carrying the catalog's EXACT mitigation
  (`direction=ENDORSE`, `predicate == WeaknessEntry.mitigation`) and
  re-evaluates the SAME `NoFlow` claim on a model copy with every OTHER
  boundary removed -- still the SAME `evaluate_claims`/`_eval_noflow`/
  `reachable` call, no new closure primitive. An `assumed` claim skips
  this check (it never reaches the closure at all; the owner/review gate
  is its only accountability, same as every other claim form).

  Disclosed precision cut (symmetric with THREAT005's `fs` disclosure
  above): the re-evaluation is PER-MODEL, not per-path.
  `FactBase.reachable` reports reachability, not which boundary blocked
  which specific path, so this cannot distinguish "every path carries a
  matching boundary" from "some paths carry a matching boundary and
  others carry only a non-matching one" at finer-than-model granularity --
  it collapses both to a single re-evaluation of the SAME claim with only
  the matching boundaries kept in. This is SOUND (removing non-matching
  boundaries can only add reachability, never remove it, so a PROVED
  result here really does mean the matching boundaries alone cut the
  closure) and deny-by-default in the imprecise direction (a path saved
  only by a non-matching boundary reopens in the restricted model and
  REFUTES the claim, correctly failing discharge) -- but a model wanting
  a true per-path mitigation-kind proof needs boundary-to-path attribution
  the closure API does not expose today. Noted here as a scope cut, not
  silently assumed away.
- **D (CVE join)**: NVD CVE->CWE ingestion into vet, the containment
  report, live-exposure severity.
- **E (quality families)**: `std.perf` / `std.reliability` /
  `std.compat` catalog packs with the anti-pattern table above; the small
  new precondition predicates (CORS wildcard, compression, batch-write,
  optimistic-render, route-authz) and their cited baselines. Reuses A-C
  machinery; adds no kernel. SHIPPED (T-0114): `QUALITY_CATALOG` in
  `_threat.py` catalogs the three table rows that map onto EXISTING
  kernel detectables with NO new precondition logic -- CWE-639 (dynamic
  ORM/query scoping) reuses the SAME `sql` `capability_kind` join CWE-89
  already fires on (a different cited id and mitigation, `tenant_scoping`,
  over the identical THREAT002/THREAT003 machinery); REL-001 (single-
  dependency bottleneck) and PERF-002 (non-statically-hosted content) are
  `capability_kind=None` citation-only entries whose actual refutation
  lives in the already-shipped capacity/budget (T-0066) and std.infra
  cdn/immutable machineries, mirroring the existing CWE-22/352/798
  citation-only precedent. Stored XSS needed no new entry at all: the
  existing CWE-79 `NoFlow` chokepoint check already walks `reachable`
  transitively, so a two-hop foreign-to-store-to-render path is the SAME
  obligation the phase-A entry already covers. `QUALITY_VIEWS` adds three
  family-scoped baselines (`web-performance-baseline`,
  `reliability-baseline`, `web-quality-security-baseline`) that
  `check_catalog_completeness` (THREAT001, unmodified) proves exhaustive
  when passed `QUALITY_CATALOG`/`QUALITY_OUT_OF_SCOPE` explicitly -- kept
  separate from `CWE_CATALOG`/`VIEWS` so the `owasp-top-10` view (built
  directly from `CWE_CATALOG`'s ids) never silently absorbs non-OWASP
  quality rows. The remaining five table rows (uncompressed JSON,
  one-at-a-time writes, un-optimistic render, wide-open CORS, loose
  backend URL rules) each need a genuinely new precondition the kernel
  model has no field for today (write cardinality, a `waits_for` render
  edge, a CORS-credentials boundary predicate, an endpoint/route concept)
  -- `QUALITY_OUT_OF_SCOPE` catalogs each with a reasoned entry rather
  than forcing a precondition that does not exist, honestly disclosed
  per docs/strata/threat.md#what-is-honestly-not-covered. No
  `compatibility`-family view is stubbed: the anti-pattern table above
  names zero compatibility rows, so a `compat-baseline` view would lie
  about what it checks.
- **F (audit + docs)**: `frob sys audit` per-family exhaustiveness matrix,
  DOC002 binding of security/quality prose, the litmus (a deliberately
  vulnerable+unoptimized model whose every planted anti-pattern the audit
  flags, with a hardened twin that discharges all families).

Catalog data is ingested from the authoritative sources (MITRE CWE
lists, NVD CVE->CWE), never hand-transcribed from memory -- the build
step pins and verifies the source digest.
