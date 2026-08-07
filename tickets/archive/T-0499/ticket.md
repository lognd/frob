---
id: T-0499
title: 'strata: wire real known_rule_ids into evaluate_exhaustiveness/evaluate_compliance
  production callsites'
state: done
kind: security
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/app/sys_runner.py
- src/frob/strata/_audit.py
- tests/test_gates.py
- tests/unit/strata/test_audit.py
- docs/modules/gates.md
- .frob-release.json
- CHANGELOG.md
- pyproject.toml
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: add evidence tests + doc anchor for known_gate_rule_ids public accessor
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/strata/test_audit.py
  reason: add evidence tests + doc anchor for known_gate_rule_ids public accessor
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/modules/gates.md
  reason: add evidence tests + doc anchor for known_gate_rule_ids public accessor
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: REL001 version bump for known_gate_rule_ids public API addition
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: REL001 version bump for known_gate_rule_ids public API addition
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: REL001 version bump for known_gate_rule_ids public API addition
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: REL001 version bump for known_gate_rule_ids public API addition
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_gates.py::TestKnownGateRuleIds::test_returns_known_rule_id
- tests/test_gates.py::TestKnownGateRuleIds::test_is_frozenset
- tests/unit/strata/test_audit.py::TestExhaustiveness::test_known_rule_ids_reaches_compliance_caught_by_check
designated_repro_test: null
threat: null
component: null
---
Found while working T-0382. THREAT006 (check_caught_by_integrity) and the new COMPLIANCE004 (check_regulation_caught_by_integrity) both take a known_rule_ids frozenset[str] param that must be the live gate-rule-id set (frob.gates._KNOWN_GATE_RULES) for rule-id-shaped caught_by references to ever resolve -- otherwise every rule-id-shaped reference is (correctly, fail-closed) treated as unresolved, and no positive case can ever pass in production. Today: (1) frob.gates has no known_gate_rule_ids() public accessor despite _audit.py's evaluate_exhaustiveness docstring already naming it as the expected source; (2) the only two callers of evaluate_exhaustiveness (src/frob/app/sys_runner.py:615, src/frob/strata/_native_test.py:136) never pass known_rule_ids, so it silently defaults to empty; (3) evaluate_compliance's new known_rule_ids param (T-0382) is similarly never threaded from sys_runner.py. No current caught_by entry references a rule-id-shaped token so this is currently dormant, not actively wrong -- but a future entry that legitimately names a real gate rule (e.g. SEC001) would be incorrectly refused. Add known_gate_rule_ids() to frob.gates (public, returns _KNOWN_GATE_RULES) and thread it through both production callsites for both families.