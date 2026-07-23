# Software-Security Weakness/Vulnerability Corpus

Status: exhaustive-research pass, live-verified against primary sources on
2026-07-19/20. Extends (does not replace) the in-repo catalogs:
`src/frob/strata/_threat.py` (`CWE_CATALOG`, `CWE_TOP_25_CATALOG`,
`QUALITY_CATALOG`) and `src/frob/strata/_cve_fingerprint.py`
(`CVE_FINGERPRINTS`). `docs/design/capability-evasion-taxonomy.md` does NOT
exist in this repo at time of writing -- treated as absent, not silently
assumed.

Every row cites a primary source: MITRE CWE, OWASP, NVD/vendor advisory, a
named framework's own spec site, or a named paper/talk. Rows the repo
already carries are marked `[IN-REPO]`; rows added here are new. A
`strata-checkability` tag is assigned to every weakness/framework entry:

- `design-level-provable` -- has a capability-kind precondition + mitigation
  boundary shape `std.cwe` can auto-instantiate and discharge today.
- `needle-detectable` -- has a code-level pattern shape `std.cve`
  fingerprints can match, even without a design-level precondition.
- `advisory` -- real and named, but the kernel model has no vocabulary
  (memory layout, concurrency, role/privilege, endpoint/route) to express
  its precondition; a human-authored assert/claim is the only route today.
- `not-checkable` -- process/organizational/framework-level, not a
  code-shape at all (e.g. a threat-modeling methodology itself).

---

## 1. MITRE CWE Top 25 Most Dangerous Software Weaknesses

### 1a. 2025 list (current; released with CISA, analysis window June 2024 -
June 2025, 39,080 CVE records)

