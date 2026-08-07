---
id: T-0346
title: 'EPIC: unified design-knowledge registry -- single source of truth, per-entry
  disposition, no prose-only or split-across-files misses'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/**
- src/frob/strata/**
- src/frob/arch/**
- tickets.md
- tests/unit/strata/
- tests/test_registry_reconciliation_weaknesses.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/strata/
  reason: T-0346 strata work maps to tests/unit/strata/
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_registry_reconciliation_weaknesses.py
  reason: 'epic close-condition evidence: acceptance [1]/[2] (CWE-1000 full exhaustiveness)
    cited against T-0384''s weaknesses reconciliation test'
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/strata/test_registry_cross_corpus_totality.py::TestCrossCorpusLinkageIntegrity::test_every_cross_ref_resolves_to_a_real_id
- tests/unit/strata/test_registry_cross_corpus_totality.py::TestProseOnlyRetrofitIntegrity::test_retrofit_counts_and_source_doc_pointers_hold
- tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesExhaustiveness::test_declared_cwe_total_is_944
- tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesExhaustiveness::test_audit_reports_exhausted
- tests/unit/strata/test_registry_cross_corpus_totality.py::TestCrossCorpusLinkageIntegrity::test_every_cross_ref_is_mutually_navigable
designated_repro_test: null
acceptance:
- text: every item across ALL corpora (design patterns, arch checks, traps, system-design,
    capability-evasion, security/CWE, compliance, secrets, PII, supply-chain) has
    a stable canonical id in ONE machine-readable registry (docs/design/registry/*.yaml
    or equivalent); the prose corpus docs become human elaboration that REFERENCES
    registry ids, never the sole home of an entry -- a reconciliation test fails if
    any prose entry (a table row / named item in a corpus doc) has no registry id
    (a prose-only miss) or if two docs describe the same item under different unlinked
    ids (a split-across-files miss)
  evidence:
  - tests/unit/strata/test_registry_cross_corpus_totality.py::TestCrossCorpusLinkageIntegrity::test_every_cross_ref_resolves_to_a_real_id
  - tests/unit/strata/test_registry_cross_corpus_totality.py::TestCrossCorpusLinkageIntegrity::test_every_cross_ref_is_mutually_navigable
- text: 'TRUE exhaustiveness: enumerations that were bulk-skipped or census-only get
    COMPLETED to per-entry granularity with an individual disposition each -- CWE-1000
    full (~900+, each: has-design-precondition->checkable / no-kernel-concept->out-of-scope-naming-the-missing-concept
    / duplicate-of-cataloged-id), AWS pattern catalog, the detector rule sets counted
    only as census (gitleaks/trufflehog/GitHub-partner-patterns). ''seems like spam/redundant''
    is NOT a valid skip; redundant-with-X is a disposition (duplicate-of X), not an
    omission'
  evidence:
  - tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesExhaustiveness::test_declared_cwe_total_is_944
- text: 'every registry entry carries a DISPOSITION: addressed-by-check(s) <ids> |
    reasoned-deferral(advisory/not-checkable, reason) | duplicate-of <id> | out-of-scope(named-missing-concept).
    T-0343''s exhaustiveness drift-lock binds to this registry and fails if ANY entry
    lacks a disposition or an addressed entry''s check vanishes -- so an implementing
    ticket provably addresses EVERYTHING'
  evidence:
  - tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesExhaustiveness::test_audit_reports_exhausted
threat: null
component: null
---
User critique (2026-07-20): the corpora hedged where the mandate is to EXHAUST -- e.g. security-corpus skipped CWE-1000 as 'repo spam' when the intent is to enumerate ALL ~900, categorize each, and reason mitigation per entry; and information split across 10 docs/design/*.md files means an item can exist in one file's prose but be absent from the enforceable denominator ('miss split across two files'). This epic makes the corpus a REGISTRY, not a reading list: (1) a single canonical machine-readable registry aggregating every corpus manifest with stable ids + cross-refs (pattern<->trap<->evasion<->mitigation linked by id); (2) a reconciliation/consolidation pass that de-dups cross-file and flags any prose-only entry; (3) completion of the bulk-skipped enumerations to per-entry disposition; (4) T-0343 (exhaustiveness drift-lock) bound to the registry with a mandatory per-entry disposition. Governs T-0330/331/332/339/341/343 and all the corpus docs. The corpora already emit '## DENOMINATOR MANIFEST' sections (per-doc TOTAL); this epic unifies them into one registry and closes the 'seems like spam so I skipped it' and 'split across two files' gaps permanently.