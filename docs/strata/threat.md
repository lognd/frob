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

**`cwe-top-25` (T-0143).** Pinned to the **2023** MITRE CWE Top 25 Most
Dangerous Software Weaknesses release
(cwe.mitre.org/top25/archive/2023/2023_top25_list.html). Staleness review
applies per the charter's "pinned to a release ... staleness past a review
bound is a gate warning" rule above -- when MITRE ships a newer Top 25, this
pin should be re-verified and bumped, not silently left stale. Eight of the
25 ids overlap the OWASP-cited core reframe entries already cataloged
(CWE-79/89/78/22/918/502/352/798) and are reused, not duplicated. Of the
remaining 17: one (CWE-94, code injection) gets a genuine new
`WeaknessEntry` reusing CWE-78's `exec` capability join (the kernel does
not distinguish an OS-command sink from a code-eval sink, so both fire on
the same precondition -- the same pattern CWE-639 already uses for `sql`).
The other 16 are honest `OutOfScopeEntry` rows, each naming the SPECIFIC
kernel concept still missing: a memory-safety group (CWE-787/416/125/119/
476/190 -- no pointer/buffer/allocator/arithmetic-width model), a
concurrency id (CWE-362 -- no synchronization/scheduling model), an
authn/authz-boundary group (CWE-862/863/306/287/269/276 -- no endpoint/
route + authn/authz predicate concept, the same gap `SEC-ROUTE-AUTHZ-001`
already names), a file-upload id (CWE-434 -- no content-type-validation
sink), a generic-precondition id (CWE-20 -- no structural precondition of
its own, same class as CWE-840 below), and one duplicate-coverage
disclosure (CWE-77, the generic parent of CWE-78's already-cataloged
OS-command instance -- a second entry would duplicate the identical fire
path, the same non-duplication discipline the stored-XSS note above
applies). `cwe-top-25`'s view table (`CWE_TOP_25_VIEWS`) is kept
deliberately separate from the main `VIEWS` dict: `frob.strata._audit`'s
`DEFAULT_SECURITY_VIEWS` iterates every `VIEWS` key against the bare
`CWE_CATALOG` default, so merging `cwe-top-25` in would silently
under-catalog it there -- the exact rationale `QUALITY_VIEWS` already
follows for the performance/reliability/compat families.

**`owasp-asvs` / `cwe-1000` decision (T-0143).** Deliberately kept
unstubbed, not transcribed. ASVS (the OWASP Application Security
Verification Standard) is a verification-CHECKLIST standard -- its items
are testing/process requirements ("verify that...") rather than discrete
weakness ids with a natural CWE-shaped precondition/mitigation pair; most
ASVS items either restate CWEs already cataloged above under a different
organizing scheme, or name a verification activity (code review, pen test
cadence) with no flow precondition the closure engine can detect at all.
Force-fitting ASVS into `WeaknessEntry`/`OutOfScopeEntry` rows would mean
either silently duplicating existing CWE coverage under new ids, or
padding the catalog with `capability_kind=None` citation-only stubs that
add no exhaustiveness signal beyond what `owasp-top-10`/`cwe-top-25`
already prove -- busywork, not more honesty. `cwe-1000` is MITRE's full
research view of roughly 900 entries, the overwhelming majority far
outside anything a design-level closure engine's precondition vocabulary
can express (deeply platform/language-specific memory, protocol, and
hardware weaknesses). Transcribing it wholesale would produce hundreds of
near-identical `OutOfScopeEntry` rows citing the SAME handful of missing
kernel concepts (memory model, concurrency model, endpoint/route model)
already named above for the 16 Top-25 out-of-scope ids -- out-of-scope
spam that would bury the genuinely actionable gaps rather than surface
them. Both stay unstubbed so THREAT001 never lies about a view it cannot
meaningfully check; this paragraph is the recorded WHY, not a silent
gap.

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

