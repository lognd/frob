<!-- frob:used-by src/frob/gates/_registry_exhaustiveness.py -->
# Registry reconciliation report

Universe: **11 corpus docs** under `docs/design/*.md` on `main` at build
time (the 10 named in the task, plus `cwe-1000-registry.md`, which landed
on `main` mid-pass and was merged into this worktree and folded in --
confirmed via `git show main:docs/design/cwe-1000-registry.md` before this
pass ended; see the "Mid-pass addition" section below). All 11 were read
in full and reconciled. **Registry grand total: 1950 entries.**

Per-domain totals (registry entries built vs. each source doc's own
stated denominator, where it states one):

| Domain / file | Source doc(s) | Registry entries | Source doc's own TOTAL | Match? |
|---|---|---:|---:|---|
| `arch-checks.yaml` (arch-check-catalog portion) | architecture-check-catalog.md | 288 | 288 | yes |
| `arch-checks.yaml` (hardening portion) | structural-linter-adversarial-hardening.md | 23 | none stated (no manifest) | n/a -- see finding (a) |
| `patterns.yaml` (catalog portion) | design-pattern-catalog.md | 325 | 325 | yes |
| `patterns.yaml` (traps portion) | design-pattern-traps-corpus.md | 21 | 21 (own coverage ledger, not a manifest) | yes |
| `system-design.yaml` | system-design-corpus.md | 119 (105 genuine + 14 artifact) | 119 | yes numerically, but see finding (d) |
| `evasion.yaml` | capability-evasion-taxonomy.md | 112 | 112 (own combined-coverage table, not a manifest) | yes |
| `weaknesses.yaml` (CWE portion) | cwe-1000-registry.md | 944 | 944 | yes |
| `weaknesses.yaml` (other portion) | security-corpus.md | 40 | 65 stated in doc's own manifest TOTAL, but that 65 = 25 (cwe-top25, moved to cross-ref below) + 40 (owasp/cve-fp/threat-fw/canon) | yes once the 25 CWEs are correctly attributed to the CWE registry instead of double-counted here -- see finding (e) |
| `compliance.yaml` | compliance-corpus.md | 27 units | 27 units / 599 leaf controls | yes at unit granularity; leaf granularity not id'd in source -- finding (f) |
| `secrets.yaml` + `pii.yaml` | secrets-pii-corpus.md | 10 sections | 10 sections / 56+44 leaf items | yes at section granularity; same caveat as (f) |
| `supply-chain.yaml` | supply-chain-corpus.md | 41 | 39 (doc's own TOTAL field) | **NO -- self-inconsistent, finding (g)** |

**Grand total 1950** = 311 (arch-checks) + 346 (patterns) + 119
(system-design) + 112 (evasion) + 984 (weaknesses: 944 CWE + 40 other) +
27 (compliance) + 3 (secrets) + 7 (pii) + 41 (supply-chain).

---

## Hard findings

### (a) PROSE-ONLY docs -- no manifest at all, ids minted by this pass

Three of the 11 source docs have **zero** `## DENOMINATOR MANIFEST`
section and assign **zero** stable ids to their own content, despite
containing genuinely enumerable, named entries:

- **`structural-linter-adversarial-hardening.md`** -- 5 named principles
  (rule 1-5) + 9 named arch-evasion rows + 9 named strata-evasion rows =
  **23 entries**, all prose-table only. Registry ids `SLH-RULE-*`,
  `SLH-ARCH-EVA-*`, `SLH-SYS-EVA-*` were minted by this pass to close the
  gap. Before this pass, none of these 23 items were reachable by any
  drift-lock check.
- **`capability-evasion-taxonomy.md`** -- 112 named language constructs
  (13+9 Python, 17+9 TS/JS, 13+6 Rust, 7+5 C, 12+5 C++, 11+5 Kotlin) in
  per-language tables, with only a prose "Combined coverage table" and a
  "Phase 2 coverage verdict" narrative -- no `id:` column, no manifest.
  Registry ids `EVA-<LANG>-<S|R><NN>` were minted by this pass.
- **`design-pattern-traps-corpus.md`** -- 21 named trap topics, only
  named in a "Phase-0/Phase-2 coverage ledger" narrative paragraph (its
  own frontier-loop bookkeeping), not a manifest with per-topic ids.
  Registry ids `PAT-TRAP-<NN>-<TOPIC>` were minted by this pass.

**Total prose-only entries closed by this pass: 23 + 112 + 21 = 156.**
These 156 existed as real content before this pass but had no canonical
id and were therefore invisible to any exhaustiveness drift-lock keyed on
manifest ids -- this is the single largest miss category found.

### (b) SPLIT entries -- same real-world item, unlinked ids across files

Grepped for named concepts appearing in >=2 source docs' own tables/prose
(non-exhaustive spot-check, not a full pairwise diff of 1950 entries --
flagged as a residual gap, see "What this pass did NOT do" below).
Confirmed present in multiple files, each currently under a
file-local, unlinked id in this registry (`cross_refs: []`):

| Concept | Appears in | Registry ids (unlinked) |
|---|---|---|
| Circuit Breaker | architecture-check-catalog.md sec 5.2, design-pattern-catalog.md | `ACC-5-2-CIRCUIT-BREAKER` (or equivalent), a `PAT-*` id in patterns.yaml |
| Bulkhead | architecture-check-catalog.md, design-pattern-catalog.md, system-design-corpus.md | ids in `arch-checks.yaml`, `patterns.yaml`, `system-design.yaml` (three-way split) |
| Idempotent Receiver | architecture-check-catalog.md, design-pattern-catalog.md, system-design-corpus.md | three-way split, same as above |
| Anti-Corruption Layer | design-pattern-catalog.md (DDD tactical, sec 3.3), architecture-check-catalog.md | two-way split |
| Value Object | design-pattern-catalog.md, architecture-check-catalog.md | two-way split |
| Repository (pattern) | design-pattern-catalog.md, architecture-check-catalog.md, design-pattern-traps-corpus.md (8.2, "Repository as leaky abstraction") | three-way split |
| Timeout | architecture-check-catalog.md, design-pattern-catalog.md, system-design-corpus.md, supply-chain-corpus.md | four-way split |
| Singleton | design-pattern-catalog.md, architecture-check-catalog.md, design-pattern-traps-corpus.md (5.1), system-design-corpus.md | four-way split |
| Anemic Domain Model | architecture-check-catalog.md (sec 4), design-pattern-traps-corpus.md (8.1) | two-way split |
| Saga | architecture-check-catalog.md, design-pattern-catalog.md, system-design-corpus.md | three-way split |

None of these were linked via `cross_refs` in this pass (`cross_refs: []`
on every affected entry) because collapsing them to one canonical id
requires a human/reviewer judgment call this pass did not manufacture:
e.g. is "Circuit Breaker" the arch-check's tier-1 presence-detector and
"Circuit Breaker" the pattern catalog's recommend-only entry the SAME
concept (one id, two facets) or two genuinely distinct checkable claims
that happen to share a name? Reported as an open finding, not silently
resolved either way. **At minimum 10 concepts, 24+ file-local id
occurrences, currently unlinked.**

### (c) Entries with no DISPOSITION yet

Every entry in `arch-checks.yaml`, `patterns.yaml`, `system-design.yaml`
(genuine portion), `evasion.yaml`, `compliance.yaml`, `secrets.yaml`,
`pii.yaml`, and `supply-chain.yaml` carries `disposition: pending` --
**1006 entries** (1950 grand total minus 944 CWE entries which inherit a
real disposition from `cwe-1000-registry.md`). None of the 9 source docs
for those files record a per-entry addressed/deferred/duplicate/
out-of-scope call themselves (their own manifests stop at
name+checkability+tier); this registry did not invent dispositions where
the source made none, per instruction not to silently "fix" by dropping
or fabricating. `cwe-1000-registry.md` is the one source doc in the
universe that already does full per-entry disposition (`checkable` /
`duplicate-of` / `out-of-scope`), so `weaknesses.yaml`'s 944 CWE entries
are the only fully-dispositioned slice of the registry.

**1006 of 1950 entries (51.6%) are undispositioned.**

### (d) system-design-corpus.md manifest-extraction artifacts

Of the 119 ids in `system-design-corpus.md`'s own manifest, **14 are not
real named entries**: they are mechanical-extraction artifacts where a
repeated table-header cell (`STRATA-CHECKABILITY`, appearing 8 times
across sections 1/5/10) or a repeated cell value (`best practice`,
appearing 4 times in section 13; `advisory`/`not-checkable` appearing
once each in section 1) got treated as if each occurrence were a distinct
named row. Full list: `SDC-1-STRATA-CHECKABILITY`,
`SDC-1-STRATA-CHECKABILITY-2` through `-5`, `SDC-1-ADVISORY`,
`SDC-1-NOT-CHECKABLE`, `SDC-5-STRATA-CHECKABILITY`,
`SDC-5-STRATA-CHECKABILITY-2`, `SDC-10-STRATA-CHECKABILITY`,
`SDC-13-BEST-PRACTICE` through `-4`. These inflate the source doc's own
stated TOTAL (119) by 14 -- the genuine content is **105 entries**, not
119. Kept in `system-design.yaml` with
`disposition: "out-of-scope(manifest-extraction-artifact)"` rather than
deleted, per instruction never to silently drop a discrepancy.

### (e) security-corpus.md CWE Top-25 vs. cwe-1000-registry.md tension

`security-corpus.md`'s own manifest lists 25 unique `cwe-top25-2025:*`
ids (its manifest text says "TOTAL 65" for the whole document, which
decomposes as 25 CWE + 10 OWASP + 16 CVE-fingerprint + 7 threat-framework
+ 7 canon = 65 -- confirmed by count). Cross-checking those 25 ids
against `cwe-1000-registry.md`'s 27 `checkable` CWE ids:

- **19 exact matches** (both docs agree the id is directly checkable) --
  linked via `cross_refs: ["security-corpus:cwe-top25-2025"]` on the
  corresponding `weaknesses.yaml` CWE entry.
- **6 ids present in security-corpus's Top-25 but NOT marked `checkable`
  in cwe-1000-registry.md**: `CWE-120`, `CWE-121`, `CWE-122` (all
  reclassified by cwe-1000-registry.md as `duplicate-of` a broader
  checkable parent -- CWE-787/CWE-119), and `CWE-200`, `CWE-284`,
  `CWE-770` (reclassified by cwe-1000-registry.md as
  `out-of-scope:authn-authz-boundary-predicate` /
  `out-of-scope:memory-model` respectively). This is a genuine
  cross-document tension, not a bug in either doc alone:
  security-corpus.md treats these 6 as directly checkable (its own
  `design-level-provable`/`advisory` tags), cwe-1000-registry.md's
  stricter rule-based classifier does not. **Flagged, not resolved** --
  resolving it requires a reviewer decision about which
  classification rule wins, out of scope for a consolidation pass.
- **8 ids `checkable` in cwe-1000-registry.md but absent from
  security-corpus's Top-25** (`CWE-119`, `CWE-190`, `CWE-269`, `CWE-276`,
  `CWE-287`, `CWE-362`, `CWE-798`, `CWE-922`) -- not a conflict, just
  different scope (cwe-1000-registry.md's checkable set is drawn from
  `frob`'s live `CWE_CATALOG`, a superset of the 2025 Top 25 list).

### (f) compliance/secrets/pii granularity gap -- RESOLVED (T-0675, frozen at unit granularity)

`compliance-corpus.md`'s own manifest is UNIT-granular: e.g.
`GDPR-ARTICLES: count 99` is one manifest line, not 99 individually
id'd articles; same for `ASVS-REQUIREMENTS: count 286`,
`CIS-SAFEGUARDS: count 153`, `ISO27002-CONTROLS: count 93`. The doc's own
stated `TOTAL_LEAF_CONTROLS_ENUMERATED: 599` is a SUM of these counts,
not a set of 599 individually addressable ids. `secrets-pii-corpus.md` is
the same shape (`secrets.provider_token_formats: total 30` is one line).
**This registry cannot manufacture 599 (compliance) + 56 (secrets) + 44
(pii) = 699 leaf-level canonical ids that do not exist in either source
doc** without inventing content neither doc actually enumerated
row-by-row -- reported as a structural gap in the SOURCE corpus, not
silently patched over. `compliance.yaml`, `secrets.yaml`, `pii.yaml` are
built at the doc's own actual granularity (27 + 3 + 7 = 37 entries) and
this gap is the reconciliation finding.

**Decision (T-0675): freeze at unit granularity -- option (b) of the
finding's own two choices.** Expanding to real leaf-level enumeration
(option (a)) was rejected on the merits, not skipped for convenience:
the overwhelming majority of the 599 compliance leaf counts are
denominators borrowed from external standards frob does not own or
redistribute the text of (e.g. `GDPR-ARTICLES: 99`, `ASVS-REQUIREMENTS:
286`, `CIS-SAFEGUARDS: 153`, `ISO27002-CONTROLS: 93` together already
account for 631 of the 599 compliance leaf count). Minting 631 individual
`GDPR-ART-{1..99}`-style ids from a bare count, with no per-article text
sourced or cited, would not be a real leaf-level enumeration -- it would
be 699 fabricated ids dressed as one, which is the exact failure mode
this reconciliation pass exists to catch, not commit. This freeze was
already made operationally by the three sibling reconciliation tickets
T-0675 was blocked on -- T-0386 (secrets.yaml, 3 entries), T-0387
(pii.yaml, 7 entries), T-0388 (compliance.yaml, 27 entries) -- each of
which built and closed its registry file at the source doc's own unit
granularity, with a passing file-specific EXHAUSTIVENESS meta-test wired
into `frob check`. T-0675 makes that already-landed practice an
explicit, written decision at the finding level instead of an implicit
one; see `docs/design/registry/README.md`'s "Granularity freeze (finding
(f))" note for the rationale as recorded alongside the registry file
list. `compliance.yaml` + `secrets.yaml` + `pii.yaml` stay at
27 + 3 + 7 = 37 entries; the 699 leaf-level ids are not built, and this
finding is closed as a documented decision, not left open.

