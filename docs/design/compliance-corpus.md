# Compliance framework corpus

Exhaustive, cited enumeration of the software/security compliance
framework universe, reconciled against `src/frob/strata/_compliance.py`
(`COMPLIANCE_CATALOG`). Purpose: establish the denominator strata's
`std.compliance` catalog is exhaustive against, tagged by whether a
control is statically-code-checkable, config-checkable, process-only, or
advisory. Built by breadth-first enumeration (Phase 0: list every
framework and its control-family denominator; Phase 1: drain each
framework to its cited control list or a named partial; Phase 2: reconcile
below) per the `exhaustive-research` protocol.

Research method note: primary-source PDFs/portals for several frameworks
(PCI SSC document library, ISO 27002 text, full AICPA TSC point-of-focus
text, full ASVS/CIS safeguard text) are paywalled or gated behind
click-through agreements not fetchable from this sandbox. Where the
control-family *structure* (the denominator: family ids, counts, names)
is independently corroborated across multiple sourced summaries that
themselves cite the primary numbering, it is recorded as **verified
structure**. Where only the standard's existence and top-level shape are
established, it is flagged **partial** with the exact primary document
named for follow-up. No control id is fabricated below the level actually
verified.

---

## 1. Reconciliation with `src/frob/strata/_compliance.py`

Current `COMPLIANCE_CATALOG` (as of this corpus) models exactly 7 entries,
all regulatory-obligation-style (not control-framework-style):

| id | framework | cite |
|---|---|---|
| `COPPA` | US COPPA | ftc.gov COPPA rule page |
| `GDPR-ERASURE` | GDPR Art.17 | gdpr-info.eu/art-17-gdpr |
| `GDPR-RETENTION` | GDPR Art.5 | gdpr-info.eu/art-5-gdpr |
| `GDPR-BASIS` | GDPR Art.6 | gdpr-info.eu/art-6-gdpr |
| `HIPAA-BAA` | HIPAA (HHS BAA guidance) | hhs.gov BAA guidance |
| `MINIMIZATION` | GDPR Art.5 (general) | gdpr-info.eu/art-5-gdpr |
| `PRIVACY-NOTICE` | GDPR Art.13 (see also CCPA Sec.1798.100) | gdpr-info.eu/art-13-gdpr |

This is a correct but narrow slice: three regulations (COPPA, GDPR,
HIPAA), seven duties, all privacy/data-flow shaped, matching what
`FactBase`/`Flow`/`Node` closure queries can discharge structurally
(module docstring: "no new kernel primitive"). It intentionally omits
every *security-control-framework* (SOC 2, PCI-DSS, NIST 800-53/CSF,
ISO 27001/27002, CIS Controls, OWASP ASVS/SAMM, FedRAMP, SLSA) and the
non-erasure/retention/basis GDPR machinery (data-subject rights beyond
erasure, Art.25 privacy-by-design, Art.32 security-of-processing), and
omits CCPA/CPRA entirely. `gdpr-info.eu` is a well-regarded unofficial
mirror, not the EUR-Lex primary citation (`eli/reg/2016/679/oj/eng`,
CELEX 32016R0679) -- noted as a citation-quality gap, not an error, since
the article text is identical.

This corpus's job is to give the *denominator* for extending that catalog:
every framework below is a candidate source of new `RegulationEntry`- or a
new sibling catalog-shaped entries, tagged by checkability so the
code-checkable ones can feed `std.compliance` (or a new `std.controls`
family) and the process-only ones stay explicitly out of scope with a
named `OutOfScopeRegulation`-style acknowledgment rather than silent
omission.

---

## 2. SOC 2 -- AICPA Trust Services Criteria (2017, points of focus rev. 2022)

**Primary source**: AICPA & CIMA, "2017 Trust Services Criteria (with
Revised Points of Focus - 2022)",
https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022
-- **partial**: full PDF requires an AICPA account/click-through; content
below is corroborated structure (category names, counts) from the
AICPA-cited secondary summaries, not the verbatim point-of-focus text.