## PII declarations (`std.pii`, T-0154)

`std.compliance` (above) proves REGULATORY obligations (COPPA/GDPR/HIPAA)
keyed on `subject:`/`jurisdiction:`/`basis:` attrs and the `Pii` label
rung -- opaque-string vocabulary an author must remember to attach by
hand. `std.pii` adds the missing FIRST-CLASS layer underneath it: a
`carries "<category>.<field>"` surface declaration (`strata-core/src/
parse.rs::parse_node`/`parse_store`, the SAME STRING-quoted `code`/`may`
grammar shape T-0132 established) naming WHAT personal data a node/store
actually holds, one attr per tag (`pii=<category>.<field>`,
`_pii.py::_PII_PREFIX`) -- no new kernel primitive (charter law 1), just
a new attr convention `code`/`skew`/`fanout` already established the
shape for.

**Categories** (`_pii.py::PII_CATEGORIES`, T-0154 ticket body): identifier,
contact, financial, health, biometric, behavioral, credentials. A
`carries` tag's category prefix (before the first `.`) must be one of
these seven.

Everything past the declaration itself is a JOIN, not new detection where
existing machinery already computes the fact:

| Rule | Fires when | Discharge |
|---|---|---|
| PII001 (catalog) | a `carries` tag's category prefix is not one of the fixed seven | none -- fix the tag; a malformed/unknown category is not a claim-overridable obligation, the same shape THREAT001's catalog-completeness check has no per-violation override either |
| PII002 (boundary-crossing protection) | a flow touching a PII-carrying node (either end) crosses a different `TRUST` level | an ASSUMED `pii:PROTECTION:<flow-id>` claim, owner+review -- deny-by-default since no structural encryption/pseudonymization/consent detector exists (the SAME THREAT003 discharge shape, applied to a capability-free precondition) |
| PII003 (retention/erasure) | a PII-carrying node has no `retention=` bound and no revocation-edge flow | a declared `retention=<bound>` attr, or a flow carrying `attrs=("revocation", ...)` -- REUSING `_compliance.py::_retention_limit`/`_REVOCATION_ATTR` directly, not re-detecting either fact (the "join to existing compliance obligations rather than duplicating them" instruction) |
| PII004 (undeclared-PII lint) | a flow sourced from a PII-carrying node is labeled below `Pii` | relabel the flow `Pii` (or above) -- the model's own `carries` fact contradicting the flow's declared label is the violation |

PII003 is deliberately JURISDICTION-AGNOSTIC (fires on `carries` alone,
no `jurisdiction:eu-resident` tag required) -- it is the baseline "if you
carry PII at all, declare how it leaves" duty; `_compliance.py`'s
GDPR-RETENTION/GDPR-ERASURE checks are the EU-specific tightening layered
on top of the SAME two helpers, not a second implementation of the same
rule.

**Litmus pair**: `tests/unit/strata/litmus/pii_vuln.strata` fires
PII002/PII003/PII004 undischarged (a collection flow into a `carries
"identifier.email"` store, no protection claim, no retention/erasure, and
a mislabeled downstream flow); `pii_hardened.strata` discharges every one
of them (an assumed `pii:PROTECTION:f_collect` claim, a revocation-edge
flow, and a correctly `Pii`-labeled downstream flow) -- both round-trip
through the real parser (`tests/unit/strata/test_litmus_pii.py`), the
same T-0145 discipline `cwe_79_vuln.strata`/`cwe_79_hardened.strata`
established. PII001 has no discharge shape to litmus-test (see table
above), so its coverage lives in `test_pii.py`'s hand-built-`KernelModel`
unit tests instead, mirroring where `_compliance.py`'s own tests live.

**Self-model**: `design/frob.strata` declares its own PII posture
EXPLICITLY ZERO (frob models design/ticket/code text, not personal data)
-- `tests/unit/strata/test_pii.py::TestFrobSelfModelPiiPosture` locks this
as a checked assertion (zero `pii=` attrs on every node, `evaluate_pii`
clean) rather than letting the zero case hold silently by omission.