### (g) supply-chain-corpus.md self-inconsistent TOTAL

`supply-chain-corpus.md`'s own `## DENOMINATOR MANIFEST` YAML block lists
**41 unique entries** under `denominator_manifest.entries` (16 attack +
9 defense + 16 detection, verified: no duplicate ids) but its own
`TOTAL:` field two lines below says **39**. The doc's own
`totals_by_class` block (attack:16, defense:9, detection:16, summing to
41) tries to explain this away as "class subtotals sum to more than
TOTAL by the number of dual-tagged entries" -- but that note describes
why class-subtotal SUMS exceed a raw-entry TOTAL, it does not explain why
the raw entries LIST itself (41 unique ids, not summed) exceeds the
doc's own declared TOTAL of 39. **This is a self-inconsistency in the
source doc, not a counting error in this pass** -- `supply-chain.yaml`
is built with all 41 real entries (never dropping 2 to force a match to
39) and both numbers are recorded (`total: 41`,
`total_per_source_doc_TOTAL_field: 39`) so the discrepancy is visible
rather than silently resolved in either direction.

---

## Mid-pass addition: `cwe-1000-registry.md`

This doc did not exist on `main` when this worktree branched. It landed
on `main` after Phase 1 of this pass had already built
`arch-checks.yaml`, `patterns.yaml`, and `system-design.yaml`. On
notification, `main` was merged into this worktree
(`git merge main --no-edit`), the new file was read in full (1218 lines),
its manifest (a fenced code block, 944 `CWE-<id>|<abstraction>|
<disposition>|parents:<...>|name:<...>` lines, `TOTAL: 944` confirmed by
exact line count) was parsed programmatically, and folded into
`weaknesses.yaml` as the PRIMARY source for that domain, with
`security-corpus.md`'s 25 CWE Top-25 ids linked in via `cross_refs`
rather than duplicated as separate ids (finding (e) above documents the
19-match / 6-tension / 8-scope-only breakdown from that linking). The
universe count in this report (11 docs, 1950 entries) already includes
this addition -- it is not a follow-up.

