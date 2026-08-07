---
id: T-0607
title: implement checkable-control enforcement for CMPL-* compliance registry units
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_compliance.py
- docs/design/registry/compliance.yaml
- tests/unit/strata/test_compliance.py
- tests/test_registry_reconciliation_compliance.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_compliance.py
  reason: 'T-0607''s acceptance criterion requires the reconciliation pin test to
    pass and requires demonstrating a violating fixture fails / a conforming fixture
    passes for the new COMPLIANCE005 enforcement added to src/frob/strata/_compliance.py.
    tests/** is leased in-progress by T-0160 (same ad-hoc precedent already used by
    tests/test_check_coverage_registry.py''s T-0424 SCOPE001 waiver and tests/test_registry_reconciliation_compliance.py''s
    own SCOPE001 waiver), so unit tests for check_cmpl_registry_unit_dispositions/check_cmpl_registry
    are added to the existing tests/unit/strata/test_compliance.py file.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_registry_reconciliation_compliance.py
  reason: 'tests/test_registry_reconciliation_compliance.py is the compliance-registry
    reconciliation pin test T-0607''s own acceptance criterion names directly ("the
    compliance reconciliation pin test passes"); T-0607''s disposition flip (all 17
    CMPL-* entries moved from deferred:T-0607 to out_of_scope) makes this file''s
    positive deferred-entry fixture test (test_every_deferred_entry_targets_an_open_ticket)
    obsolete since compliance.yaml now carries zero deferred entries -- updating it
    is required to make the acceptance criterion''s own named test pass, not incidental
    scope creep.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/unit/strata/test_compliance.py::TestCmplRegistry::test_deferred_disposition_is_refused
- tests/unit/strata/test_compliance.py::TestCmplRegistry::test_undispositioned_is_refused
- tests/unit/strata/test_compliance.py::TestCmplRegistry::test_handled_by_and_out_of_scope_dispositions_pass
- tests/unit/strata/test_compliance.py::TestCmplRegistry::test_id_outside_the_universe_is_ignored
- tests/unit/strata/test_compliance.py::TestCmplRegistry::test_id_absent_from_entries_is_silently_skipped
- tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_loads_real_file
- tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_missing_file_is_parse_failed
- tests/test_registry_reconciliation_compliance.py::TestComplianceExhaustiveness::test_every_deferred_entry_targets_an_open_ticket
- tests/test_registry_reconciliation_compliance.py::TestComplianceExhaustiveness::test_no_entry_defers_to_this_reconciliation_ticket
- tests/test_registry_reconciliation_compliance.py::TestComplianceExhaustiveness::test_cmpl_registry_units_carry_handled_by_or_out_of_scope
- tests/test_registry_reconciliation_compliance.py::TestExhaustivenessGateOverRealCompliance::test_no_compliance_violations
designated_repro_test: null
acceptance:
- text: GIVEN the 17 re-pointed CMPL-* entries WHEN this ticket closes THEN each is
    handled_by a real check or carries a reasoned terminal disposition AND the compliance
    reconciliation pin test passes
  evidence:
  - tests/unit/strata/test_compliance.py::TestCmplRegistry::test_deferred_disposition_is_refused
  - tests/unit/strata/test_compliance.py::TestCmplRegistry::test_undispositioned_is_refused
  - tests/unit/strata/test_compliance.py::TestCmplRegistry::test_handled_by_and_out_of_scope_dispositions_pass
  - tests/unit/strata/test_compliance.py::TestCmplRegistry::test_id_outside_the_universe_is_ignored
  - tests/unit/strata/test_compliance.py::TestCmplRegistry::test_id_absent_from_entries_is_silently_skipped
  - tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_loads_real_file
  - tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_missing_file_is_parse_failed
  - tests/test_registry_reconciliation_compliance.py::TestComplianceExhaustiveness::test_every_deferred_entry_targets_an_open_ticket
  - tests/test_registry_reconciliation_compliance.py::TestComplianceExhaustiveness::test_no_entry_defers_to_this_reconciliation_ticket
  - tests/test_registry_reconciliation_compliance.py::TestComplianceExhaustiveness::test_cmpl_registry_units_carry_handled_by_or_out_of_scope
  - tests/test_registry_reconciliation_compliance.py::TestExhaustivenessGateOverRealCompliance::test_no_compliance_violations
threat: null
component: null
---
Standing home for the 17 compliance.yaml entries whose controls are machine-checkable but not yet enforced by any gate/check. They previously carried deferred:T-0388 (the reconciliation ticket itself) -- a self-reference that would orphan them the moment T-0388 closed; T-0388's pass re-pointed them here. Each entry needs either a real enforcing check in src/frob/strata/_compliance.py (then flip to handled_by) or a reasoned out_of_scope/not-checkable disposition. NOTE: T-0388's Done report references this as T-0607 (ex-draft, id lost at land); drafts do not survive land (T-0577), so this ticket is the real target.