## Operational design lints (`std.lint`, T-0155)

`std.pii` (above) proves a MODELING-shape obligation family (does a
node's own `carries` fact stay consistent with the rest of the model);
`std.lint` proves an OPERATIONAL family instead: caching, resource
bounds, rate-limiting, and kill-switch rules over the SAME kernel facts
`Node.capacity` (T-0103), `Flow.rate`, `std.infra`'s `cache` construct
(`_infra.py`), the scenario engine's `ScaleRate` rewrite (T-0073), and
`Node.may` capability kinds (`_effects.py::_may_kind`, T-0150) already
carry. Zero new kernel primitive (charter law 1) -- every LINT rule is a
JOIN, and the one new surface vocabulary word (a kill-switch reference)
reuses the grammar's already-existing generic `attr IDENT=IDENT` node
property (`flag=<id>`), the SAME attr-desugar convention `code=`/`pii=`
established (T-0132/T-0154), not a new keyword.

| Rule | Fires when | Discharge |
|---|---|---|
| LINT001 (undeclared rate limit) | a flow sourced from a `foreign`-trust node has no declared `rate` | declare `rate` on the flow -- no claim override; a missing rate is a missing FACT, not an assumable risk (the PII001 no-override shape) |
| LINT002 (store overload, caching-escapable) | a node's declared `capacity.service_rate` is exceeded by its non-infra inbound flows' combined rate, with no `cache` construct declared over it | declare a `cache X of <node>` (`_infra.py`), OR raise `capacity`, OR lower the flow(s)' declared rate |
| LINT003 (surge scenario with no capacity bound) | a `Scenario` with a `ScaleRate` rewrite nests no `BoundClaim` (RATE or UTILIZATION) targeting the scaled flow or either endpoint | nest an `assert`/`assume bound rate|utilization ... <= ...` claim inside the same scenario -- structural presence only, asserted or assumed both count |
| LINT004 (risky capability, no kill switch) | a node holds a `may` atom of kind `exec`/`net` (`RISKY_CAPABILITY_KINDS`) with no declared `attr flag=<id>` | declare `attr flag=<id>;` naming the real feature-flag/kill-switch identifier an operator flips live |
| LINT005 (fan-in exceeding capacity, unconditional) | a node's declared `capacity` (`service_rate * replicas_max`) is exceeded by its TOTAL inbound flow rate, regardless of caching | raise `capacity` (service rate or `replicas_max`), or reduce the fan-in -- no caching escape (module docstring: caching relieves repeated reads of a source of truth, not a compute sink's raw fan-in) |

LINT002 and LINT005 are deliberately NOT the same check under two names:
LINT002 is narrower and caching-escapable (a store-shaped node's overload
is relieved once a cache sits in front of it); LINT005 is the
caching-agnostic baseline (a node with no possible cache construct over
it -- a queue consumer, a balancer target -- still needs enough replica
headroom to absorb its fan-in). A model can fail LINT002 and pass LINT005
(cache-covered, but the cached node itself sits below its callers'
declared rate) or vice versa (no cache, but `replicas_max` headroom
absorbs the fan-in) -- the exact LINT002-vs-LINT005 relationship
`_lint.py`'s module docstring spells out is the same PII003/GDPR-RETENTION
precedent this catalog already establishes (above).

Any LINT001-005 finding (or SYS100-102/THREAT002-003/PII/COMPLIANCE) can
be waived with a written reason via a `waive` clause on the firing node --
see `docs/strata/waive.md` (T-0174) for the mechanism, WAIVED reporting,
and the stale-waiver drift lock.

