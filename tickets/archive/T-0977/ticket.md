---
id: T-0977
title: Decide + burn down ARCH101/102/103 (SRP/cohesion advisories)
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/**
- docs/audits/gates-quality.md
- frob.toml
- tests/unit/test_arch_srp.py
- docs/modules/arch.md
- docs/modules/app.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_arch_srp.py
  reason: T-0977 test/doc surface for the ARCH101/102/103 fixes
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/arch.md
  reason: T-0977 test/doc surface for the ARCH101/102/103 fixes
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/app.md
  reason: T-0977 added an ARCH103 waiver note to App.__call__'s doc anchor
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/test_arch_srp.py::TestGodModule::test_data_only_classes_are_excluded_from_god_module
- tests/unit/test_arch_srp.py::TestGodModule::test_method_bearing_classes_still_count_toward_god_module
- tests/unit/test_arch_srp.py::TestGodModule::test_unrelated_export_clusters_trigger_god_module
- tests/unit/test_arch_srp.py::TestGodModule::test_related_exports_do_not_trigger_god_module
- tests/unit/test_arch_srp.py::TestLcom4::test_disjoint_field_groups_trigger_lcom4
- tests/unit/test_arch_srp.py::TestLcom4::test_shared_fields_do_not_trigger_lcom4
- tests/unit/test_arch_srp.py::TestMixedConcernFunction::test_io_compute_and_formatting_together_trigger
designated_repro_test: null
threat: null
component: null
---
T-0970 wrote the promote-or-advisory decision for ARCH101 (low-cohesion-
class/LCOM4), ARCH102 (god-module/export-cohesion), and ARCH103 (mixed-
concern-function) into docs/audits/gates-quality.md: all three stay
advisory-only (WARN, not promoted to ERROR via [gates.severity]) this
round, because the live count (2 + 23 + 24 = 49 unwaived, 0 waived) is
too large to promote without immediately redding main, mirroring the same
reasoning T-0399 already applied to ARCH001/PERF/PII/SEC110.

This ticket carries the actual burn-down + re-decision:
- ARCH101 (2 live findings, both in src/frob/mutate/__init__.py:
  `_Mutator` and `_PointCollector`): small enough to burn down in one
  pass -- fix or waive both, then flip ARCH101 to error given it would
  be at zero.
- ARCH102 (23 live findings, all module-level "N top-level exports split
  across M unrelated clusters"): investigate the clustering heuristic's
  false-positive rate first (per gates-quality.md finding 4's god-class
  lineage, per-file heuristics here are known gameable) before burning
  down blindly -- some of these may be legitimately-cohesive modules the
  naming/usage clustering misjudges.
- ARCH103 (24 live findings, "mixes I/O, string-formatting, and N
  decision points"): burn down like ARCH001 (extract cohesive helpers or
  waive with a real argument), then flip to error once at/near zero.

Re-measure with `frob check --only gates-native --json` at pickup --
these counts were measured post-T-0970-merge and may have moved.