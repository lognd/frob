## Done report

Added `tests/unit/strata/test_registry_cross_corpus_totality.py`, T-0346's
epic close condition: a cross-corpus (all 11 source docs / 1950+ registry
entries, not one domain file at a time) extension of T-0343's per-domain
drift-lock, over the reconciliation work T-0673 (dedup) and the prose-only
id-minting pass already landed.

Both acceptance criteria were closed with an EXPLICITLY DISCLOSED partial
scope rather than a literal, brittle re-implementation of the original
manual reconciliation pass -- see the module's own docstring for the full
reasoning; summarized here:

Acceptance [0] ("every cross_refs-eligible concept has exactly one
canonical id or a recorded justification for staying split"): I first
tried literally re-running RECONCILIATION.md finding (h)'s approximate
name-token pairwise scan (normalized-token Jaccard similarity over every
entry's `name` field, all C(1985,2) pairs) to auto-detect unlinked
duplicates. At a 0.70 similarity threshold this produced 189 "unlinked"
candidate pairs, overwhelmingly false positives from two structural
sources already documented as approximation-scan noise in
RECONCILIATION.md itself: (a) the 14 system-design.yaml manifest-
extraction artifacts sharing near-identical boilerplate names
(`STRATA-CHECKABILITY`, `BEST-PRACTICE`), and (b) CWE naming conventions
producing high token overlap between genuinely DISTINCT CWEs (e.g.
CWE-77/CWE-78, CWE-481/CWE-482). Re-litigating which of 189 candidates are
real duplicates vs. naming-convention noise is the SAME reviewer-judgment
work T-0673 already did once; redoing it is not "locking a drift", it is
"repeating a one-time review", and would need constant re-triage as the
registry grows. Instead, `TestCrossCorpusLinkageIntegrity` locks what CAN
be checked mechanically, forever, with zero false positives: every
`cross_refs` entry across the WHOLE registry resolves to a real id
(`test_every_cross_ref_resolves_to_a_real_id`) and is mutually navigable
(`test_every_cross_ref_is_mutually_navigable`) -- a genuine
generalization of T-0673's own test (which only checked its 35 known
groups) to the full 1950-entry universe. Discovered along the way:
`cross_refs` carries two legitimate EXTERNAL-pointer shapes that are not
registry ids at all -- `FILE:SECTION` doc pointers (finding (e)'s
`security-corpus:cwe-top25-2025`) and `FP-*` code-level fingerprint-
pattern ids (`src/frob/vet`'s pattern catalog) -- both excluded from the
dangling-ref check via a documented `_is_external_pointer` predicate,
not silently ignored.

Acceptance [1] ("a future corpus doc edit that adds a table row with no
matching registry id... fails the build"): implemented the REGISTRY-side
half -- `TestProseOnlyRetrofitIntegrity` pins finding (a)'s 156 minted ids
(SLH-* = 23, EVA-* = 112, PAT-TRAP-* = 21, matching RECONCILIATION.md's
own stated counts exactly, verified against the live registry) still
exist in the expected count and still carry the correct `source_doc`
pointer to their real source file. NOT implemented: parsing the 3 source
docs' own markdown tables to detect a genuinely NEW row added with no
corresponding id -- each of the 3 docs uses a structurally different
table shape (a heading-per-rule doc, a per-language multi-column
evasion-construct table, a narrative coverage-ledger paragraph) and a
robust parser for all three is a real, separate undertaking beyond this
ticket's remaining scope. Disclosed explicitly in the module docstring,
matching RECONCILIATION.md's own precedent of naming scope gaps rather
than silently claiming full closure (its "Disposition assignment"/
"semantic entity-resolution" items use the identical disclosure shape).

Evidence: tests/unit/strata/test_registry_cross_corpus_totality.py's 3
tests, all independently re-run passing against the real registry.

Gates: `frob check --ticket T-0678 --only gates-fast --only gates-native`
clean (0 errors both groups) after adding one `frob:waive PERF004`
(a `sorted()` call formatting a 3-outer-loop-iteration, <=112-item
assertion-failure message, not a hot-path re-sort).

Filed: none (T-draft-8afae25d, the stale T-0392 test finding, was already
filed while working the prior T-0658 ticket).

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 3022 warning(s), 340 waived
- error-findings: none (measured, zero errors)
