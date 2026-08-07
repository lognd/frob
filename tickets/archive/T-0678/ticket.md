---
id: T-0678
title: 'registry: cross-corpus totality meta-test - zero unlinked duplicate concepts,
  zero prose-only entries (T-0346 close condition)'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0673
- T-0384
- T-0389
- T-0390
- T-0391
- T-0392
parent: T-0346
tier: ticket
sprint: null
scope:
- docs/design/registry/**
- src/frob/strata/**
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_registry_cross_corpus_totality.py::TestCrossCorpusLinkageIntegrity::test_every_cross_ref_resolves_to_a_real_id
- tests/unit/strata/test_registry_cross_corpus_totality.py::TestProseOnlyRetrofitIntegrity::test_retrofit_counts_and_source_doc_pointers_hold
- tests/unit/strata/test_registry_cross_corpus_totality.py::TestCrossCorpusLinkageIntegrity::test_every_cross_ref_is_mutually_navigable
designated_repro_test: null
acceptance:
- text: Given the full registry, when the meta-test runs, then every cross_refs-eligible
    concept has exactly one canonical id or a recorded justification for staying split
  evidence:
  - tests/unit/strata/test_registry_cross_corpus_totality.py::TestCrossCorpusLinkageIntegrity::test_every_cross_ref_resolves_to_a_real_id
- text: Given a future corpus doc edit that adds a table row with no matching registry
    id, when the meta-test runs, then it fails the build
  evidence:
  - tests/unit/strata/test_registry_cross_corpus_totality.py::TestProseOnlyRetrofitIntegrity::test_retrofit_counts_and_source_doc_pointers_hold
threat: null
component: null
---
Epic close condition. Extends T-0343's per-domain drift-lock with a cross-corpus check over all 11 source docs / 1950+ registry entries: (1) no named concept may exist under >=2 unlinked file-local ids (uses cross_refs, closes finding (b) permanently going forward); (2) no corpus table row may exist with no registry id (closes finding (a) permanently -- the 3 prose-only docs already retrofitted must never regress). Depends on the dedup pass and all five domain-reconciliation tickets (weaknesses/supply-chain/evasion/arch-checks/system-design) landing so the meta-test has a fully-dispositioned base to run against.