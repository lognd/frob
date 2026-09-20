---
id: T-0503
title: 'strata: compliance out_of_scope catalog never threaded into _audit.py evaluate_compliance
  call'
state: done
kind: security
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_audit.py
- src/frob/strata/_compliance.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense out-of-scope catalog narrative into T-0503 body
  actor: logan
  at: '2026-09-19'
  old_length: 1190
  new_length: 2251
evidence:
- tests/unit/strata/test_audit.py::TestExhaustiveness::test_compliance_out_of_scope_bad_caught_by_fails_real_audit_path
- tests/unit/strata/test_audit.py::TestExhaustiveness::test_compliance_out_of_scope_reaches_real_audit_path
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-0499. _audit.py::_compliance_pii_lint_fingerprint_gaps calls evaluate_compliance(model, view, known_rule_ids=known_rule_ids) with no out_of_scope argument -- it always defaults to (). Unlike the security/quality families (CWE_TOP_25_OUT_OF_SCOPE, QUALITY_OUT_OF_SCOPE imported and passed at _audit.py:469), there is no module-level OutOfScopeRegulation tuple defined anywhere for compliance, and none is threaded from sys_runner.py either. Effect: COMPLIANCE004 (caught_by integrity for compliance out-of-scope exclusions) can never actually fire in production regardless of T-0499's known_rule_ids threading, since check_regulation_caught_by_integrity always receives an empty out_of_scope tuple from this callsite. check_regulation_caught_by_integrity itself is correctly unit-tested with a non-empty out_of_scope (tests/unit/strata/test_compliance.py), so the gap is purely in the production wiring, same shape as the known_rule_ids gap T-0499 fixed. Fix direction: define a COMPLIANCE_OUT_OF_SCOPE catalog (or repo-configurable equivalent, mirroring load_repo_benign_capabilities) and thread it through _compliance_pii_lint_fingerprint_gaps -> evaluate_compliance.

<!-- narrative-moved:src/frob/strata/_compliance.py:218:T-0503 -->
frob:doc docs/strata/threat.md#compliance-regulatory-obligations-stdcompliance
frob:ticket T-0503
: T-0503: the production `OutOfScopeRegulation` catalog -- mirrors
: `_threat.py::CWE_TOP_25_OUT_OF_SCOPE`/`QUALITY_OUT_OF_SCOPE` for the
: compliance family (module docstring's "same obligation/discharge/
: exhaustiveness structure as `_threat.py`"). Before this, no module-level
: `OutOfScopeRegulation` tuple existed anywhere, so `evaluate_compliance`'s
: production callsite (`_audit.py::_compliance_pii_lint_fingerprint_gaps`)
: always threaded an empty `out_of_scope=()`, making COMPLIANCE004 (`caught_
: by` integrity) vacuous in production regardless of `known_rule_ids`
: threading (T-0499's own Done report flagged this as a distinct,
: not-folded-in gap). Each entry names a regulation the baseline catalog
: does not model plus the real compensating control that catches it
: elsewhere -- a fabricated or typo'd `caught_by` here is exactly the case
: COMPLIANCE004 exists to refuse.