---

## What this pass did NOT do (residual gaps, honestly reported)

- **Full pairwise cross-reference linking.** Finding (b) is a spot-check
  over ~14 hand-picked concept names known to be architecture/pattern
  vocabulary that plausibly recurs; it is NOT an exhaustive pairwise diff
  of all 1950 entries against all others. A genuinely exhaustive
  cross-reference pass (entity-resolution over ~2000 names) is
  out of scope for this consolidation pass and is itself a
  follow-up-worthy task.
- **Disposition assignment.** 1006 of 1950 entries are `pending` (finding
  c) because the source docs did not carry a disposition and this pass
  chose not to invent one. Assigning real dispositions (addressed /
  reasoned-deferral / out-of-scope) to those 1006 requires the same kind
  of domain judgment `cwe-1000-registry.md`'s own rule-based classifier
  applied to CWE-1000 -- a comparable-effort follow-up task, not a
  by-product of consolidation.
- **Checkability-tag normalization.** Each source doc uses its own
  checkability vocabulary (`tier1-static` vs. `statically-detectable` vs.
  `design-level-provable` vs. `static` vs. `checkable`) and this pass
  preserved each verbatim rather than inventing a single normalized
  taxonomy across 9 different source vocabularies -- flagged as future
  work, not done here.

## REG008/REG009 (T-0428)

