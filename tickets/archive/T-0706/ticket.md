---
id: T-0706
title: check-coverage registry + extending-guides drift from this session's landings
  (DEPR/DOC005 rules, comment-dsl guide)
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/check-coverage.yaml
- docs/guides/extending/**
- tests/test_check_coverage_registry.py
- tests/unit/test_extending_guides_complete.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules
- tests/test_check_coverage_registry.py::TestExhaustivenessGateOverRealCheckCoverage::test_no_check_coverage_violations
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_row_anchor_file_exists_and_mentions_guide
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_anchor_fragment_resolves_to_guide_h1
designated_repro_test: null
acceptance:
- text: GIVEN the 4 failing drift tests WHEN the suite runs THEN they pass with real
    registry entries and resolving anchors, tests unmodified
  evidence: []
threat: null
component: null
---
CI triage 2026-07-22: 4 failures that are drift-locks correctly firing on this session's own landings. (1) tests/test_check_coverage_registry.py x2: the live known_gate_rule_ids() gained DEPR001-004 (T-0576) and DOC005 (T-0435) but the check-coverage registry yaml has no entries for them -- add honest dispositions. (2) tests/unit/test_extending_guides_complete.py x2: T-0576 added docs/guides/extending/comment-dsl-directives.md; the guides completeness table/anchors do not resolve -- fix the table/anchor per the test's contract. Mechanical, well-scoped fixes; do NOT loosen the drift-lock tests.