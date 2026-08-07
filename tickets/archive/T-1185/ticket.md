---
id: T-1185
title: 'arch: fix-or-waive the last 3 gates/** OPAQUE001 sites and promote to ERROR
  tier'
state: done
kind: security
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_docblocks.py
- src/frob/gates/_opaque.py
- frob.toml
- tests/test_vet.py
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_vet.py
  reason: T-1185's OPAQUE001 WARN->ERROR promotion in _opaque.py directly breaks tests/test_vet.py::TestOpaqueIndirectionGate.test_opaque_gate_emits_warn_severity_violation's
    severity assertion; fixing it is a direct mechanical consequence of this ticket's
    own in-scope change
  actor: logan
  at: '2026-07-29'
- op: add
  glob: frob.lock
  reason: frob ack (DRIFT001 remedy) after opaque_gate's body changed (severity WARN->ERROR)
    writes new digests here; same class as frob.toml already in scope
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_emits_warn_severity_violation
- tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_no_findings_on_empty_tracked_set
- tests/test_vet.py::TestOpaqueIndirectionGate::test_waived_finding_is_suppressed_and_reason_recorded
designated_repro_test: null
threat: null
component: null
---
T-1038 fixed or waived 90 of the T-0665 first-turn-on 93-site OPAQUE001 set, but src/frob/gates/__init__.py:7536 (getattr) and src/frob/gates/_docblocks.py:396-397 (importlib.import_module/getattr) were out of T-1038's declared scope (owned by a concurrent sibling ticket that wave). Dispose those 3 the same way (real fix or reasoned frob:waive), then promote OPAQUE001 from Severity.WARN to Severity.ERROR in src/frob/gates/_opaque.py (opaque_gate's Violation construction) and add OPAQUE001 = "error" to frob.toml's [gates.severity] table, in the SAME land that zeroes the repo-wide unwaived count -- the T-0973/T-0976 promote-at-zero precedent T-1038's own Done report follows.