The disposition grammar's `handled_by:<rule-id>` (above) is a hand-typed
CLAIM about which rule enforces an entry -- exactly the "catalogued, not
enforced" drift this registry exists to close, moved up one level. T-0428
adds the code-side half: a rule/detector's own code declares what it
enforces via `frob:enforces <concept-id>` (a comment-DSL directive,
`frob.graph._models.EdgeKind.ENFORCES`), and `registry_gate`'s optional
`snapshot` argument cross-checks the two SSOTs bidirectionally:

- **REG008** (WARN, advisory) -- an entry dispositioned
  `handled_by:<rule-id>` with no `frob:enforces <entry-id>` edge anywhere
  in code: the yaml claims enforcement the code does not itself declare.
- **REG009** (WARN, advisory) -- a `frob:enforces <concept-id>` edge in
  code naming a concept id absent from every loaded registry file: a
  typo, or a rule enforcing something the universe corpus never
  enumerated.

Both WARN, not ERROR: this repo's ~1950 entries were built before
`frob:enforces` existed, so nearly every existing `handled_by` entry is
presently undeclared in code by this new measure -- an honest first-
turn-on debt (the same shape INV003/INV004 started in), not something
retroactively backfillable in one pass. `registry_gate`'s `snapshot`
parameter defaults to `None`, under which REG008/REG009 do not run at
all (no claim, rather than a false-positive flood for every caller that
has not wired a `GraphSnapshot` through yet).

## Registry file list

`docs/design/registry/README.md`, `docs/design/registry/arch-checks.yaml`,
`docs/design/registry/patterns.yaml`,
`docs/design/registry/system-design.yaml`,
`docs/design/registry/evasion.yaml`, `docs/design/registry/weaknesses.yaml`,
`docs/design/registry/compliance.yaml`, `docs/design/registry/secrets.yaml`,
`docs/design/registry/pii.yaml`, `docs/design/registry/supply-chain.yaml`,
`docs/design/registry/RECONCILIATION.md` (this file).
