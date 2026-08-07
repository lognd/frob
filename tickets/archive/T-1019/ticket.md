---
id: T-1019
title: 'REG011 burn-down: 1157 out_of_scope disposition reasons fail the accountable-excuse
  form (weaknesses 798, patterns 346)'
state: done
kind: docs
origin: human
created: '2026-07-27'
priority: high
parent: T-0204
tier: ticket
sprint: null
scope:
- docs/design/registry/weaknesses.yaml
- docs/design/registry/patterns.yaml
- docs/design/registry/compliance.yaml
- docs/design/registry/supply-chain.yaml
- docs/design/registry/secrets.yaml
- src/frob/gates/_registry_exhaustiveness.py
- tests/test_registry_exhaustiveness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_registry_cross_corpus_totality.py::TestCrossCorpusLinkageIntegrity::test_every_cross_ref_resolves_to_a_real_id
- tests/unit/strata/test_registry_cross_corpus_totality.py::TestCrossCorpusLinkageIntegrity::test_every_cross_ref_is_mutually_navigable
- tests/unit/strata/test_registry_cross_corpus_totality.py::TestProseOnlyRetrofitIntegrity::test_retrofit_counts_and_source_doc_pointers_hold
- tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy::test_reason_naming_no_control_warns
designated_repro_test: null
acceptance:
- text: GIVEN a full frob check run THEN REG011 warnings are zero and no disposition
    was silently weakened (spot-check 10 rewrites read as substantive)
  evidence:
  - tests/unit/strata/test_registry_cross_corpus_totality.py::TestCrossCorpusLinkageIntegrity::test_every_cross_ref_resolves_to_a_real_id
  - tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy::test_reason_naming_no_control_warns
threat: null
component: null
---
REG011 demands each out_of_scope disposition name a catching control (rule-id/CWE token) or be a substantive 'none -- <explanation>' reasoned-none disclosure. 1157 entries fail. First make a design decision: entries whose own checkability tag is process/advisory are definitionally not statically checkable -- either the rule accepts that class with the tag as grounds, or every reason is rewritten to the compliant reasoned-none form. Prefer honest per-class rewrites over blanket rule loosening; if the rule changes, it must still reject genuinely unaccountable excuses (keep a before-fails test).