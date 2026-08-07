---
id: T-1111
title: 'warnings: small-residue sweep to zero (DEPR 4, LANG 3, INV 2, REG 2, WAIVE
  2, WALK 2)'
state: done
kind: bug
origin: agent
created: '2026-07-28'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- docs/**
- frob.toml
- tests/system/test_cli_sys_audit.py
- docs/design/registry/check-coverage.yaml
- src/frob/gates/_vet.py
- src/frob/gates/_arch.py
- invariants/**
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: narrow to real DEPR/LANG/INV/REG/WAIVE/WALK finding sites (T-1111 re-measure,
    TICK009)
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/system/test_cli_sys_audit.py
  reason: real DEPR005 caller site + REG registry entries + REG009 offending frob:enforces
    edge
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: real DEPR005 caller site + REG registry entries + REG009 offending frob:enforces
    edge
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/gates/_vet.py
  reason: real DEPR005 caller site + REG registry entries + REG009 offending frob:enforces
    edge
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/gates/_arch.py
  reason: real DEPR005 caller site + REG registry entries + REG009 offending frob:enforces
    edge
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/system/test_cli_sys_audit.py
  reason: real DEPR005 caller site + REG registry entries + REG009 offending frob:enforces
    edge
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: real DEPR005 caller site + REG registry entries + REG009 offending frob:enforces
    edge
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/gates/_vet.py
  reason: real DEPR005 caller site + REG registry entries + REG009 offending frob:enforces
    edge
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/gates/_arch.py
  reason: real DEPR005 caller site + REG registry entries + REG009 offending frob:enforces
    edge
  actor: logan
  at: '2026-07-28'
- op: add
  glob: invariants/**
  reason: INV003/004 fix needs a real invariants/INV-###.md file for the SYS103 coverage-totality
    claim
  actor: logan
  at: '2026-07-28'
- op: add
  glob: frob.lock
  reason: frob ack writes to frob.lock when acking INV-048's new code anchor
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_vet.py::TestSupplyChainUnpinnedDependencies::test_pyproject_caret_range_flagged
- tests/test_vet.py::TestSupplyChainInstallArtifacts::test_setup_py_absolute_data_files_flagged
- tests/test_vet.py::TestSupplyChainCiActionPin::test_workflow_branch_ref_flagged
- tests/test_vet.py::TestSupplyChainOpaqueBinaryArtifact::test_tracked_so_without_recipe_flagged
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103
- tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
designated_repro_test: null
acceptance:
- text: GIVEN a full frob check WHEN all gates run THEN the DEPR, LANG, INV, REG,
    WAIVE, and WALK families each report zero unwaived warnings
  evidence:
  - tests/test_vet.py::TestSupplyChainUnpinnedDependencies::test_pyproject_caret_range_flagged
  - tests/test_vet.py::TestSupplyChainInstallArtifacts::test_setup_py_absolute_data_files_flagged
  - tests/test_vet.py::TestSupplyChainCiActionPin::test_workflow_branch_ref_flagged
  - tests/test_vet.py::TestSupplyChainOpaqueBinaryArtifact::test_tracked_so_without_recipe_flagged
  - tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103
  - tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
threat: null
component: null
---
Endgame tail: the sub-five-warning families (DEPR003 x4, LANG003 x3, INV003/004 x2, REG009/REG010 x2, WAIVE004 x2, WALK001 x2 per gate summary). Fix or grounded-waive each. REG009/REG010 residue is the CPPTHROW001 check-coverage auto-sync gap noted at T-1042 land -- fold the registry entry fix here. Narrow scope at start.