**Litmus pair**: `tests/unit/strata/litmus/lint_vuln.strata` fires all
five rules from one small model (a foreign-sourced unrated flow, an
overloaded `may "exec"` store with no cache/kill-switch, and an unbounded
surge scenario); `lint_hardened.strata` discharges every one of them (a
declared rate, a `cache` construct, a nested bound claim, an `attr
flag=<id>`, and widened `replicas_max`) -- both round-trip through the
real parser (`tests/unit/strata/test_litmus_lint.py`), the same T-0145/
T-0154 discipline established.

**Wired into `frob sys audit`**: `_audit.py::evaluate_exhaustiveness`
joins `_lint.py::evaluate_lint` in under a fixed `lint:model` view (LINT
rules have no baseline-view/catalog-completeness concept, the same fixed-
view shape `pii:model` uses), so every LINT001-005 finding surfaces
alongside self-conformance/PII/compliance in one audit report.

**Self-model honesty note (T-0155, "make it green honestly")**:
`design/frob.strata`'s `f_registry_fetch` now declares a real, honestly
conservative `rate 1 req/s` (LINT001 discharged). `checker`/`core`/
`stratamod`/`vet` each hold a risky (`exec`/`net`) capability with
**no real kill switch in the codebase today** -- rather than fabricate a
`flag=<id>` attr that names a mechanism that does not exist, each of these
four nodes now declares a `waive "LINT004" reason "..." ticket "T-0200";`
clause (T-0174, `docs/strata/waive.md`): `frob sys audit` prints these as
WAIVED with the reason rather than either a fabricated pass or permanent
unexplained red, and the waiver goes stale (fails the run) the moment
T-0200 lands a real kill switch and the LINT004 finding stops firing --
so the debt cannot silently outlive its own fix.

## CVE: threat intelligence joined to the proof

CWE is the design side; CVE is the dependency side, enriching `frob vet`.
A CVE against a dependency maps (via NVD) to one or more CWEs. So a vet
finding becomes: "this dep has CVE-XXXX, which is CWE-89; your design's
CWE-89 obligation is [discharged -> contained in depth / assumed / missing
-> LIVE exposure]." CVE ingestion rides vet's existing osv-scanner
adapter and 14-day cooldown; the join is the shared CWE id. A live CVE
whose CWE obligation is undischarged is a high-severity finding; one whose
obligation is discharged is defense-in-depth and reported as contained.

<a id="cve-fingerprints-code-level-pattern-catalog-t-0153"></a>
## CVE fingerprints: code-level pattern catalog (T-0153)

Distinct from the section above: that join is dependency-VERSION-shaped
("this pinned version has advisory CVE-XXXX"), useless for first-party
code or a dependency with no filed advisory yet. `frob.strata.
_cve_fingerprint.CveFingerprint` is a source-code NEEDLE for a canonical
vulnerable-usage class -- `frob.vet._capability.scan_file_fingerprints`
flags the SHAPE of the vulnerability directly in a file's text, following
`scan_file_capabilities`'s recall-over-precision substring philosophy
(module docstring, `src/frob/vet/_capability.py`) plus the T-0151 dot-
exclusion lesson (a needle must not fire on a dotted method access that
merely shares a name with a dangerous bare call).

`CVE_FINGERPRINTS` (`src/frob/strata/_cve_fingerprint.py`) ships nine
entries, each joined to an EXISTING `std.cwe` catalog id via `cwe_id` and
cited by at least one REAL, independently-verified CVE -- `cve` is never
hand-guessed from memory; every citation here was checked against a
primary/vendor/NVD source at authoring time. `check_fingerprint_catalog_
drift` (CVEFP001) fails loudly if a fingerprint names a `cwe_id` absent
from the joined `CWE_CATALOG + CWE_TOP_25_CATALOG + QUALITY_CATALOG` --
the same "an unjoined reference is an error, never a silent pass" rule
`WeaknessEntry.capability_kind`'s join to `_effects.py::_may_kind` already
follows. `CVE_FINGERPRINT_VIEWS['cve-fingerprint-catalog']` is a SEPARATE
view table (never merged into `VIEWS`/`CWE_TOP_25_VIEWS`), following the
same "no silent default-view widening" precedent those tables already set.

