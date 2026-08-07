---
id: T-0658
title: 'strata systems-checks: N:M coverage meta-test vs system-design-corpus.md denominator
  (epic T-0331 close condition)'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0640
- T-0641
- T-0642
- T-0643
- T-0644
- T-0645
- T-0646
- T-0647
- T-0648
- T-0649
- T-0650
- T-0651
- T-0652
- T-0653
- T-0654
- T-0655
- T-0656
- T-0392
parent: T-0331
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- docs/design/registry/system-design.yaml
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_system_design_coverage.py::TestSystemDesignCorpusCoverage::test_every_corpus_entry_is_dispositioned_and_total_matches
- tests/unit/strata/test_system_design_coverage.py::TestSystemDesignGateLiveZero::test_no_system_design_violations
- tests/unit/strata/test_system_design_coverage.py::TestSystemDesignCorpusCoverage::test_at_least_one_systems_checks_family_rule_is_bound
designated_repro_test: null
acceptance:
- text: Given the full system-design-corpus.md denominator, when the meta-test runs,
    then every entry has a disposition (addressed-by-check | reasoned-deferral) and
    the coverage total matches TOTAL
  evidence:
  - tests/unit/strata/test_system_design_coverage.py::TestSystemDesignCorpusCoverage::test_every_corpus_entry_is_dispositioned_and_total_matches
- text: Given a future new system-design-corpus.md entry with no disposition, when
    the meta-test runs, then it fails the build
  evidence:
  - tests/unit/strata/test_system_design_coverage.py::TestSystemDesignGateLiveZero::test_no_system_design_violations
threat: null
component: null
---
Epic close condition. Bind every genuine system-design-corpus.md manifest entry (105 genuine, per RECONCILIATION.md finding (d), plus 14 manifest-extraction artifacts explicitly excluded) to >=1 registered SYS2xx/REL2xx check or a reasoned deferral, following the T-0343 drift-lock framework. (addressed union deferred) == TOTAL. Cannot close while any relevant entry is unaddressed and un-deferred. Depends on all 16 obligation children plus T-0392 (system-design registry-domain reconciliation) landing so 'registered check' is a real, checkable claim.