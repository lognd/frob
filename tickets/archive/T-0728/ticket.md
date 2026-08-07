---
id: T-0728
title: 'arch: wire ARCH1xx SOLID checks into analyze_project, frob.toml thresholds,
  gate registry'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: high
blocked_by:
- T-0616
parent: T-0330
tier: ticket
sprint: null
scope:
- src/frob/arch/__init__.py
- src/frob/app/config.py
- src/frob/gates/**
- docs/modules/arch.md
- tests/unit/test_arch_srp.py
- tests/unit/test_config.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_config.py
  reason: 'Editing src/frob/app/config.py''s load_arch_config (in-scope, required
    by

    this ticket''s plan to thread the five ARCH1xx thresholds through frob.toml)

    adds five new keys to the dict it returns. tests/unit/test_config.py''s

    test_reads_override and test_missing_toml_defaults assert exact dict

    equality (cfg == {...five original keys...}), so they now fail on the

    extra keys through no behavior change of their own -- a direct, minimal,

    unavoidable consequence of the in-scope config.py edit, not a widening of

    this ticket''s own feature work. Adding the two new keys to those two

    assertions is the minimal fix.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/unit/test_arch_srp.py::TestAnalyzeProjectWiring::test_two_cluster_class_fires_arch101
- tests/unit/test_arch_srp.py::TestAnalyzeProjectWiring::test_cohesive_class_does_not_fire_arch101
- tests/unit/test_arch_srp.py::TestAnalyzeProjectWiring::test_god_module_fires_arch102
- tests/unit/test_arch_srp.py::TestAnalyzeProjectWiring::test_mixed_concern_function_fires_arch103
- tests/unit/test_arch_srp.py::TestArchGateSrpWiring::test_two_cluster_class_fires_arch101
- tests/unit/test_arch_srp.py::TestArchGateSrpWiring::test_cohesive_class_does_not_fire_arch101
- tests/unit/test_arch_srp.py::TestArchGateSrpWiring::test_god_module_fires_arch102
- tests/unit/test_arch_srp.py::TestArchGateSrpWiring::test_mixed_concern_function_fires_arch103
- tests/unit/test_arch_srp.py::TestArchGateSrpWiring::test_arch101_respects_explicit_frob_toml_override
- tests/unit/test_arch_srp.py::TestArchConfigThresholds::test_reads_srp_overrides
- tests/unit/test_arch_srp.py::TestArchConfigThresholds::test_srp_defaults_without_frob_toml
designated_repro_test: null
acceptance:
- text: GIVEN a fixture repo with a two-cluster class WHEN frob check runs THEN ARCH101
    appears in arch output with frob.toml-tunable thresholds AND the rule ids are
    waivable/registered
  evidence:
  - tests/unit/test_arch_srp.py::TestAnalyzeProjectWiring::test_two_cluster_class_fires_arch101
  - tests/unit/test_arch_srp.py::TestAnalyzeProjectWiring::test_cohesive_class_does_not_fire_arch101
  - tests/unit/test_arch_srp.py::TestAnalyzeProjectWiring::test_god_module_fires_arch102
  - tests/unit/test_arch_srp.py::TestAnalyzeProjectWiring::test_mixed_concern_function_fires_arch103
  - tests/unit/test_arch_srp.py::TestArchGateSrpWiring::test_two_cluster_class_fires_arch101
  - tests/unit/test_arch_srp.py::TestArchGateSrpWiring::test_cohesive_class_does_not_fire_arch101
  - tests/unit/test_arch_srp.py::TestArchGateSrpWiring::test_god_module_fires_arch102
  - tests/unit/test_arch_srp.py::TestArchGateSrpWiring::test_mixed_concern_function_fires_arch103
  - tests/unit/test_arch_srp.py::TestArchGateSrpWiring::test_arch101_respects_explicit_frob_toml_override
  - tests/unit/test_arch_srp.py::TestArchConfigThresholds::test_reads_srp_overrides
  - tests/unit/test_arch_srp.py::TestArchConfigThresholds::test_srp_defaults_without_frob_toml
threat: null
component: null
---
T-0616 (and successive T-0330 children) deliver check families over the normalized model with module-default thresholds, but nothing invokes them in production -- the invoked-by-nothing pattern, called out by T-0616's reviewer with the exact wiring list: (a) register run_srp_checks (and each subsequent family runner) in analyze_project's dispatch so they fire during real frob check; (b) thread the thresholds (LCOM4_MIN_METHODS, LCOM4_MIN_FIELD_USING_METHODS, GOD_MODULE_MIN_EXPORTS, GOD_MODULE_MIN_CLUSTERS, MIXED_CONCERN_MIN_DECISION_POINTS, plus later families') into frob.app.config's [arch] table; (c) add ARCH101-103 (and successors) to _KNOWN_GATE_RULES for waiver/registry visibility; (d) coordinate with T-0626's registry rows. Extend as each T-0617..T-0625 sibling lands -- this is the standing wiring home for the family.