**Curated, not exhaustive -- a disclosed cut, not a silent one.** Three of
the ticket's suggested example classes are deliberately NOT shipped:
TLS `verify=False` (CWE-295), weak-hash password storage (CWE-916), and
XML external entities (CWE-611) have no `WeaknessEntry` in ANY catalog
tuple yet, so a fingerprint citing any of the three would fail this
module's OWN CVEFP001 drift-lock -- confirming they need a catalog
addition (a separate, catalog-scoped ticket) before a fingerprint can
honestly join them, rather than being force-fit around the drift-lock.
JNDI-style lookup injection (the Log4Shell class) is Java/JNDI-specific
with no equivalent construct in any of the four languages `frob.vet.
_capability` scans (python/typescript/rust/c-cpp); a fingerprint with no
genuine needle in a scanned language would be undetectable data, not a
pattern-match capability, so it is omitted rather than shipped inert.

**Wired into two operational paths, not test-only.** (1) `frob.vet.
_capability.scan_directory_fingerprints` runs from `frob.vet._scan.
_scan_source` the SAME way `scan_directory_capabilities` already does --
a `frob vet` run over a dependency tree surfaces a VET006 finding (and a
`"cve-fingerprint"` signal on the stored `PackageVerdict`) when a
dependency's source matches a fingerprint's needle(s), independent of
whether its pinned version has a filed osv advisory. (2)
`check_fingerprint_catalog_drift` runs from `_audit.py::
evaluate_exhaustiveness` every call (model-independent, like `_pii_gaps`
-- reported under the fixed `cve-fingerprint:catalog` pseudo-view,
mirroring PII001-004's fixed `"model"` view since a catalog-join property
has no per-model baseline-view concept), so `frob sys audit` fails closed
on a drifted `cwe_id` the same way THREAT001-003 already do for the
security/quality families.

**Self-match note (same class as T-0151/T-0158):** `_cve_fingerprint.py`
stores every needle as a Python string literal, so scanning that file's
OWN text would trivially "match" every fingerprint it defines regardless
of what the file's code actually does; `scan_directory_capabilities`
excludes it from aggregation the same way it already excludes `_capability.
py`/`_capability_registry.py` (`_is_self_path`).

<a id="litmus-coverage"></a>
## Litmus coverage: every catalog entry fires from real source (T-0145)

`tests/unit/strata/litmus/*.strata` + `tests/unit/strata/test_litmus_cwe.py`
prove, for EVERY `WeaknessEntry` in `CWE_CATALOG` and `CWE_TOP_25_CATALOG`,
that its THREAT003 obligation actually fires from a `.strata` file run
through the real `parse_module -> elaborate -> check_discharge_completeness`
pipeline -- never a hand-built `KernelModel` (that precedent stays in
`test_threat.py`, e.g. `TestCweTop25.test_cwe_94_fires_and_discharges_on_
exec_capability`). This is the same round trip `design/litmus/audit_vuln.
strata` + `audit_hardened.strata` (T-0115/T-0138) already prove for
CWE-89/CWE-639; T-0145 extends it to EVERY catalog id, parametrized so a
future `WeaknessEntry` with no fixture fails the suite (vacuous-pass
doctrine, the same drift-lock discipline the tmLanguage keyword-parity
test uses).

**One fixture pair per firing id** (`<id>_vuln.strata` fires undischarged,
`<id>_hardened.strata` discharges it as an ASSUMED `NoFlow` claim named
`weakness:<cwe-id>:<node-id>`, owned and reviewed): CWE-79, CWE-89,
CWE-918, CWE-502, CWE-922. **One shared fixture pair** for CWE-78/CWE-94
(`cwe_exec_vuln.strata`/`cwe_exec_hardened.strata`): both weaknesses fire
on the SAME `may "exec"` capability (the kernel has no OS-command-vs-
code-eval distinction), so one fixture proves both fire, and the hardened
twin proves both discharge independently -- an extra test drops just the
CWE-94 discharge claim and confirms CWE-78 alone stays discharged while
CWE-94 alone stays undischarged (the shared-join non-duplication
guarantee, matching `test_cwe_94_reuses_the_exec_capability_join`'s
precedent).

