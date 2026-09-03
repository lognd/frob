## Done report

Repointed the 4 (rule,file) identities from T-3586's post-land sweep: relocated INV-011/013/041 evidence anchors to their tests/gates_suite/ homes (test_run.py::TestOptInGates, test_coverage.py::TestCoverageGate, test_sys.py::TestSelfAuditGate), and relocated the 8 PII012 _PII012_REVIEWED_NON_PII allowlist entries (the 'token' homonym plus 7 named TestPiiStructuralCrossLanguage tests) from tests/test_gates.py to tests/gates_suite/test_compliance.py 1:1, same reasons. Verified via scoped frob check --ticket T-3631: gate:INV and gate:PII both 0 errors.

### Changed
```
 invariants/INV-011.md                       |  6 +++---
 invariants/INV-013.md                       |  6 +++---
 invariants/INV-041.md                       |  4 ++--
 src/frob/gates/_pii_structural/_keywords.py | 28 ++++++++++++++++++++--------
 tickets/T-3631/ticket.md                    | 15 ++++++++++++++-
 5 files changed, 42 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov003_rejects_empty_directory_level_evidence` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_run.py::TestOptInGates::test_dup_gate_off_by_default` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_sys.py::TestSelfAuditGate::test_selfaudit001_clean_model_no_violations` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage::test_ts_interface_email_field_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 13 error(s), 4170 warning(s), 901 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/app/_config_external.py, PRE001@tickets/T-3631, REL001@src/frob/__init__.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
