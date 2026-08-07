---
id: T-0616
title: 'arch: SRP/cohesion checks (ARCH1xx) -- LCOM4, god-module, mixed-concern function'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0609
parent: T-0330
tier: ticket
sprint: null
scope:
- src/frob/arch/_models.py
- docs/modules/arch.md
- tests/unit/test_arch.py
- src/frob/arch/_srp.py
- tests/unit/test_arch_srp.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/arch/_solid.py
  reason: 'coordination: T-0615/T-0617 concurrently touch test_arch.py, own new file
    _srp.py + test_arch_srp.py to avoid collision'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/arch/_srp.py
  reason: 'coordination: T-0615/T-0617 concurrently touch test_arch.py, own new file
    _srp.py + test_arch_srp.py to avoid collision'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/unit/test_arch_srp.py
  reason: 'coordination: T-0615/T-0617 concurrently touch test_arch.py, own new file
    _srp.py + test_arch_srp.py to avoid collision'
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/test_arch_srp.py::TestLcom4::test_disjoint_field_groups_trigger_lcom4
- tests/unit/test_arch_srp.py::TestLcom4::test_shared_fields_do_not_trigger_lcom4
- tests/unit/test_arch_srp.py::TestGodModule::test_unrelated_export_clusters_trigger_god_module
- tests/unit/test_arch_srp.py::TestGodModule::test_related_exports_do_not_trigger_god_module
- tests/unit/test_arch_srp.py::TestMixedConcernFunction::test_io_compute_and_formatting_together_trigger
- tests/unit/test_arch_srp.py::TestMixedConcernFunction::test_single_concern_does_not_trigger
- tests/unit/test_arch_srp.py::TestRunSrpChecks::test_combines_all_three_checks
- tests/unit/test_arch_srp.py::TestCrossLanguage::test_lcom4_fires_on_typescript_adapter_output
- tests/unit/test_arch_srp.py::TestCrossLanguage::test_lcom4_does_not_fire_on_cohesive_typescript_class
designated_repro_test: null
threat: null
component: null
---
New ARCH1xx family for SRP: (1) LCOM4 low-cohesion class -- methods partition into disjoint field-usage components via a connectivity graph over self-field reads/writes; (2) god-module -- unrelated exports clustered by naming/usage disjointness; (3) mixed-concern function -- one body containing I/O capability calls + pure compute + string-formatting. Each check ships its static proxy definition, severity, ARCHxxx id, and is waivable via the existing T-0289 reasoned-override mechanism. Runs on the normalized model (T-0609) so it works across languages already adapted. Acceptance: one fixture per check triggers it; one negative fixture per check does not; docs/modules/arch.md documents each id + proxy.