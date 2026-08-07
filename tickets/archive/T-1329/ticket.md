---
id: T-1329
title: 'design/frob.strata: model src/frob/refactor/** (SYS102/SYS103 unmodeled, pre-existing
  T-1197 gap)'
state: done
kind: bug
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- design/frob.strata
- tests/test_gates.py
- tests/test_vet.py
- src/frob/vet/_capability.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: 'T-1320 coverage-run fallout: COMPLIANCE007 real-repo test expected the
    16 vacuous rows T-1245..49 have since re-dispositioned; updating expectation to
    0-and-locked'
  actor: logan
  at: '2026-07-30'
- op: add
  glob: tests/test_vet.py
  reason: 'T-1320 coverage-run fallout: vet fingerprint real-repo test failure under
    diagnosis, same batch'
  actor: logan
  at: '2026-07-30'
- op: add
  glob: src/frob/vet/_capability.py
  reason: 'T-1320 fallout: FP-DESERIALIZE-YAML-001 needle false-positives on explicit-Loader
    yaml.load calls (T-1206''s remediated shape); per-fingerprint refinement hook
    added here'
  actor: logan
  at: '2026-07-30'
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean
- tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap
- tests/test_vet.py::TestFingerprintScan::test_yaml_load_with_explicit_loader_is_not_flagged
- tests/test_vet.py::TestFingerprintScan::test_one_bare_yaml_load_among_remediated_calls_still_flags
- tests/test_vet.py::TestFingerprintScan::test_scan_directory_fingerprints_excludes_the_catalog_itself
- tests/test_gates.py::TestComplianceGate::test_compliance007_real_repo_registry_surfaces_known_gap
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp
designated_repro_test: null
threat: null
component: null
---
Found while working T-1203 (may-mutation audit): tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant and ::TestCoverageTotality::test_repo_unrestricted_scan_is_clean fail on main (pre-existing, unrelated to T-1203's diff) because src/frob/refactor/** (landed by T-1197) has no code= binding in design/frob.strata: SYS102 unmodeled-code plus 4x SYS103 coverage-totality findings on _apply.py/_resolve.py/_scan.py/_verify.py (fs-read/fs-write observed, FOREIGN to every node). Needs a real node (or code= glob on an existing one) added for src/frob/refactor/**, with may declarations matching its real fs-read/fs-write effects, and interface= attrs for its public surface (SYS104 will fire too once bound).