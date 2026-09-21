---
id: T-4073
title: 'H-1: node declares no-PII, client_storage write requires waiver'
state: done
kind: security
origin: agent
created: '2026-09-06'
priority: high
parent: T-4071
tier: ticket
sprint: v1.1.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_pii_structural/__init__.py
- tests/test_pii_structural_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_pii_structural_gate.py
  reason: 'PII013 (H-1) needs test evidence; adding the gate''s own test file to scope,
    per the ticket''s own ''positive control, failing test first, evidence'' instruction.

    '
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.538.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.538.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
evidence:
- tests/test_pii_structural_gate.py::TestClientStorageNoPii::test_fires_on_namespaced_session_storage_write
- tests/test_pii_structural_gate.py::TestClientStorageNoPii::test_stays_quiet_without_no_pii_declaration
- tests/test_pii_structural_gate.py::TestClientStorageNoPii::test_stays_quiet_on_unrelated_setitem_call
- tests/test_pii_structural_gate.py::TestClientStorageNoPii::test_no_scan_without_any_no_pii_node
- tests/test_pii_structural_gate.py::TestClientStorageNoPii::test_waived_call_site_is_accepted
- tests/test_pii_structural_gate.py::TestClientStorageNoPii::test_fires_on_local_storage_write
designated_repro_test: null
acceptance:
- text: given a strata node with an explicit no-PII declaration, when a client_storage
    write occurs on that node with no per-call-site waiver, then it is flagged
  evidence:
  - tests/test_pii_structural_gate.py::TestClientStorageNoPii::test_fires_on_namespaced_session_storage_write
  - tests/test_pii_structural_gate.py::TestClientStorageNoPii::test_stays_quiet_without_no_pii_declaration
  - tests/test_pii_structural_gate.py::TestClientStorageNoPii::test_stays_quiet_on_unrelated_setitem_call
  - tests/test_pii_structural_gate.py::TestClientStorageNoPii::test_no_scan_without_any_no_pii_node
  - tests/test_pii_structural_gate.py::TestClientStorageNoPii::test_fires_on_local_storage_write
- text: given the same write with a reasoned per-call-site waiver present, when frob
    check runs, then it is accepted
  evidence:
  - tests/test_pii_structural_gate.py::TestClientStorageNoPii::test_waived_call_site_is_accepted
- text: given the cheaper first step, when this ticket is designed, then taint/dataflow
    analysis is explicitly deferred rather than blocking this ticket
  evidence:
  - tests/test_pii_structural_gate.py::TestClientStorageNoPii::test_no_scan_without_any_no_pii_node
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
H-1 (F-273). VERIFIED: PII gate (src/frob/gates/_pii_structural/) compares against strata carries declarations; there is currently no way for a node to declare it carries NO PII at all (an absence declaration), only positive carries() facts.

FINDING THIS WOULD HAVE CAUGHT: emails written to localStorage on the browser node, invisible because the browser node declares no carries at all -- so there is nothing for a PII rule to compare a client-side write against. SYS100/SYS103 check WHICH FILES hold client_storage capability, not WHAT flows into it; logging.ts sat on the allowlist so the capability ceiling was satisfied while the actual PII leak was invisible.

PREFER THE CHEAPER FIRST STEP OVER TAINT ANALYSIS, per the consumer's own explicit ranking and the coordinator's instruction: taint/dataflow from a carries("contact.email") source to a client_storage sink on a foreign node is the ambitious version and should NOT gate the cheap one. The cheap first step: extend the carries model so a node can declare it carries NO PII (an explicit negative/empty declaration, distinct from simply omitting carries()), and make any client_storage write on such a node require an explicit per-call-site waiver -- turning a silent gap into a mandatory, reviewable exception. FALLING BACK further: an INV rule bound to a docstring's own "redacted before storage" claim (e.g. logging.ts) would independently have forced a test feeding a real value through the redaction function -- note this as a second, complementary angle (ties to T-3954's docstring-claims-as-obligations theme) rather than a replacement for the carries fix.