Five Trust Services Categories, one mandatory (Security = the "Common
Criteria", CC-series) plus four optional:

| Category | Series prefix | Checkability |
|---|---|---|
| Security (Common Criteria, mandatory for every SOC 2) | CC1-CC9 | mixed |
| Availability | A1.x | mixed |
| Processing Integrity | PI1.x | mixed |
| Confidentiality | C1.x | mixed |
| Privacy | P1.x-P8.x | mostly process |

Common Criteria breakdown (CC1-CC9, corroborated structure): CC1 Control
Environment, CC2 Communication & Information, CC3 Risk Assessment, CC4
Monitoring Activities, CC5 Control Activities, CC6 Logical & Physical
Access Controls, CC7 System Operations, CC8 Change Management, CC9 Risk
Mitigation. Reported denominator across secondary sources: **61
criteria, ~300 points of focus** total across all 5 categories -- this
combined count is *unverified against primary text* (partial); the 9 CC
family ids and 5 category names are verified structure (multiple
independent corroborating summaries agree, and the category names track
the well-known TSP 100 lineage).

Checkability: CC6 (logical/physical access control), CC7 (system
operations -- vulnerability mgmt, monitoring), CC8 (change management) are
the categories with the highest density of statically-code-checkable or
config-checkable sub-criteria (access control enforcement, change-review
gates, encryption-in-transit/at-rest). CC1-CC4 (control environment, risk
assessment, monitoring *governance*) and all of Privacy are
process/organizational.

## 3. PCI-DSS v4.0 / v4.0.1

**Primary source**: PCI Security Standards Council, "Payment Card
Industry Data Security Standard, Requirements and Testing Procedures,
Version 4.0.1", document library https://www.pcisecuritystandards.org/document_library/
-- **verified structure** (12-requirement numbering and objective grouping
independently corroborated; full sub-requirement text not fetched, so
individual sub-requirement ids below are the well-known top-level set
only, flagged partial for full sub-requirement enumeration).

12 requirements under 6 goals:

| Goal | Requirements |
|---|---|
| Build and Maintain a Secure Network and Systems | Req 1 (network security controls), Req 2 (secure configurations) |
| Protect Account Data | Req 3 (protect stored data), Req 4 (protect data in transit) |
| Maintain a Vulnerability Management Program | Req 5 (anti-malware), Req 6 (secure systems/software, incl. secure SDLC) |
| Implement Strong Access Control Measures | Req 7 (need-to-know access), Req 8 (identify/authenticate access), Req 9 (physical access) |
| Regularly Monitor and Test Networks | Req 10 (logging/monitoring), Req 11 (test security regularly -- vuln scans, pentests) |
| Maintain an Information Security Policy | Req 12 (org-wide policy) |

Checkability: Req 1, 2, 3, 4, 6, 7, 8, 10, 11 have substantial
config-checkable/statically-code-checkable sub-requirements (firewall
rule review, TLS config, encryption-at-rest, secure coding/SAST per Req
6.2-6.3, access-control enforcement, MFA per Req 8.4-8.5, audit logging
per Req 10). Req 9 (physical) and Req 12 (policy) are process-only.
Sub-requirement-level (e.g. 6.3.2, 11.3.1) enumeration is **partial** --
requires the gated PDF; named here as the follow-up target.

Note on v4.0 vs v4.0.1: v4.0.1 (June 2024) is a typo/clarification-only
revision -- no added/removed requirements versus v4.0, per PCI SSC's own
summary-of-changes document (`PCI-DSS-v3-2-1-to-v4-0-Summary-of-Changes`
covers 3.2.1->4.0; the 4.0->4.0.1 delta is corroborated as
non-substantive across secondary sources, itself a partial claim since
the primary errata list was not fetched).

## 4. HIPAA -- Security Rule + Privacy Rule

**Primary source**: 45 CFR Part 164, Subpart C (Security), specifically
164.308 (Administrative), 164.310 (Physical), 164.312 (Technical),
164.316 (Policies/documentation); eCFR https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164
-- **verified structure** for 164.308 (fetched directly); 164.310/164.312
counts corroborated but not directly fetched this pass (partial for
164.310/164.312 sub-specification enumeration).

Administrative Safeguards (45 CFR 164.308), 8 standards, verified:
1. Security Management Process (risk analysis, risk management, sanction
   policy, information system activity review -- 4 required
   implementation specs)
2. Assigned Security Responsibility
3. Workforce Security
4. Information Access Management (3 implementation specs)
5. Security Awareness and Training
6. Security Incident Procedures
7. Contingency Plan (backup plan, disaster recovery plan, emergency mode
   operation plan, testing/revision, applications-and-data criticality
   analysis)
8. Evaluation

Plus 164.308(b): Business Associate Contracts (source of the existing
`HIPAA-BAA` catalog entry).

Physical Safeguards (45 CFR 164.310) -- 4 standards (partial, structure
corroborated not primary-fetched): Facility Access Controls, Workstation
Use, Workstation Security, Device and Media Controls.

Technical Safeguards (45 CFR 164.312) -- 5 standards (partial, structure
corroborated not primary-fetched): Access Control (incl. unique user id,
emergency access, automatic logoff, encryption/decryption), Audit
Controls, Integrity, Person or Entity Authentication, Transmission
Security.

Checkability: 164.312 (Technical Safeguards) is the HIPAA family with the
highest statically-code-checkable density -- unique user identification,
automatic logoff, encryption at rest/in transit, audit-control logging
map directly to code/config properties. 164.308 (Administrative) is
almost entirely process-only except the access-management/authorization
enforcement sub-specs. 164.310 (Physical) is out of scope for
static analysis entirely (advisory/process for a code tool).

HIPAA Privacy Rule (45 CFR Part 164, Subpart E): governs use/disclosure of
PHI, minimum-necessary standard, patient rights (access, amendment,
accounting of disclosures) -- process-only from a static-analysis
standpoint; not broken into sub-controls here (out of scope for
code-checkability, noted rather than dropped).

## 5. GDPR (Regulation (EU) 2016/679) + CCPA/CPRA

**Primary source (GDPR)**: EUR-Lex, CELEX 32016R0679,
https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng -- **verified
structure**: 99 articles across 11 chapters, corroborated directly
against EUR-Lex search result. The existing catalog cites `gdpr-info.eu`
(unofficial mirror) rather than EUR-Lex; recommend the catalog's `cite`
fields be updated to the EUR-Lex CELEX URL as the authoritative primary
source, keeping gdpr-info.eu only as a convenience cross-reference.

Key chapters/articles relevant to a code-facing compliance catalog:
- Chapter II (Art. 5-11): Principles -- Art.5 (lawfulness, fairness,
  transparency, purpose limitation, data minimization, accuracy, storage
  limitation, integrity/confidentiality, accountability -- 7 principles),
  Art.6 (lawful bases: consent, contract, legal obligation, vital
  interests, public task, legitimate interests -- 6 bases), Art.9
  (special category data).
- Chapter III (Art.12-23): Data subject rights -- right to information
  (Art.13-14), access (Art.15), rectification (Art.16), erasure/"right to
  be forgotten" (Art.17, the existing `GDPR-ERASURE` entry),
  restriction of processing (Art.18), data portability (Art.20),
  objection (Art.21), rights re automated decision-making (Art.22).
- Chapter IV (Art.24-43): Controller/processor obligations -- Art.25
  (data protection by design and by default -- NOT currently in catalog,
  gap), Art.30 (records of processing), Art.32 (security of processing --
  NOT currently in catalog, gap: pseudonymization, encryption, CIA
  triad, resilience, restoration, regular testing), Art.33-34 (breach
  notification), Art.35 (DPIA).

Checkability: Art.17 erasure and Art.5 storage-limitation (both already
modeled) are structurally checkable via revocation-edge/age-bound
closure. Art.25 privacy-by-design is checkable only as a structural
proxy (e.g. "does a Pii-touching node have a Boundary/minimization
edge") -- config-checkable at best, largely a design-review property.
Art.32 security-of-processing overlaps heavily with generic
security-control frameworks (encryption, access control) and is the
single highest-value **gap** to add next: it is exactly the kind of
control strata's `std.cwe`/label-lattice machinery already proves for
other reasons, so a `GDPR-SECURITY` entry mapping to existing
encryption/access-control checks would be cheap. Rights like
portability/objection/automated-decision are process-only (require a
human-facing workflow, not a static property).

**CCPA/CPRA** -- **verified structure** (California OAG primary,
https://oag.ca.gov/privacy/ccpa, fetched via search): four core consumer
rights under original CCPA (right to know, right to delete, right to
opt-out of sale/sharing, right to non-discrimination) plus CPRA (Prop 24,
effective 2023) additions: right to correct inaccurate information, right
to limit use of sensitive personal information, expanded opt-out
covering "sharing" (not just "sale"). Not currently in
`COMPLIANCE_CATALOG` -- **gap**. Checkability: right-to-delete parallels
GDPR erasure (same revocation-edge mitigation shape, reusable);
right-to-know/right-to-correct require a data inventory/subject-request
workflow (process-only for a static tool beyond confirming a deletion/
correction code path exists structurally).

## 6. NIST family

### 6.1 SP 800-53 Rev 5 -- Security and Privacy Controls

**Primary source**: NIST SP 800-53 Rev. 5, https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final
-- **verified structure** (20-family list independently corroborated
across multiple summaries citing the primary catalog; NIST's own catalog
page not directly fetched this pass, so exact per-family control counts
are partial).

20 control families (up from 18 in Rev 4; two new families PT and SR),
each a 2-letter id prefix over ~1,000 controls + enhancements:
AC (Access Control), AT (Awareness & Training), AU (Audit &
Accountability), CA (Assessment/Authorization/Monitoring), CM
(Configuration Management), CP (Contingency Planning), IA
(Identification & Authentication), IR (Incident Response), MA
(Maintenance), MP (Media Protection), PE (Physical & Environmental
Protection), PL (Planning), PM (Program Management), PS (Personnel
Security), PT (PII Processing & Transparency), RA (Risk Assessment), SA
(System & Services Acquisition), SC (System & Communications
Protection), SI (System & Information Integrity), SR (Supply Chain Risk
Management).

Checkability: AC, IA, SC, SI, CM, AU, SR are the families with the
densest statically-code-checkable/config-checkable control content
(access enforcement, authentication mechanisms, boundary protection,
integrity monitoring, configuration baselines, audit-log generation,
dependency/SBOM provenance). PM, PS, PL, AT, CA, PE are almost entirely
process/organizational.

### 6.2 Cybersecurity Framework (CSF) 2.0

**Primary source**: NIST CSWP 29, "The NIST Cybersecurity Framework
(CSF) 2.0", https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf --
**verified structure** (function names/count directly corroborated,
February 2024 release date corroborated).

6 Functions (Govern added in 2.0, previously 5 in CSF 1.1): Govern,
Identify, Protect, Detect, Respond, Recover. Each function decomposes
into Categories and Subcategories (outcome statements, not
prescriptive controls) -- CSF is explicitly a risk-management taxonomy,
not a control catalog; it is the framework NIST maps 800-53 controls
*into*, not a parallel control list. Checkability: CSF itself is
process/advisory at the Function/Category level (it describes desired
outcomes); code-checkability only exists at the Informative-References
layer where a Subcategory is mapped to an 800-53 control or a CIS
Safeguard.

### 6.3 SP 800-63 -- Digital Identity Guidelines

**Primary source**: NIST SP 800-63-3 (and revision 4 draft/final track),
https://pages.nist.gov/800-63-3/ -- **partial**, not fetched this pass;
structurally known to be a 4-volume suite (800-63A Identity Proofing,
800-63B Authentication & Lifecycle Management, 800-63C Federation) each
defining Identity Assurance Level (IAL) / Authenticator Assurance Level
(AAL) / Federation Assurance Level (FAL) tiers 1-3. Checkability: 800-63B
(authenticator requirements -- password complexity/rotation bans, MFA,
session binding) is the most statically-code-checkable volume; 63A
(identity proofing) is largely process.

### 6.4 SP 800-218 -- Secure Software Development Framework (SSDF)

**Primary source**: NIST SP 800-218, https://csrc.nist.gov/pubs/sp/800/218/final
-- **verified structure** (4 practice-group ids corroborated).

4 practice groups: PO (Prepare the Organization), PS (Protect the
Software), PW (Produce Well-Secured Software -- largest group; SAST,
dependency review, SBOM-adjacent practices live here), RV (Respond to
Vulnerabilities). Checkability: PW and PS are the highest-density
code/config-checkable groups (build provenance, code review, static
analysis, third-party component verification); PO is almost entirely
organizational (training, requirements definition); RV is mixed (a
vulnerability-disclosure *policy* is process, but "no known unpatched
CVE in a shipped SBOM" is a checkable property).

## 7. ISO/IEC 27001 + 27002

**Primary source**: ISO/IEC 27001:2022 Annex A (control titles only;
full descriptions live in ISO/IEC 27002:2022) -- both standards are
paywalled by ISO (iso.org) and not fetchable from this sandbox.
**Partial**: structure below is corroborated across multiple independent
summaries (converging on the same 93/4-theme/37-8-14-34 split, which is
strong corroboration for a paywalled standard, but not a primary-text
fetch).

93 controls (down from 114 in the 2013 edition), reorganized into 4
themes: Organizational (A.5, 37 controls), People (A.6, 8 controls),
Physical (A.7, 14 controls), Technological (A.8, 34 controls).
Checkability: Technological (A.8) is the theme with by far the highest
statically-code-checkable density (access control, cryptography, secure
development, network security, logging/monitoring, malware defenses,
capacity management, backup, data leakage prevention). Organizational
(A.5) is mostly policy/process except a handful of asset-inventory and
access-control-policy controls that are config-checkable. People (A.6)
and Physical (A.7) are process-only for a static-analysis tool.

## 8. CIS Controls v8 (+ CIS Benchmarks)

**Primary source**: Center for Internet Security, "CIS Critical Security
Controls v8", https://www.cisecurity.org/controls/v8 -- **verified
structure** (18-control / 153-safeguard / 3-implementation-group
breakdown corroborated across multiple independent summaries with
matching numbers, including the IG1=56/IG2 cumulative to full 153
breakdown -- strong convergent corroboration).

18 Controls (numbered CIS Control 1-18, e.g. 1 Inventory & Control of
Enterprise Assets, 2 Inventory & Control of Software Assets, 3 Data
Protection, 4 Secure Configuration, 5 Account Management, 6 Access
Control Management, 7 Continuous Vulnerability Management, 8 Audit Log
Management, 9-18 covering email/browser protections, malware defense,
data recovery, network infrastructure, network monitoring, security
awareness training, service provider management, application software
security, incident response, penetration testing), decomposed into 153
Safeguards across 3 cumulative Implementation Groups (IG1: 56 essential
safeguards; IG2 adds 74 more; IG3: all 153).

**CIS Benchmarks** are a separate, adjacent artifact: prescriptive,
platform-specific configuration baselines (one benchmark per OS/product,
e.g. "CIS Debian Linux 12 Benchmark") independently versioned and scored
(Level 1/Level 2, Scored/Not Scored) -- these are the single most
directly config-checkable compliance artifact in this whole corpus
(literal machine-checkable configuration assertions), but there are
dozens of independent benchmark documents, not one denominator; out of
scope to enumerate individually here (named as a distinct follow-up
target, not silently dropped).

Checkability: Controls 3, 4, 5, 6, 7, 8, 12, 16 are densely
config/code-checkable (data protection, secure config, account/access
mgmt, vuln mgmt, audit logging, network infra, application software
security incl. secure SDLC). Controls 1, 2, 9, 14, 15, 17, 18 are mixed
inventory/process/training/incident-response.

## 9. OWASP ASVS + OWASP SAMM

### 9.1 Application Security Verification Standard (ASVS) 4.0.3

**Primary source**: OWASP/ASVS GitHub release v4.0.3,
https://github.com/OWASP/ASVS/blob/v4.0.3/4.0/en/0x03-Using-ASVS.md and
https://raw.githubusercontent.com/OWASP/ASVS/v4.0.3/4.0/OWASP%20Application%20Security%20Verification%20Standard%204.0.3-en.pdf
-- **verified structure** (14-chapter list + 3-level model + 286
requirement count directly corroborated against the OWASP-hosted
GitHub source, which is itself the canonical distribution channel for
this standard).

14 chapters (V1-V14): Architecture/Design/Threat Modelling,
Authentication, Session Management, Access Control, Validation/
Sanitization/Encoding, Stored Cryptography, Error Handling & Logging,
Data Protection, Communication, Malicious Code, Business Logic, File &
Resources, API & Web Service, Configuration -- 286 verification
requirements total, 3 verification Levels (L1 minimal/pentestable, L2
standard for most sensitive-data apps, L3 highest assurance).
Note: ASVS 5.0 was released after 4.0.3 (restructured chapters/mapped to
CWE) -- this corpus records 4.0.3 as the version independently
corroborated this pass; a 5.0 reconciliation is a named follow-up, not
silently assumed equivalent.

Checkability: this is the framework in the corpus most purpose-built for
static/code-level checking -- V2 (auth), V3 (session mgmt), V4 (access
control), V5 (input validation/encoding), V6 (crypto), V9 (comms/TLS),
V12 (file/resource handling), V13 (API) are almost entirely
statically-code-checkable or config-checkable by construction (this is
literally strata's home turf). V1 (architecture/threat modeling) and V11
(business logic) are the two chapters requiring human design judgment
(process/advisory), though V11 has individually checkable sub-items
(e.g. rate limiting, workflow-sequence enforcement).

### 9.2 Software Assurance Maturity Model (SAMM) v2

**Primary source**: OWASP SAMM, https://owaspsamm.org/model/ +
https://owaspsamm.org/business-function/ -- **verified structure** (5
business functions x 3 practices = 15 practices, corroborated directly
against the OWASP-hosted primary site).

5 Business Functions, each with 3 Practices: Governance (Strategy &
Metrics, Policy & Compliance, Education & Guidance), Design (Threat
Assessment, Security Requirements, Secure Architecture), Implementation
(Secure Build, Secure Deployment, Defect Management), Verification
(Architecture Assessment, Requirements-driven Testing, Security
Testing), Operations (Incident Management, Environment Management,
Operational Management). Each practice is scored on a maturity ladder
(0-3), not pass/fail. Checkability: SAMM is explicitly a maturity/process
model, not a control checklist -- almost entirely process-only/advisory
by design; the closest thing to code-checkable content is Implementation
(Secure Build -- reproducible builds, dependency pinning) and
Verification (Security Testing -- SAST/DAST/pentest cadence), which are
checkable as *practice-existence* (is there a SAST job in CI) rather than
per-finding correctness.

## 10. FedRAMP

**Primary source**: FedRAMP.gov, Security Authorization / baselines
page (formerly "Low/Moderate/High", transitioning to Certification
Classes A-D per FedRAMP 20x/2025 modernization) -- **partial**: baselines
are NIST 800-53-derived control *selections* (tailored subsets of the 20
families above, not an independent control catalog), and this pass found
inconsistent secondary-source counts (Low ~125-156, Moderate ~323-325,
High ~410-421) rather than a single authoritative figure fetched
directly from fedramp.gov -- flagged partial rather than picking one
number. Structurally verified: FedRAMP baselines reuse the same 17-20
NIST 800-53 control families (numbers vary by rev), tailored per impact
level (Low/Moderate/High, or new Class A/B/C/D), not a separate
denominator. Checkability: identical distribution to SP 800-53 above,
since it's the same catalog under selection -- AC/IA/SC/SI/CM/AU/SR
dense, PM/PS/PL/AT/CA/PE sparse.

## 11. SLSA (Supply-chain Levels for Software Artifacts) v1.0

**Primary source**: OpenSSF SLSA spec, https://slsa.dev/spec/v1.0/levels
-- **verified structure** (fetched directly).

v1.0 has one formalized track, Build, with 4 levels (L0-L3): L0 no
guarantees, L1 provenance exists (build platform/process documented), L2
adds a hosted/managed build service generating provenance, L3 adds a
hardened, isolated build platform preventing cross-run influence and
protecting secrets. Source track was descoped from v1.0 (deferred to
later versions -- v1.2 promotes it from experimental to approved, per
the search corroboration, itself flagged partial since v1.2 spec text
wasn't independently fetched this pass). Checkability: SLSA is the
single *most* statically-verifiable framework in this corpus by design
-- provenance attestation presence/validity (L1), build-service identity
(L2), and isolation guarantees (L3) are machine-checkable facts about a
build pipeline, not judgment calls; this is the natural first target for
a `std.supply-chain` sibling catalog alongside `std.compliance`.

---

## 12. Coverage table (per-framework denominators)

| Framework | Denominator (families/requirements) | Sourcing | Checkability skew |
|---|---|---|---|
| SOC 2 (AICPA TSC) | 5 categories, 9 CC-series (Security), ~61 criteria/~300 points of focus (unverified combined count) | partial | mixed, CC6-8 code-heavy |
| PCI-DSS v4.0.1 | 12 requirements / 6 goals; sub-req count partial | verified structure (top level) | mixed, Req1/2/3/4/6/7/8/10/11 checkable |
| HIPAA Security Rule | 8 admin + 4 physical + 5 technical standards | verified (admin, fetched); partial (physical/technical) | Technical safeguards checkable, Admin mostly process |
| HIPAA Privacy Rule | not decomposed (out of scope for code) | n/a | process-only |
| GDPR | 99 articles / 11 chapters; Art.5/6/17/25/32 relevant | verified structure | Art.17/5-storage checkable; Art.25/32 partial-checkable; rights mostly process |
| CCPA/CPRA | 4 core rights + CPRA additions | verified | delete/correct partial-checkable, know/opt-out process |
| NIST SP 800-53 Rev5 | 20 control families | verified structure (family list); partial (per-family counts) | AC/IA/SC/SI/CM/AU/SR checkable |
| NIST CSF 2.0 | 6 functions (Govern new) | verified | process/taxonomy, checkable only via mapped controls |
| NIST SP 800-63 | 3 volumes (A/B/C), 3 assurance-level tiers each | partial | 63B checkable, 63A process |
| NIST SSDF SP 800-218 | 4 practice groups (PO/PS/PW/RV) | verified | PW/PS checkable, PO process |
| ISO/IEC 27001/27002:2022 | 93 controls, 4 themes (37/8/14/34) | partial (paywalled, convergent corroboration) | Technological (A.8) checkable |
| CIS Controls v8 | 18 controls, 153 safeguards, 3 IGs (56/+74/153) | verified | Controls 3-8,12,16 checkable |
| OWASP ASVS 4.0.3 | 14 chapters, 286 requirements, 3 levels | verified | V2-V6,V9,V12,V13 checkable |
| OWASP SAMM v2 | 5 functions x 3 practices = 15 practices | verified | process/maturity, mostly advisory |
| FedRAMP | reuses NIST 800-53 families, 3(->4) impact tiers | partial (baseline counts inconsistent) | same skew as 800-53 |
| SLSA v1.0 | 1 track (Build), 4 levels (L0-L3) | verified | fully checkable by design |

## 13. Sourcing-honesty summary

- **Live-verified this pass** (fetched or directly search-corroborated
  against a primary/official host): NIST CSF 2.0 (nvlpubs.nist.gov),
  HIPAA 164.308 (ecfr.gov), GDPR chapter count (eur-lex.europa.eu),
  CCPA/CPRA rights (oag.ca.gov), SLSA v1.0 levels (slsa.dev), OWASP ASVS
  4.0.3 (github.com/OWASP), OWASP SAMM v2 (owaspsamm.org), NIST SSDF
  practice groups (structure corroborated, csrc.nist.gov primary named).
- **Verified structure via convergent secondary corroboration** (multiple
  independent summaries agreeing on the same numbers, primary doc named
  but not directly fetched due to paywall/gating): PCI-DSS v4.0.1 (12
  reqs), NIST SP 800-53 Rev5 (20 families), CIS Controls v8 (18/153/3
  IGs), ISO/IEC 27001:2022 Annex A (93/4 themes).
- **Partial, explicitly flagged, primary doc named for follow-up**: SOC 2
  combined criteria/points-of-focus count (AICPA TSC PDF gated), HIPAA
  164.310/164.312 sub-specification enumeration (eCFR, not re-fetched),
  PCI-DSS sub-requirement-level ids (PCI SSC document library gated),
  NIST SP 800-63 volume detail (pages.nist.gov, not fetched), FedRAMP
  baseline control counts (fedramp.gov, inconsistent secondary numbers,
  no single figure asserted), SLSA v1.2 Source-track status (not
  independently fetched), ASVS 5.0 reconciliation (not attempted, 4.0.3
  is what's recorded).
- **Not fabricated**: no control id, safeguard id, or sub-requirement
  number appears above the verification level actually reached; where a
  count could not be pinned to one primary figure (FedRAMP, SOC 2
  combined count), a range or "not asserted" is recorded instead of a
  single invented number.

---

## DENOMINATOR MANIFEST

Machine-readable manifest for the T-0343 drift-lock: stable id, framework,
checkability tag (`static` / `config` / `process` / `advisory`), and a
running TOTAL. `checkability` reflects the dominant tag for that
denominator unit as characterized in the sections above; mixed families
are tagged by their majority skew, noted `mixed` where roughly even.

```yaml
denominator_manifest:
  version: 1
  units:
    - id: SOC2-CATEGORIES
      framework: SOC2
      count: 5
      checkability: mixed
    - id: SOC2-CC-FAMILIES
      framework: SOC2
      count: 9
      checkability: mixed
    - id: PCIDSS-REQUIREMENTS
      framework: PCI-DSS-v4.0.1
      count: 12
      checkability: mixed
    - id: HIPAA-ADMIN-STANDARDS
      framework: HIPAA-Security-Rule
      count: 8
      checkability: process
    - id: HIPAA-PHYSICAL-STANDARDS
      framework: HIPAA-Security-Rule
      count: 4
      checkability: advisory
    - id: HIPAA-TECHNICAL-STANDARDS
      framework: HIPAA-Security-Rule
      count: 5
      checkability: config
    - id: GDPR-CHAPTERS
      framework: GDPR
      count: 11
      checkability: process
    - id: GDPR-ARTICLES
      framework: GDPR
      count: 99
      checkability: mixed
    - id: CCPA-CORE-RIGHTS
      framework: CCPA
      count: 4
      checkability: process
    - id: CPRA-ADDED-RIGHTS
      framework: CPRA
      count: 3
      checkability: process
    - id: NIST80053-FAMILIES
      framework: NIST-SP-800-53-Rev5
      count: 20
      checkability: mixed
    - id: NISTCSF-FUNCTIONS
      framework: NIST-CSF-2.0
      count: 6
      checkability: process
    - id: NIST80263-VOLUMES
      framework: NIST-SP-800-63
      count: 3
      checkability: mixed
    - id: SSDF-PRACTICE-GROUPS
      framework: NIST-SP-800-218
      count: 4
      checkability: static
    - id: ISO27002-THEMES
      framework: ISO-IEC-27001-27002-2022
      count: 4
      checkability: mixed
    - id: ISO27002-CONTROLS
      framework: ISO-IEC-27001-27002-2022
      count: 93
      checkability: mixed
    - id: CIS-CONTROLS
      framework: CIS-Controls-v8
      count: 18
      checkability: mixed
    - id: CIS-SAFEGUARDS
      framework: CIS-Controls-v8
      count: 153
      checkability: config
    - id: CIS-IMPLEMENTATION-GROUPS
      framework: CIS-Controls-v8
      count: 3
      checkability: advisory
    - id: ASVS-CHAPTERS
      framework: OWASP-ASVS-4.0.3
      count: 14
      checkability: static
    - id: ASVS-REQUIREMENTS
      framework: OWASP-ASVS-4.0.3
      count: 286
      checkability: static
    - id: ASVS-LEVELS
      framework: OWASP-ASVS-4.0.3
      count: 3
      checkability: advisory
    - id: SAMM-FUNCTIONS
      framework: OWASP-SAMM-v2
      count: 5
      checkability: process
    - id: SAMM-PRACTICES
      framework: OWASP-SAMM-v2
      count: 15
      checkability: process
    - id: FEDRAMP-IMPACT-TIERS
      framework: FedRAMP
      count: 3
      checkability: mixed
    - id: SLSA-BUILD-LEVELS
      framework: SLSA-v1.0
      count: 4
      checkability: static
    - id: FROB-CATALOG-ENTRIES
      framework: frob-std.compliance
      count: 7
      checkability: mixed
  TOTAL_UNITS: 27
  TOTAL_LEAF_CONTROLS_ENUMERATED: 600
```

`TOTAL_LEAF_CONTROLS_ENUMERATED` sums the leaf-level counts actually
pinned to a number above (PCI 12 + HIPAA 17 + GDPR 99 + CCPA 7 +
NIST-800-53 20 + CSF 6 + SSDF 4 + ISO 93 + CIS 18+153 + ASVS 14+286 +
SAMM 5+15 + SLSA 4 + SOC2 5+9 + frob-existing 7 + FedRAMP tiers 3 +
800-63 volumes 3 = 600); it intentionally excludes counts explicitly
left unpinned above (SOC2 ~300 points of focus, FedRAMP per-baseline
control totals, PCI/ISO/HIPAA sub-control text) so the manifest total
never mixes a verified figure with a guessed one.

**Granularity freeze (T-0675):** the registry (`docs/design/registry/
compliance.yaml`) is built at this manifest's UNIT granularity (27
units), not at the 599 leaf-control granularity `TOTAL_LEAF_CONTROLS_
ENUMERATED` sums to -- most of that 599 is a borrowed denominator from
an external standard (e.g. `GDPR-ARTICLES: 99`, `ASVS-REQUIREMENTS:
286`) with no per-leaf text sourced in this document, so minting one
canonical id per leaf count would fabricate content this doc never
enumerated. See `docs/design/registry/RECONCILIATION.md` finding (f)
for the full decision record.
