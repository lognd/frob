---
id: T-0382
title: 'strata: verify caught_by controls actually exist and fire'
state: done
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0381
parent: T-0376
tier: ticket
sprint: null
scope:
- src/frob/strata/_threat.py
- src/frob/strata/_compliance.py
- tests/unit/strata/test_threat.py
- tests/unit/strata/test_compliance.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/test_strata*.py
  reason: declared glob tests/test_strata*.py matches zero files (same hazard as T-0381);
    narrowed to the two files this ticket actually touches
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/strata/test_threat.py
  reason: declared glob tests/test_strata*.py matches zero files (same hazard as T-0381);
    narrowed to the two files this ticket actually touches
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/strata/test_compliance.py
  reason: declared glob tests/test_strata*.py matches zero files (same hazard as T-0381);
    narrowed to the two files this ticket actually touches
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/strata/test_threat.py::TestCaughtByUnresolvedTokens::test_unknown_rule_id_is_unresolved
- tests/unit/strata/test_threat.py::TestCaughtByUnresolvedTokens::test_known_rule_id_resolves
- tests/unit/strata/test_threat.py::TestCaughtByUnresolvedTokens::test_no_referenced_tokens_is_unresolved_empty
- tests/unit/strata/test_compliance.py::TestRegulationCaughtByIntegrity::test_honest_none_caught_by_never_fails
- tests/unit/strata/test_compliance.py::TestRegulationCaughtByIntegrity::test_caught_by_naming_absent_control_is_refused
- tests/unit/strata/test_compliance.py::TestRegulationCaughtByIntegrity::test_caught_by_naming_present_control_discharges
- tests/unit/strata/test_compliance.py::TestRegulationCaughtByIntegrity::test_free_text_with_no_rule_id_token_is_not_checked_further
- tests/unit/strata/test_compliance.py::TestEvaluateCompliance::test_caught_by_integrity_folds_into_the_conjunction
- tests/unit/strata/test_compliance.py::TestEvaluateCompliance::test_caught_by_integrity_passes_when_control_is_real
designated_repro_test: null
threat: null
component: null
---
Add a verification check that a caught_by reference (added in the prior child) names a real registered control -- a rule id / gate / catalog entry that actually exists in the repo -- and fail closed (build-breaking) if an out-of-scope/benign-capability entry names a non-existent control. Ideally also confirm the named control fires (has test/enforcement evidence), not just that it is registered. Acceptance: a caught_by referencing a fabricated rule id fails frob check; a caught_by referencing a real enforced rule passes.