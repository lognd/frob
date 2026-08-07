---
id: T-0620
title: 'arch: DIP layering contract (declared allowed-module-dependency graph) + no-DI
  construction smell'
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
- src/frob/arch/_layering.py
- frob.toml
- docs/modules/arch.md
- tests/unit/test_arch.py
- src/frob/arch/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/arch/_models.py
  reason: 'T-0620''s declared scope omits src/frob/arch/_models.py, but the DIP

    checks it implements (dip-layering-violation, no-di-construction) need a

    new ArchCategory literal registered there, exactly like every prior

    sibling in this same ARCH1xx SOLID-catalog cluster (T-0617/T-0618/T-0619

    all listed _models.py in their own declared scope for the identical

    reason -- registering new ArchCategory values is a fixed, small,

    mechanical addition, not a design decision). Extending scope rather than

    routing around it, per SCOPE001''s own remediation.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/unit/test_arch.py::TestLayeringConfig::test_layer_for_longest_prefix_match
- tests/unit/test_arch.py::TestLayeringConfig::test_layer_for_unmatched_path_is_none
- tests/unit/test_arch.py::TestLoadLayeringConfig::test_missing_frob_toml_returns_none
- tests/unit/test_arch.py::TestLoadLayeringConfig::test_parses_declared_layers_and_allow_table
- tests/unit/test_arch.py::TestLayeringViolations::test_disallowed_cross_layer_edge_flagged
- tests/unit/test_arch.py::TestLayeringViolations::test_allowed_cross_layer_edge_not_flagged
- tests/unit/test_arch.py::TestLayeringViolations::test_dynamic_import_in_layered_file_flagged
- tests/unit/test_arch.py::TestNoDiConstructionSmell::test_inline_construction_outside_init_flagged
- tests/unit/test_arch.py::TestNoDiConstructionSmell::test_construction_inside_init_not_flagged
- tests/unit/test_arch.py::TestNoDiConstructionSmell::test_construction_inside_factory_function_not_flagged
designated_repro_test: null
threat: null
component: null
---
Layering contract: a frob.toml-declared allowed-module-dependency graph (import-linter style: layers + allowed edges); a violation is a high layer importing a low/concrete module across the declared boundary -- new ARCHxxx id, resolved against actual (not surface) imports per the adversarial-hardening note (transitive re-export resolution, fail-closed on dynamic import). concrete-collaborator construction smell: a method body directly constructs a concrete dependency instead of receiving it via constructor/param injection. Acceptance: a sample frob.toml layering config + fixture violating it fails; a compliant fixture passes; docs updated with the config schema.