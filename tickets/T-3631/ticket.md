---
id: T-3631
title: 'post-land sweep regression from T-3586: 4 new (rule, file) identit(ies), 9
  finding(s) (INV001, PII012)'
state: in-progress
kind: bug
origin: agent
created: '2026-09-01'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- invariants/INV-011.md
- invariants/INV-013.md
- invariants/INV-041.md
- tests/gates_suite/test_compliance.py
- src/frob/gates/_pii_structural/_keywords.py
findings:
- - INV001
  - invariants/INV-011.md
- - INV001
  - invariants/INV-013.md
- - INV001
  - invariants/INV-041.md
- - PII012
  - tests/gates_suite/test_compliance.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_pii_structural/_keywords.py
  reason: PII012 non-PII waiver allowlist for test_gates.py test names must be relocated
    1:1 to their new tests/gates_suite/test_compliance.py home
  actor: logan
  at: '2026-09-01'
evidence:
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov003_rejects_empty_directory_level_evidence
- tests/gates_suite/test_run.py::TestOptInGates::test_dup_gate_off_by_default
- tests/gates_suite/test_sys.py::TestSelfAuditGate::test_selfaudit001_clean_model_no_violations
- tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage::test_ts_interface_email_field_fires
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-3586 at commit 096c8916806e57e814272d07e70b8dd228a507ec found 4 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (4), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 9 actual finding(s) across those 4 identit(ies).

New (rule, file) identit(ies) filed here:

- INV001  invariants/INV-011.md
- INV001  invariants/INV-013.md
- INV001  invariants/INV-041.md
- PII012  tests/gates_suite/test_compliance.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- INV001  invariants/INV-011.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- INV001  invariants/INV-013.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- INV001  invariants/INV-041.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PII012  tests/gates_suite/test_compliance.py  -> attributed to T-3586 (commit 096c8916806e, already closed/dropped -- filed below) via tests/gates_suite/test_compliance.py::TestComplianceGate

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.