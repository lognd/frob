---
id: T-0963
title: check-coverage.yaml gate_rule_entries count drifted from known_gate_rule_ids()
  (119 vs 204+)
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/check-coverage.yaml
- tests/test_check_coverage_registry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_check_coverage_registry.py
  reason: 'route-2 evidence-covers-scope binding: test file already carries frob:tests
    directives to check-coverage.yaml (route 1), but adding the test file itself to
    scope satisfies close''s covers_scope check directly, matching this repo''s own
    common convention (scope: [src, tests]) noted in frob.gates.evidence_covers_scope''s
    docstring'
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules
- tests/test_check_coverage_registry.py::TestExhaustivenessGateOverRealCheckCoverage::test_no_check_coverage_violations
designated_repro_test: null
threat: null
component: null
---
Found while working T-0961 (gates/__init__.py _KNOWN_GATE_RULES REL2xx/REL38x + SYS204 listing-omission fix).

tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules
asserts docs/design/registry/check-coverage.yaml's gate_rule_entries count equals len(known_gate_rule_ids()).
This was ALREADY failing before T-0961 touched anything (119 registry entries vs 174 known rule ids at
T-0961's starting tip, before T-0961 added its own 29 ids on top, now 204) -- confirmed by reverting
T-0961's own diff and re-running the test in isolation; it fails identically either way. Pre-existing gap,
same registry-catalogued-vs-enforced-code-drifted-apart class as T-0343/T-0903/T-0923/T-0924's own
precedent. Also tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves fails
independently of T-0961's change (same failure with or without it) -- likely a separate, unrelated
pre-existing regression, not investigated further here since it is out of T-0961's scope
(src/frob/gates/__init__.py only).

Fix: add the missing gate_rule_entries rows to docs/design/registry/check-coverage.yaml for every rule id
in known_gate_rule_ids() that check-coverage.yaml does not yet cite (mirrors T-0961's own_KNOWN_GATE_RULES
gap-fill, just in the registry file instead of the frozenset), and separately triage
test_frob_self_model.py::test_every_claim_proves's failure.