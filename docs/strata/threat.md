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
expiring. The claims audit binds prose: a README claiming "protected
against the OWASP Top 10" must cite a PROVED exhaustiveness result or it
fails CI.

**Charter drift (T-0085):** earlier phasing text in this document named
this check DOC002. By the time T-0085 implemented it, DOC002 had already
been taken by the doc-anchor-resolution gate (T-0127, `frob.gates.
docanchor_gate`). The claims audit ships as **DOC003** instead; every
other mention of "DOC002" in this file in connection with the claims
audit is this same drift and should be read as DOC003. `frob:claims
<view>` is the marker directive (docs/commands/sys.md#the-claims-audit-
doc003); the check itself lives in `frob.gates.sys_gate` (opt-in on a
`design/` directory existing, same posture as SYS001-004) rather than a
standalone `docanchor`-family gate, since it needs the loaded design
model, not just doc-to-doc anchor resolution.

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
actual system provably agree, and the claims audit (DOC003, charter drift
note above) binds the policy document to that proof. Overclaiming ("we
never store X") and under-disclosing ("we share with Y but the policy is
silent") are both build failures.

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
  chokepoint verification via the policy forms.
- **D (CVE join)**: NVD CVE->CWE ingestion into vet, the containment
  report, live-exposure severity.
- **E (quality families)**: `std.perf` / `std.reliability` /
  `std.compat` catalog packs with the anti-pattern table above; the small
  new precondition predicates (CORS wildcard, compression, batch-write,
  optimistic-render, route-authz) and their cited baselines. Reuses A-C
  machinery; adds no kernel.
- **F (audit + docs)**: per-family exhaustiveness matrix + the claims
  audit binding security/quality prose, the litmus (a deliberately
  vulnerable+unoptimized model whose every planted anti-pattern the audit
  flags, with a hardened twin that discharges all families). SHIPPED
  (T-0085) in part: `frob sys doc` renders the matrix
  (`frob.strata._sysdoc.render_audit_matrix`, docs/commands/sys.md#frob-
  sys-doc) and the claims audit (DOC003, charter drift note above) is
  wired into `sys_gate`. The litmus (deliberately vulnerable + hardened
  twin models) is not part of T-0085's scope; noted as a remaining cut,
  not silently dropped.

Catalog data is ingested from the authoritative sources (MITRE CWE
lists, NVD CVE->CWE), never hand-transcribed from memory -- the build
step pins and verifies the source digest.
