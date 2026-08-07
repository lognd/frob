## Done report

Modeled src/frob/refactor in design/frob.strata (new node refactor: fs.read+fs.write measured from the SYS103 findings, interface synced via frob sys sync-interface) -- the T-1197 land had left the whole package unbound (SYS102 + 4x SYS103), which the T-1320 coverage run surfaced as 4 red real-repo tests. Also under this ticket's widened scope, the rest of the coverage-run fallout batch: 11 SYS104 interface adds on the tickets_ledger store node (ledger-v2 chain + T-1251 re-export drift; sync-interface did not pick these up, hand-added); COMPLIANCE007 real-repo test updated 16->0-and-locked (T-1245..T-1249 re-dispositioned all 16 rows it expected open); vet FP-DESERIALIZE-YAML-001 gained a per-fingerprint refinement (_FINGERPRINT_REFINEMENTS) so an explicit-Loader yaml.load (the CVE's own remediation, T-1206's shape in tickets/_store.py) no longer false-positives, with 2 regression tests; export goldens (k8s netpol + seccomp) regenerated additions-only for the new node and self-model node count updated 20->21 with a comment. All six originally-red tests plus the new regression tests verified green in one combined run. Commits 2c16879f + the goldens commit.

### Changed
(no changed files detected)

### Evidence
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintScan::test_yaml_load_with_explicit_loader_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintScan::test_one_bare_yaml_load_among_remediated_calls_still_flags` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintScan::test_scan_directory_fingerprints_excludes_the_catalog_itself` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestComplianceGate::test_compliance007_real_repo_registry_surfaces_known_gap` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 10 error(s), 2007 warning(s), 686 waived
- error-findings: ARCH001@src/frob/gates/_debt_deprecated.py, ARCH001@src/frob/refactor/_scan.py, ARCH001@src/frob/tickets/_land_finalize.py, COV001@design/frob.strata, OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py, PERF003@src/frob/gates/_debt_deprecated.py, PRE001@tickets/T-1329, RENDER001@src/frob/refactor/_cli.py, TICK003@tickets.md
