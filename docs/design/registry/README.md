# Unified design-knowledge registry

Machine-readable, canonical-id registry that consolidates every
`## DENOMINATOR MANIFEST` (and, where a doc lacks one, every enumerable
table/list) across `docs/design/*.md` into one place, so an entry split
across two corpus files gets ONE canonical id with cross-refs instead of
two unlinked ids. This is the source of truth T-0343's exhaustiveness
drift-lock binds to.

Built by a consolidation pass over the 11 corpus docs that existed on
`main` at build time (10 originally listed in the task, plus
`docs/design/cwe-1000-registry.md`, which landed on `main` mid-pass and
was folded in -- see `RECONCILIATION.md` for the full audit trail).

## Files

| File | Domain | Source doc(s) | Entries |
|---|---|---|---|
| `arch-checks.yaml` | code-structure / systems-design checks + adversarial-hardening rules | `architecture-check-catalog.md`, `structural-linter-adversarial-hardening.md` | 311 |
| `patterns.yaml` | design patterns/principles + documented traps | `design-pattern-catalog.md`, `design-pattern-traps-corpus.md` | 346 |
| `system-design.yaml` | distributed-systems / strata checks | `system-design-corpus.md` | 119 (105 genuine + 14 flagged extraction artifacts) |
| `evasion.yaml` | capability-evasion construct taxonomy | `capability-evasion-taxonomy.md` | 112 |
| `weaknesses.yaml` | CWE weaknesses + other security-framework entries | `cwe-1000-registry.md` (primary, 944 CWEs), `security-corpus.md` (cross-ref, 40 non-CWE entries) | 984 |
| `compliance.yaml` | compliance-framework units | `compliance-corpus.md` | 27 units (599 leaf controls enumerated but not individually id'd -- frozen at unit granularity, see note below) |
| `secrets.yaml` | secret-detector/token-format sections | `secrets-pii-corpus.md` | 3 sections (56 leaf items, same freeze) |
| `pii.yaml` | PII-category sections | `secrets-pii-corpus.md` | 7 sections (44 leaf items, same freeze) |
| `supply-chain.yaml` | supply-chain attack/defense/detection | `supply-chain-corpus.md` | 41 (source doc's own TOTAL field says 39 -- self-inconsistent, see `RECONCILIATION.md`) |

**Grand total: 1950 registry entries** (311 + 346 + 119 + 112 + 984 + 27 +
3 + 7 + 41). See `RECONCILIATION.md` for how this reconciles against each
source doc's own stated totals, and for every prose-only miss, split
entry, and undispositioned entry found in the process.

### Granularity freeze (finding (f), T-0675)

`compliance.yaml` (27 entries), `secrets.yaml` (3 entries), and
`pii.yaml` (7 entries) are built at their source docs' own UNIT
granularity, not at the 599 + 56 + 44 = 699 leaf-control granularity
those docs' `TOTAL_LEAF_CONTROLS_ENUMERATED`-style manifest fields
imply. This is a deliberate, permanent decision, not an open gap: most
of the 699 leaf counts are denominators borrowed from external standards
(GDPR articles, ASVS requirements, CIS safeguards, ISO 27002 controls,
...) that this repo does not own or redistribute the text of, so minting
one canonical id per leaf count with no per-leaf text actually sourced
would fabricate 699 ids dressed as a real enumeration -- the opposite of
what this registry is for. See `RECONCILIATION.md` finding (f) for the
full accounting (which leaf counts are borrowed-denominator vs. actually
itemized in-doc) and why unit granularity is the correct, final answer
rather than a placeholder for a future leaf-level pass. Reopening this
would require the source corpus docs themselves to enumerate real
leaf-level ids with citations first (option (a) in finding (f)) -- not a
registry-side change.

## `check-coverage.yaml` (T-0424): frob's own reflexive check-coverage registry

`check-coverage.yaml` is a tenth registry file, added by T-0424 as proof
that T-0407's unified model makes "add a new registry" mean "add a
filename to `REGISTRY_FILES`", not build a second mechanism. It has two
entry families:

- `gate_rule_entries` -- one entry per id `frob.gates.known_gate_rule_ids()`
  reports LIVE at gate-run time, each self-referentially
  `handled_by:<that same rule id>` (the rule's own existence-and-firing is
  exactly what `known_gate_rule_ids()` verifies -- this is not circular,
  it is the reflexive base case: "is this concern enforced" for an
  already-enforced concern is "yes, by itself").
- `concern_family_entries` -- the `docs/audits/` (2026-07-20, 7-auditor
  pessimistic pass) concern families frob does NOT yet enforce: 5
  cross-cutting themes plus 8 per-subsystem verdicts, each
  `deferred:T-0397` (the real, open audit-remediation epic tracking them).
  As T-0397's children close a concern down to a real gate rule, that
  entry's disposition moves from `deferred:T-0397` to
  `handled_by:<new rule id>` -- the registry's own drift-lock (REG001-007)
  then requires the new rule id to actually exist and fire, closing the
  loop the ticket's charter names: frob checking that things EXIST but not
  that its own check-coverage is COMPLETE.

A future concern discovered by any audit, auditor, or user request gets a
new `concern_family_entries` row here, dispositioned honestly
(`handled_by`/`deferred`/`out_of_scope`) at the point it is discovered --
never silently dropped, per the exhaustiveness gate's own REG001 rule.

## Schema

Every entry is a YAML mapping with (at minimum):

- `id` -- STABLE, namespaced canonical id (e.g. `PAT-GOF-SINGLETON`,
  `CWE-89`, `CMPL-PCIDSS-REQUIREMENTS`, `SC-ATTACK-TYPOSQUATTING`).
  Namespacing convention: `<DOMAIN-PREFIX>-<...>` where the domain prefix
  matches the registry file (`ACC-`/`SLH-` for arch-checks, `PAT-` for
  patterns, `SDC-` for system-design, `EVA-` for evasion, `CWE-`/`SEC-`
  for weaknesses, `CMPL-` for compliance, `SC-` for supply-chain). Ids
  already assigned by a source doc's own manifest (arch-checks,
  patterns, system-design, weaknesses' CWE ids, supply-chain) are
  preserved verbatim rather than re-minted, so they stay stable against
  the source doc.
- `name` -- human-readable label.
- `source_doc` -- the `docs/design/*.md` file the entry traces to.
- `source_ref` / `parents` / `framework` / etc. -- domain-specific
  pointer back into the source doc's own section/table/manifest line.
- `checkability` -- the source doc's own checkability/tier tag, carried
  through verbatim (vocabulary differs per doc; not normalized across
  files in this pass -- a normalization pass is future work, not silently
  invented here).
- `disposition` -- one of `addressed`, `reasoned-deferral`,
  `duplicate-of:<id>`, `out-of-scope(<concept>)`, or `pending`. Only
  `weaknesses.yaml`'s CWE entries (which inherit disposition directly
  from `cwe-1000-registry.md`'s own already-reasoned per-id call) have a
  disposition other than `pending` in this pass -- see
  `RECONCILIATION.md`, finding (c).
- `cross_refs` -- list of pointers to the SAME real-world item's entry in
  another file/section, so a concept appearing in two docs (e.g. Circuit
  Breaker in both `architecture-check-catalog.md` and
  `design-pattern-catalog.md`, CWE-79 in both `cwe-1000-registry.md` and
  `security-corpus.md`'s CWE Top 25) is one id with links, not two ids.
  This pass populated `cross_refs` for the CWE<->security-corpus overlap
  (verified programmatically, id-exact) and left cross-domain pattern/
  arch-check overlaps as a named, unlinked finding in
  `RECONCILIATION.md` finding (b) -- linking those requires per-pair
  human judgment (are "Circuit Breaker" in the arch catalog and in the
  pattern catalog the SAME entry, or two distinct checkable facets of
  one concept?) that this pass did not manufacture rather than get wrong.

## Known structural gaps in this registry (see RECONCILIATION.md for detail)

1. `compliance.yaml`, `secrets.yaml`, `pii.yaml` are only as granular as
   their SOURCE docs' own manifests, which are unit/section-count
   granular, not leaf-item granular (e.g. "GDPR-ARTICLES: 99" is one
   registry entry, not 99). The source docs themselves do not assign
   individual ids to each GDPR article / ASVS requirement / CIS
   safeguard, so this registry cannot manufacture ids that do not exist
   in the source without inventing content -- flagged, not silently
   upgraded.
2. `evasion.yaml` ids (`EVA-<LANG>-<S|R><NN>`) were MINTED by this
   registry pass, not carried from the source doc, because
   `capability-evasion-taxonomy.md` has no manifest section and assigns
   no ids of its own to its 112 table rows.
3. `arch-checks.yaml`'s `SLH-*` ids (23 of them, from
   `structural-linter-adversarial-hardening.md`) were likewise minted by
   this pass for the same reason.
4. `patterns.yaml`'s `PAT-TRAP-*` ids (21, from
   `design-pattern-traps-corpus.md`) were likewise minted; that source
   doc names its 21 topics in a "Phase-0/Phase-2 coverage ledger" rather
   than a manifest, so the topic names were used directly.
5. `system-design.yaml` carries 14 ids from `system-design-corpus.md`'s
   own manifest that are mechanical-extraction artifacts (repeated
   table-header text like "STRATA-CHECKABILITY" or a repeated cell value
   like "best practice" extracted as if it were a named row) rather than
   real named checks. They are kept in the file (never silently dropped)
   with `disposition: "out-of-scope(manifest-extraction-artifact)"` and
   counted separately in `total_artifacts`.
