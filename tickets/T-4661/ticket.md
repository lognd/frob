---
id: T-4661
title: 'Gate registration interface: job list, known-rule set and check-coverage derived
  from one registry'
state: done
kind: feature
origin: human
created: '2026-09-19'
priority: critical
parent: T-4655
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_registry.py
- tests/unit/test_gate_registry.py
- docs/modules/gate-registration.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: v0.535.0
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
evidence:
- tests/unit/test_gate_registry.py::TestAddingADetectorTouchesOneFile::test_adding_a_detector_touches_one_file
- tests/unit/test_gate_registry.py::TestUnregisteredLiveRuleIsReported::test_unregistered_live_rule_is_reported
- tests/unit/test_gate_registry.py::TestDerivedViewsMatchLegacyExactly::test_derived_job_names_equal_all_gates
- tests/unit/test_gate_registry.py::TestDerivedViewsMatchLegacyExactly::test_derived_known_rule_ids_equal_known_gate_rules
- tests/unit/test_gate_registry.py::TestGateRegistrationDocDescribesTheFourDerivedViews::test_doc_describes_registration_interface_and_derived_views
designated_repro_test: null
acceptance:
- text: Given src/frob/gates/_registry.py, when the job list and the known-rule set
    are derived from it, then they equal the current hand-maintained job list and
    `_KNOWN_GATE_RULES` exactly -- no rule gained, none lost.
  evidence:
  - tests/unit/test_gate_registry.py::TestAddingADetectorTouchesOneFile::test_adding_a_detector_touches_one_file
  - tests/unit/test_gate_registry.py::TestDerivedViewsMatchLegacyExactly::test_derived_job_names_equal_all_gates
  - tests/unit/test_gate_registry.py::TestDerivedViewsMatchLegacyExactly::test_derived_known_rule_ids_equal_known_gate_rules
- text: 'POSITIVE CONTROL: tests/unit/test_gate_registry.py::test_adding_a_detector_touches_one_file
    registers a new fake detector through the registry alone and asserts its rule
    id appears in the derived job list, the derived known-rule set and the derived
    check-coverage view, with no edit to gates/__init__.py or _waive.py. It FAILS
    on dev today (the fake rule is reported as unregistered in _KNOWN_GATE_RULES)
    and passes after this leaf.'
  evidence:
  - tests/unit/test_gate_registry.py::TestUnregisteredLiveRuleIsReported::test_unregistered_live_rule_is_reported
  - tests/unit/test_gate_registry.py::TestAddingADetectorTouchesOneFile::test_adding_a_detector_touches_one_file
- text: Given the registry, when a rule id is live in a detector but absent from the
    registry, then `frob check` reports it rather than silently accepting it; tests/unit/test_gate_registry.py::test_unregistered_live_rule_is_reported
    proves it (the existing _rule_id_scan behaviour, now sourced from the registry).
  evidence:
  - tests/unit/test_gate_registry.py::TestUnregisteredLiveRuleIsReported::test_unregistered_live_rule_is_reported
- text: docs/modules/gate-registration.md describes the registration interface and
    the four derived views.
  evidence:
  - tests/unit/test_gate_registry.py::TestGateRegistrationDocDescribesTheFourDerivedViews::test_doc_describes_registration_interface_and_derived_views
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Kernel decoupling leaf (GATE story). ~3 points. This is the leaf T-4647 and T-3854 both exist downstream of.

Today adding one detector means hand-editing the job list in src/frob/gates/__init__.py (9658 lines), the `_KNOWN_GATE_RULES` frozenset literal in _waive.py, the rule table in docs/modules/gates.md, and docs/design/registry/check-coverage.yaml. All four are shared-registry lease hotspots, so two gate tickets can never run in parallel; and a finished detector can sit unwired for weeks (T-4647).

Build ONE registration interface in a new module src/frob/gates/_registry.py: a detector module declares itself (decorator or explicit register call) with its rule ids, severity, job name and the files it reads. The job list, the known-rule set, the gates.md enumeration and check-coverage.yaml become DERIVED views over that registry -- generated, or verified against it, never hand-maintained.

This leaf builds the registry and its derivation, and proves it by deriving the CURRENT job list and rule-id set from it byte-identically. Migrating each detector to register itself, and opening registration to consumer repos (T-3854), are follow-ups that become one-file changes.

Docs for the new surface go in a NEW file, docs/modules/gate-registration.md, deliberately NOT docs/modules/gates.md -- that file is leased by T-4647 and is itself one of the registry hotspots this leaf removes.