**Design finding: three catalog ids can never fire.** CWE-22, CWE-352,
and CWE-798 are cataloged with `capability_kind=None` (each entry's own
comment names why: CWE-22 is a "flow-to-filesystem-path-sink
precondition, not a capability kind"; CWE-352 is a "state-changing-
endpoint precondition"; CWE-798 is a "secret-resting-at-low-clearance
precondition, already the lattice's own clearance-violation refusal").
`_fired_obligations`/`_entries_by_capability_kind` only join entries whose
`capability_kind is not None` -- structurally, NO `.strata` source, no
matter how plausibly vulnerable-looking, can make these three fire under
THREAT003 as it exists today. `cwe_22_unfired.strata`,
`cwe_352_unfired.strata`, and `cwe_798_unfired.strata` each model the
scenario the weakness would actually look like (a foreign caller reaching
a filesystem/endpoint/secret-facing node) specifically to prove the
negative explicitly -- `test_never_fires_even_in_a_plausible_vulnerable_
scenario` asserts zero THREAT003 violations for each id, rather than
skipping it. Closing this gap for real needs the same new kernel
vocabulary each entry's `capability_kind=None` comment already names (a
filesystem-path-sink concept, a state-changing-endpoint concept, or
reusing the lattice's clearance-violation machinery directly instead of a
THREAT003 join) -- out of T-0145's scope (fixture coverage of the
EXISTING catalog, not new kernel primitives), tracked as an honest,
disclosed gap rather than a silent one.

The out-of-scope exemption boundary is checked too:
`test_out_of_scope_ids_cover_the_top_25_gap_exactly` proves
`CWE_TOP_25_OUT_OF_SCOPE`'s ids are exactly the `cwe-top-25` view members
this suite's catalog union (`CWE_CATALOG + CWE_TOP_25_CATALOG`) does not
cover -- no id can silently escape both the fixture table and the
out-of-scope list.

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
  (T-0085 + T-0115): `frob sys doc` renders the matrix
  (`frob.strata._sysdoc.render_audit_matrix`, docs/commands/sys.md#frob-
  sys-doc), the claims audit (DOC003, charter drift note above) is wired
  into `sys_gate`, and `frob sys audit`
  (`frob.strata._audit.evaluate_exhaustiveness`, docs/commands/sys.md
  #frob-sys-audit) is the CI-ready checking counterpart: the full
  THREAT001-003 + COMPLIANCE001-002 conjunction against every configured
  view, exiting nonzero with named gaps. The vuln-litmus/hardened-twin
  pair (`design/litmus/audit_vuln.strata` + `design/litmus/audit_hardened.
  strata`) exercises at least one fired-undischarged obligation per
  security/quality family (CWE-89, CWE-639), refuted then proved clean by
  its hardened twin -- both round-trip through the real parser (T-0138
  added a STRING-quoted claim-id alternate so a `weakness:<cwe>:<node>`
  discharge claim can be authored from `.strata` source). The compliance
  family (COPPA) is still a `KernelModel` Python fixture in tests/unit/
  strata/test_audit.py: a separate surface-grammar gap (no `.strata`
  source can author a `subject:child`-tagged flow attr today) blocks that
  leg specifically; `strata-core/**` grammar work for it is unscoped and
  unfiled.

Catalog data is ingested from the authoritative sources (MITRE CWE
lists, NVD CVE->CWE), never hand-transcribed from memory -- the build
step pins and verifies the source digest.