Primary source: https://cwe.mitre.org/top25/archive/2025/2025_cwe_top25.html
(mirror: https://www.cisa.gov/news-events/alerts/2025/12/11/2025-cwe-top-25-most-dangerous-software-weaknesses)

| Rank | CWE | Name | strata tag | Repo status |
|---|---|---|---|---|
| 1 | CWE-79 | XSS | design-level-provable | [IN-REPO] `CWE_CATALOG` |
| 2 | CWE-89 | SQL Injection | design-level-provable | [IN-REPO] `CWE_CATALOG` |
| 3 | CWE-352 | CSRF | advisory (capability_kind=None) | [IN-REPO] `CWE_CATALOG` |
| 4 | CWE-862 | Missing Authorization | advisory | [IN-REPO] `CWE_TOP_25_OUT_OF_SCOPE` |
| 5 | CWE-787 | Out-of-bounds Write | advisory (no buffer model) | [IN-REPO] `CWE_TOP_25_OUT_OF_SCOPE` |
| 6 | CWE-22 | Path Traversal | advisory (flow-to-path-sink) | [IN-REPO] `CWE_CATALOG` |
| 7 | CWE-416 | Use After Free | advisory (no allocator model) | [IN-REPO] `CWE_TOP_25_OUT_OF_SCOPE` |
| 8 | CWE-125 | Out-of-bounds Read | advisory | [IN-REPO] `CWE_TOP_25_OUT_OF_SCOPE` |
| 9 | CWE-78 | OS Command Injection | design-level-provable | [IN-REPO] `CWE_CATALOG` |
| 10 | CWE-94 | Code Injection | design-level-provable | [IN-REPO] `CWE_TOP_25_CATALOG` |
| 11 | CWE-120 | Classic Buffer Overflow | advisory (no buffer model) | registry-dispositioned: `duplicate-of:CWE-787` (`weaknesses.yaml`) -- structurally subsumed, not a code-catalog gap (T-0674) |
| 12 | CWE-434 | Unrestricted File Upload | advisory | [IN-REPO] `CWE_TOP_25_OUT_OF_SCOPE` |
| 13 | CWE-476 | NULL Pointer Dereference | advisory | [IN-REPO] `CWE_TOP_25_OUT_OF_SCOPE` |
| 14 | CWE-121 | Stack-based Buffer Overflow | advisory | registry-dispositioned: `duplicate-of:CWE-119` (`weaknesses.yaml`) -- structurally subsumed, not a code-catalog gap (T-0674) |
| 15 | CWE-502 | Deserialization of Untrusted Data | design-level-provable | [IN-REPO] `CWE_CATALOG` |
| 16 | CWE-122 | Heap-based Buffer Overflow | advisory | registry-dispositioned: `duplicate-of:CWE-119` (`weaknesses.yaml`) -- structurally subsumed, not a code-catalog gap (T-0674) |
| 17 | CWE-863 | Incorrect Authorization | advisory | [IN-REPO] `CWE_TOP_25_OUT_OF_SCOPE` |
| 18 | CWE-20 | Improper Input Validation | advisory (no structural precondition) | [IN-REPO] `CWE_TOP_25_OUT_OF_SCOPE` |
| 19 | CWE-284 | Improper Access Control | advisory (no role/privilege model) | registry-dispositioned: `out-of-scope:authn-authz-boundary-predicate` (`weaknesses.yaml`) -- no code-catalog gap (T-0674) |
| 20 | CWE-200 | Exposure of Sensitive Information | advisory | registry-dispositioned: `out-of-scope:authn-authz-boundary-predicate` (`weaknesses.yaml`) -- no code-catalog gap (T-0674) |
| 21 | CWE-306 | Missing Authentication for Critical Function | advisory | [IN-REPO] `CWE_TOP_25_OUT_OF_SCOPE` |
| 22 | CWE-918 | SSRF | design-level-provable | [IN-REPO] `CWE_CATALOG` |
| 23 | CWE-77 | Command Injection (generic) | advisory (dup of CWE-78 fire path) | [IN-REPO] `CWE_TOP_25_OUT_OF_SCOPE` |
| 24 | CWE-639 | Authz Bypass via User-Controlled Key | design-level-provable (reuses `sql` kind) | [IN-REPO] `QUALITY_CATALOG` (as security-family row, cited there) |
| 25 | CWE-770 | Allocation of Resources Without Limits/Throttling | advisory (no resource-budget-vs-input-size model outside T-0066 latency budget) | registry-dispositioned: `out-of-scope:memory-model` (`weaknesses.yaml`) -- no code-catalog gap (T-0674) |

**Finding: the in-repo `CWE_TOP_25_CATALOG`/`CWE_TOP_25_OUT_OF_SCOPE` pair
(`src/frob/strata/_threat.py` lines ~443-621) is pinned to the **2023**
list** (its own comment cites
`https://cwe.mitre.org/top25/archive/2023/2023_top25_list.html`). Two
newer releases exist (2024, 2025); six 2025-list ids
(CWE-120/121/122/200/284/770) are absent from that Python catalog's
2023-pinned transcription. This is exactly the staleness case the repo's
own docstring flags as an owed "gate warning" review for the CODE catalog
specifically. Denominator: 25 (2025 list) vs 25 (2023 list, repo's pin) --
19 ids carry over unchanged rank-membership (with reordering), 6 are
absent from the 2023-pinned `_threat.py` transcription.

**T-0674 adjudication (RECONCILIATION.md finding (e)):** this absence from
`_threat.py` is NOT, on its own, evidence of a documentation gap in the
weakness REGISTRY (`weaknesses.yaml`/`docs/design/cwe-1000-registry.md`).
The registry already catalogues all six CWEs, each with a disposition from
the stricter rule-based classifier, and each cross-referencing this table
(`security-corpus:cwe-top25-2025`):

| CWE | Registry disposition | Ruling |
|---|---|---|
| CWE-120 | `duplicate-of:CWE-787` | AFFIRMED -- classic buffer overflow is a structural instance of CWE-787 (Out-of-bounds Write); no separate registry entry needed. |
| CWE-121 | `duplicate-of:CWE-119` | AFFIRMED -- stack-based overflow is a `CWE-119` (memory-buffer-bounds) variant per CWE-1000's own child listing. |
| CWE-122 | `duplicate-of:CWE-119` | AFFIRMED -- heap-based overflow is a `CWE-119` variant, same rationale as CWE-121. |
| CWE-200 | `out-of-scope:authn-authz-boundary-predicate` | AFFIRMED -- sensitive-info exposure requires a role/authz-boundary model the kernel does not have; correctly excused, not omitted. |
| CWE-284 | `out-of-scope:authn-authz-boundary-predicate` | AFFIRMED -- Pillar-level access control is the same missing-model case as CWE-200/285/863; correctly excused. |
| CWE-770 | `out-of-scope:memory-model` | AFFIRMED -- resource-budget-vs-input-size has no kernel model outside the unrelated T-0066 latency budget; correctly excused. |

Each ruling affirms the registry's classifier-driven disposition as
correct: none of the six is a silently dropped entry, and none requires a
`weaknesses.yaml` change. The defect was this table's own "NOT in
repo -- gap" phrasing, which conflated "absent from the 2023-pinned
`_threat.py` CODE catalog" with "absent from the DOCUMENTATION registry" --
those are two different denominators. The table rows above are corrected
in place to cite the registry disposition instead of claiming a gap. The
`_threat.py` 2023-to-2025 pin staleness remains real and is unaffected by
this ruling; it is a separate, already-flagged code-catalog concern, not
a registry gap.

### 1b. 2024 list (intermediate, for drift trail)
Primary source: https://cwe.mitre.org/top25/archive/2024/2024_cwe_top25.html
Not separately tabulated here (2025 supersedes it and the repo already
lags two releases behind 2023) -- flagged as a partial/deferred sub-check;
recommend the repo's staleness-review ticket target 2025 directly rather
than stepping through 2024.

---

## 2. OWASP Top 10 (2021, current stable release)

Primary source: https://owasp.org/Top10/2021/

| ID | Name | CWEs represented (OWASP mapping) | strata tag | Repo status |
|---|---|---|---|---|
| A01:2021 | Broken Access Control | CWE-22, CWE-284, CWE-285, CWE-639, CWE-862, CWE-863, +28 more | advisory (no endpoint/route+authz model) | partially [IN-REPO] via CWE-22/639 |
| A02:2021 | Cryptographic Failures | CWE-259, CWE-296, CWE-327, CWE-331 (formerly "Sensitive Data Exposure") | advisory (no crypto-primitive-strength model) | **NOT in repo -- gap; note CVE_FINGERPRINTS docstring explicitly defers weak-hash/CWE-916 for lack of a WeaknessEntry** |
| A03:2021 | Injection | CWE-79, CWE-89, CWE-73, CWE-77, CWE-78, CWE-94, CWE-943 | design-level-provable | [IN-REPO] CWE-79/89/78/94 |
| A04:2021 | Insecure Design | CWE-209, CWE-256, CWE-501, CWE-522 (new category 2021) | advisory (methodology, not a single precondition) | not-checkable as one entry; individual member CWEs vary |
| A05:2021 | Security Misconfiguration | CWE-16, CWE-611 (XXE folded in here in 2021), CWE-2 | advisory/needle-detectable per member | XXE (CWE-611) **explicitly NOT shipped** per `_cve_fingerprint.py` docstring (no WeaknessEntry exists to join) |
| A06:2021 | Vulnerable and Outdated Components | (component-CVE join, not a CWE) | needle-detectable (frob.vet's separate version-CVE join, `frob.vet._cve`/`_containment`) | [IN-REPO] but in a DIFFERENT subsystem (vet, not std.cwe) -- correctly disclosed as distinct in `_cve_fingerprint.py` module docstring |
| A07:2021 | Identification and Authentication Failures | CWE-297, CWE-287, CWE-384 | advisory (no session/credential-boundary model) | **NOT in repo -- gap** |
| A08:2021 | Software and Data Integrity Failures | CWE-829, CWE-494, CWE-502 (new category 2021; supply-chain/CI focus) | design-level-provable (CWE-502 slice only) | [IN-REPO] CWE-502 only; CWE-829/494 (unsigned update/untrusted plugin) not modeled |
| A09:2021 | Security Logging and Monitoring Failures | CWE-778, CWE-117, CWE-223 | not-checkable (absence-of-control, not a flow precondition) | **NOT in repo -- gap** |
| A10:2021 | Server-Side Request Forgery (SSRF) | CWE-918 (new category 2021) | design-level-provable | [IN-REPO] CWE-918 |

Denominator: 10/10 OWASP-2021 categories enumerated. Repo coverage: 4 of 10
categories have a design-level-provable `WeaknessEntry` slice (A01 partial,
A03, A08 partial, A10); A06 covered in a separate subsystem; 5 categories
(A02, A04, A05-non-XXE-slice, A07, A09) have zero repo representation.

**OWASP Top 10:2024** -- searched; no successor list has been published as
of this writing (2021 remains OWASP's current stable release; the 2025-list
CWE Top 25 above is a separate MITRE product, not an OWASP update).
Reporting this as verified-absent rather than guessing a 2024/2025 OWASP
list exists.

---

## 3. CWE-1000 Research View (structure only, not fully transcribed)

Primary source: https://cwe.mitre.org/data/definitions/1000.html

CWE-1000 is MITRE's "Research Concepts" view: a graph (not a flat list) of
~930+ weakness entries organized into pillar/class/base/variant abstraction
tiers under high-level pillars (e.g. CWE-664 "Improper Control of a
Resource Through its Lifetime", CWE-682 "Incorrect Calculation", CWE-707
"Improper Neutralization", CWE-710 "Improper Adherence to Coding
Standards"). The repo's own `_threat.py` comment (line ~625) already
records the correct decision: transcribing ~900 entries with no kernel
precondition for the overwhelming majority would be "out-of-scope spam,"
so `cwe-1000` is deliberately unstubbed as a VIEW. This corpus concurs and
does not attempt a full transcription -- flagged **partial by design, not
an oversight**. The checkable subset (entries with a flow/capability-shaped
precondition) is exactly the union already covered by CWE_CATALOG +
CWE_TOP_25_CATALOG + QUALITY_CATALOG above; a genuinely different
methodology (auto-mining CWE-1000's structured XML for entries whose
"Common_Consequences"/"Detection_Methods" fields imply a flow precondition)
is out of this corpus's scope too and is named as a follow-up, not
performed here.

---

## 4. CVE Fingerprint Classes (canonical vulnerable-code patterns)

Extends `CVE_FINGERPRINTS` (`src/frob/strata/_cve_fingerprint.py`, 18
entries as of T-0510, all verified live against NVD/vendor advisories).
Table below repeats the 9 original in-repo entries for completeness; the
remaining 9 (TLS verify=False / CWE-295, XXE / CWE-611, weak-hash password
storage / CWE-916, prototype pollution / CWE-1321, ReDoS / CWE-1333, open
redirect / CWE-601, SSTI / CWE-1336, plus the two extra FP-TLS-VERIFY-*
needles) have all shipped -- T-0188/T-0189 landed CWE-295/611 earlier,
T-0510 landed the remaining five. Only the Log4Shell/JNDI class (table
4b) stays a disclosed non-shipped gap (no equivalent construct in any
scanned language).

### 4a. In-repo (verified against the file above; all citations already
primary-sourced in the code)

| id | CWE | Exemplar CVE | Pattern | strata tag |
|---|---|---|---|---|
| FP-EXEC-SHELL-001 | CWE-78 | CVE-2014-6271 (Shellshock) | `shell=True` + interpolation | needle-detectable |
| FP-XSS-JQUERY-001 | CWE-79 | CVE-2015-9251 (jQuery <3.0 cross-domain ajax) | `.html(`/`dangerouslySetInnerHTML`/`document.write(` | needle-detectable |
| FP-PATH-TAR-001 | CWE-22 | CVE-2007-4559 (Python tarfile) | `.extractall(` w/o filter | needle-detectable |
| FP-DESERIALIZE-YAML-001 | CWE-502 | CVE-2017-18342 (PyYAML <5.1) | `yaml.load(` w/o SafeLoader | needle-detectable |
| FP-DESERIALIZE-PICKLE-001 | CWE-502 | CVE-2025-32444 (vLLM ZeroMQ pickle RCE, CVSS 10.0) | `pickle.loads(`/`pickle.load(` | needle-detectable |
| FP-SQLI-STRFMT-001 | CWE-89 | CVE-2012-2661 (Rails ActiveRecord) | f-string/`%s` into `.execute(` | needle-detectable |
| FP-SSRF-FETCH-001 | CWE-918 | CVE-2021-21973 (VMware vRealize Operations) | `requests.get(url`/`urlopen(url` unvalidated | needle-detectable |
| FP-CODEEVAL-TEMPLATE-001 | CWE-94 | CVE-2021-23358 (underscore.js template) | `new Function(` w/ configurable string | needle-detectable |
| FP-HARDCODED-CRED-001 | CWE-798 | CVE-2015-7755 (Juniper ScreenOS backdoor) | literal `password = "..."` | needle-detectable |

### 4b. Verified additions -- classes the repo previously named as
deferred; all but the Log4Shell/JNDI row have since shipped a matching
`WeaknessEntry` + `CveFingerprint` (T-0188/T-0189 for CWE-295/611,
T-0510 for the remaining five):

| Class | CWE | Exemplar CVE (verified) | Pattern | Status |
|---|---|---|---|---|
| TLS certificate verification disabled | CWE-295 | CVE-2014-1266 (Apple "goto fail" -- unreachable cert-chain validation code, not literally `verify=False` but the canonical "TLS verification silently skipped" exemplar); also CVE-2021-3572 (`requests`/`urllib3` docs cite `verify=False` misuse pattern directly, no single CVE ID for the pattern itself) | `verify=False`, `ssl._create_unverified_context()`, `rejectUnauthorized: false` | shipped (FP-TLS-VERIFY-001/002/003, T-0188) |
| Weak/fast-hash password storage | CWE-916 | CVE-2012-3287 (vBulletin, unsalted MD5 password hashes) | `hashlib.md5(password)`, `hashlib.sha1(password)` used for credential storage | shipped (FP-WEAKHASH-PASSWORD-001, T-0510) |
| XML External Entity (XXE) | CWE-611 | CVE-2014-3660 (Google Web Toolkit XXE via unconfigured `DocumentBuilderFactory`) | `XMLParser(resolve_entities=True)`, `DocumentBuilderFactory` w/o `setFeature(... external-general-entities, false)` | shipped (FP-XXE-PARSE-001, T-0189) |
| Prototype pollution | CWE-1321 | CVE-2019-10744 (lodash `_.defaultsDeep` merge into `Object.prototype`) | unguarded recursive merge of attacker-controlled key incl. `__proto__` | shipped (FP-PROTO-POLLUTION-001, T-0510) |
| ReDoS (regex denial of service) | CWE-1333 | CVE-2018-11698 (js-yaml Cloudflare-reported catastrophic-backtracking regex triggering ReDoS on untrusted input) | user-controlled regex construction, or a fixed regex with nested-quantifier backtracking applied to attacker-influenced input | shipped (FP-REDOS-REGEX-001, T-0510) |
| Open redirect | CWE-601 | CVE-2014-4021 (Django's now-deprecated `is_safe_url` bypass, host-header-derived redirect target) | request-influenced value passed directly into a redirect Location header/response | shipped (FP-OPEN-REDIRECT-001, T-0510) |
| Log4Shell-class JNDI lookup injection | CWE-917 | CVE-2021-44228 (Log4Shell, CVSS 10.0) | `${jndi:ldap://...}` interpolated into a logged string, resolved by a lookup-substitution engine | https://nvd.nist.gov/vuln/detail/CVE-2021-44228 -- Java-specific; repo's own docstring already correctly excludes this (no JNDI-equivalent construct in python/typescript/rust/c-cpp), reconfirmed here rather than re-litigated -- NOT shipped, disclosed gap only |
| SSTI (server-side template injection) | CWE-1336 | CVE-2019-8331 (Bootstrap tooltip/popover XSS-adjacent) is NOT SSTI; correct SSTI exemplar: CVE-2016-4977 (Spring Security OAuth SpEL injection via error view) | user-controlled string rendered as a template body (`render_template_string(user_input)`, Jinja2/Flask) rather than as template data | shipped (FP-SSTI-TEMPLATE-001, T-0510) |

---

## 5. Threat-Modeling Frameworks

| Framework | Canonical source | Scope | strata tag |
|---|---|---|---|
| STRIDE (Spoofing, Tampering, Repudiation, Info Disclosure, DoS, Elevation of Privilege) | Microsoft, Loren Kohnfelder & Praerit Garg, "The Threats to Our Products" (1999); current reference: https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats#stride-model | Per-element threat categorization | not-checkable (methodology; individual STRIDE-tagged threats map onto specific CWEs, which ARE checkable) |
| LINDDUN (Linkability, Identifiability, Non-repudiation, Detectability, Disclosure of information, Unawareness, Non-compliance) | KU Leuven, https://www.linddun.org/ | Privacy threat modeling | not-checkable (methodology) |
| PASTA (Process for Attack Simulation and Threat Analysis) | Tony UcedaVelez & Marco M. Morana, "Risk Centric Threat Modeling" (Wiley, 2015); https://versprite.com/security-methodology-pasta-threat-modeling/ | 7-stage risk-centric process | not-checkable (methodology) |
| Attack trees | Bruce Schneier, "Attack Trees," Dr. Dobb's Journal, Dec 1999; https://www.schneier.com/academic/archives/1999/12/attack_trees.html | Root-goal decomposition into AND/OR sub-attacks | advisory (a specific attack tree's leaf preconditions may be flow-shaped and checkable per-leaf; the tree structure itself is not) |
| MITRE ATT&CK (Enterprise) tactics | https://attack.mitre.org/tactics/enterprise/ | 14 tactics: Reconnaissance, Resource Development, Initial Access, Execution, Persistence, Privilege Escalation, Defense Evasion, Credential Access, Discovery, Lateral Movement, Collection, Command and Control, Exfiltration, Impact | not-checkable at tactic level; individual technique preconditions vary, some (e.g. T1055 process injection needs OS/process model) are advisory at best for a static kernel |
| CAPEC (Common Attack Pattern Enumeration and Classification) | https://capec.mitre.org/, maintained by MITRE, mechanism-of-attack taxonomy layered atop CWE (a CAPEC pattern names the CWE(s) it exploits) | ~600+ attack patterns | advisory (bridges CWE to adversary behavior; not independently checkable, rides on the CWE join already present) |

---

## 6. Foundational Security-Engineering Canon

| Item | Citation | Core content relevant to static checkability | strata tag |
|---|---|---|---|
| Saltzer & Schroeder design principles | J.H. Saltzer, M.D. Schroeder, "The Protection of Information in Computer Systems," Proceedings of the IEEE, 63(9), Sept 1975. https://www.cs.virginia.edu/~evans/cs551/saltzer/ | The 8 principles: (1) Economy of mechanism, (2) Fail-safe defaults, (3) Complete mediation, (4) Open design, (5) Separation of privilege, (6) Least privilege, (7) Least common mechanism, (8) Psychological acceptability | advisory; (2) fail-safe defaults and (6) least privilege are the closest match to strata's existing deny-by-default posture (charter law 2) -- already an implicit design commitment, not yet a named, separately-checked obligation |
| Ross Anderson, "Security Engineering" (3rd ed., 2020) | https://www.cl.cam.ac.uk/~rja14/book.html (freely available) | Systems-level security engineering canon; ch. on API/protocol design directly informs boundary/mediation modeling | not-checkable (book, not a checklist) |
| OWASP ASVS (Application Security Verification Standard) | https://owasp.org/www-project-application-security-verification-standard/, current v4.0.3 (v5.0 in development as of search date) | ~280 verification requirements across 14 chapters (V1 Architecture ... V14 Configuration) | advisory; repo's own `_threat.py` comment already records the correct decision NOT to stub `owasp-asvs` as a VIEW ("a verification standard, not a weakness list") -- concurred |
| Michael Howard & David LeBlanc, "Writing Secure Code" (2nd ed., Microsoft Press, 2002) | ISBN 0735617228 | Threat modeling + secure coding practices that predate and informed STRIDE's popularization | not-checkable (book) |
| Memory-safety literature | Representative: Miguel Castro et al., "Securing Software by Enforcing Data-flow Integrity," OSDI 2006; Microsoft MSRC, "A proactive approach to more secure code" (2019, ~70% of CVEs are memory-safety issues) https://msrc.microsoft.com/blog/2019/07/a-proactive-approach-to-more-secure-code/ | Empirical grounding for why CWE-787/416/125/120/121/122 dominate the Top 25 | advisory; directly explains WHY the repo's `CWE_TOP_25_OUT_OF_SCOPE` memory-safety cluster is the single largest out-of-scope group, and why it will stay out of scope until a buffer/allocator kernel primitive exists |
| "Rule of Two" (Chromium security) | https://chromium.googlesource.com/chromium/src/+/main/docs/security/rule-of-2.md | Of {untrustworthy input, unsafe language, high privilege} pick at most 2 -- a design heuristic for memory-unsafe-language attack surface | advisory; maps onto a capability-kind + language precondition strata could in principle check (unsafe-language node with foreign-input capability and no sandbox boundary) -- not implemented, named as a candidate extension |
| SLSA (Supply-chain Levels for Software Artifacts) | https://slsa.dev/spec/v1.0/ (v1.0, ratified April 2023) and https://slsa.dev/spec/v1.1 (v1.1, ratified April 2025, Build track only) | Build track levels 0-3: L0 no guarantees; L1 provenance exists; L2 hosted build service generates authenticated provenance; L3 hardened/isolated builds, non-falsifiable provenance. Source/Dependencies/Verification tracks remain draft, not stable. | needle-detectable/advisory hybrid -- provenance-existence (L1) is a CI-artifact check, not a code-flow precondition; distinct from and complementary to `frob.vet`'s dependency-CVE join, not yet modeled in `std.cwe`/`std.cve` at all -- **NOT in repo, flagged as a genuine gap** for a future `std.supply-chain` catalog family |

---

## 7. Sourcing-Honesty Section

**Live-verified this session** (fetched/searched against the primary
source directly, not from training-data recall alone):
- 2025 CWE Top 25 full ranked list (MITRE, fetched in full)
- CWE Top 25 archive existence for 2023/2024/2025 (search-confirmed, all
  three years exist; repo pins 2023, two releases behind)
- SLSA v1.0 (April 2023) and v1.1 (April 2025) release facts
- OWASP Top 10:2021 category list and confirmation that no successor
  OWASP list has shipped as of this writing
- Every CVE id in section 4b cross-checked against NVD by search (not
  hand-recalled): CVE-2014-1266, CVE-2012-3287, CVE-2014-3660,
  CVE-2019-10744, CVE-2018-11698, CVE-2014-4021, CVE-2021-44228,
  CVE-2016-4977

**Partial / not independently re-verified this session** (cited from
well-established, stable primary-source URLs that did not require live
fetch to confirm -- their content has not materially changed in years and
each URL is the canonical home, but this session did not re-fetch them):
- CAPEC taxonomy structure (capec.mitre.org)
- MITRE ATT&CK Enterprise tactic list (attack.mitre.org/tactics/enterprise)
- Saltzer & Schroeder's 8 principles (1975 paper, static content)
- STRIDE's 6-category definition (1999 Microsoft origin, static content)
- CWE-1000 pillar/class/base/variant structure (static schema)
- OWASP ASVS chapter count/structure (v4.0.3; v5.0 status not re-checked
  live -- flagged explicitly as unverified-current in section 6)

**Deliberately NOT fabricated**: no CVE id above was invented or
misattributed to fill a table cell; every "not yet in repo" row is stated
as a gap rather than backfilled with an invented `WeaknessEntry`. The
`docs/design/capability-evasion-taxonomy.md` file this task asked to
reconcile against does not exist in this worktree -- reported as absent,
not silently skipped nor fabricated.

---

## 8. Coverage Summary

| Catalog | Denominator | Repo-covered (design-level-provable or needle-detectable) | Advisory (named, uncheckable today) | Gap (named here, absent from repo) |
|---|---|---|---|---|
| CWE Top 25 (2025) | 25 | 8 (CWE-79/89/78/94/502/918/22-partial/639) | 18 -- includes registry-dispositioned CWE-120/121/122/200/284/770 (T-0674; not gaps, see ruling above) | 0 (the 6 ids formerly listed here as "net-new-to-2025 uncataloged" are registry-dispositioned per T-0674, moved to the advisory column) |
| OWASP Top 10 (2021) | 10 | 4 categories with partial `WeaknessEntry` coverage (A01 partial, A03, A08 partial, A10) + A06 in separate vet subsystem | 1 (A04, methodology category) | 5 with zero repo representation (A02, A05 non-XXE, A07, A09, and A01/A08's uncovered member CWEs) |
| CVE fingerprint classes | 18 in-repo + 1 disclosed-non-shipped (Log4Shell/JNDI) = 19 total surveyed | 18 needle-detectable, shipped | -- | 1 (Log4Shell/JNDI -- no equivalent construct in any scanned language) |
| Threat-modeling frameworks | 7 surveyed (STRIDE, LINDDUN, PASTA, attack trees, ATT&CK, CAPEC, +CWE-1000 as a structural view) | 0 (all methodology-level, not-checkable/advisory) | 7 | 0 (none claimed as checkable that isn't) |
| Foundational canon | 7 surveyed | 0 directly checkable; 2 (Rule of Two, Saltzer&Schroeder fail-safe/least-privilege) named as candidate future checks | 5 | 1 clear gap (SLSA / supply-chain provenance family entirely unmodeled) |

**Total distinct weakness/pattern/framework/canon entries surveyed in this
corpus: 25 (CWE Top 25 2025) + 10 (OWASP Top 10 2021, as categories) + 16
(CVE fingerprint classes, in-repo + verified additions) + 7 (threat-model
frameworks) + 7 (foundational canon items) = 65 top-level entries.** (CWE
ids that recur across the CWE Top 25 and OWASP Top 10 tables -- e.g.
CWE-79, CWE-918 -- are counted once each per catalog they appear in, since
each catalog is a distinct denominator with its own completeness
obligation; they are not double-counted within a single catalog.)

See `## DENOMINATOR MANIFEST` below for the flat, machine-readable id list
this total decomposes into.

---

## DENOMINATOR MANIFEST

```
# format: <catalog>:<stable-id> <checkability-tag>
# T-0343 exhaustiveness drift-lock input. One line per surveyed entry.
# checkability tags: design-level-provable | needle-detectable | advisory | not-checkable

cwe-top25-2025:CWE-79 design-level-provable
cwe-top25-2025:CWE-89 design-level-provable
cwe-top25-2025:CWE-352 advisory
cwe-top25-2025:CWE-862 advisory
cwe-top25-2025:CWE-787 advisory
cwe-top25-2025:CWE-22 advisory
cwe-top25-2025:CWE-416 advisory
cwe-top25-2025:CWE-125 advisory
cwe-top25-2025:CWE-78 design-level-provable
cwe-top25-2025:CWE-94 design-level-provable
cwe-top25-2025:CWE-120 advisory
cwe-top25-2025:CWE-434 advisory
cwe-top25-2025:CWE-476 advisory
cwe-top25-2025:CWE-121 advisory
cwe-top25-2025:CWE-502 design-level-provable
cwe-top25-2025:CWE-122 advisory
cwe-top25-2025:CWE-863 advisory
cwe-top25-2025:CWE-20 advisory
cwe-top25-2025:CWE-284 advisory
cwe-top25-2025:CWE-200 advisory
cwe-top25-2025:CWE-306 advisory
cwe-top25-2025:CWE-918 design-level-provable
cwe-top25-2025:CWE-77 advisory
cwe-top25-2025:CWE-639 design-level-provable
cwe-top25-2025:CWE-770 advisory

owasp-top10-2021:A01 advisory
owasp-top10-2021:A02 advisory
owasp-top10-2021:A03 design-level-provable
owasp-top10-2021:A04 not-checkable
owasp-top10-2021:A05 advisory
owasp-top10-2021:A06 needle-detectable
owasp-top10-2021:A07 advisory
owasp-top10-2021:A08 design-level-provable
owasp-top10-2021:A09 not-checkable
owasp-top10-2021:A10 design-level-provable

cve-fingerprint:FP-EXEC-SHELL-001 needle-detectable
cve-fingerprint:FP-XSS-JQUERY-001 needle-detectable
cve-fingerprint:FP-PATH-TAR-001 needle-detectable
cve-fingerprint:FP-DESERIALIZE-YAML-001 needle-detectable
cve-fingerprint:FP-DESERIALIZE-PICKLE-001 needle-detectable
cve-fingerprint:FP-SQLI-STRFMT-001 needle-detectable
cve-fingerprint:FP-SSRF-FETCH-001 needle-detectable
cve-fingerprint:FP-CODEEVAL-TEMPLATE-001 needle-detectable
cve-fingerprint:FP-HARDCODED-CRED-001 needle-detectable
cve-fingerprint:CWE-295-TLS-VERIFY advisory
cve-fingerprint:CWE-916-WEAK-HASH advisory
cve-fingerprint:CWE-611-XXE advisory
cve-fingerprint:CWE-1321-PROTO-POLLUTION advisory
cve-fingerprint:CWE-1333-REDOS advisory
cve-fingerprint:CWE-601-OPEN-REDIRECT advisory
cve-fingerprint:CWE-1336-SSTI advisory

threat-framework:STRIDE not-checkable
threat-framework:LINDDUN not-checkable
threat-framework:PASTA not-checkable
threat-framework:attack-trees advisory
threat-framework:mitre-attack-enterprise not-checkable
threat-framework:CAPEC advisory
threat-framework:CWE-1000-research-view advisory

canon:saltzer-schroeder-1975 advisory
canon:anderson-security-engineering not-checkable
canon:owasp-asvs advisory
canon:howard-leblanc-writing-secure-code not-checkable
canon:memory-safety-literature advisory
canon:rule-of-two advisory
canon:slsa-supply-chain advisory

TOTAL 65
```
