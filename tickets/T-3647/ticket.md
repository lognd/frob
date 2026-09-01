---
id: T-3647
title: 'post-land sweep regression from T-3593: 4 new (rule, file) identit(ies), 48
  finding(s) (DRIFT002)'
state: queued
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
- src/frob/vet/_capability_core.py
- src/frob/vet/_capability_python.py
- src/frob/vet/_capability_scan.py
- src/frob/vet/_supplychain.py
findings:
- - DRIFT002
  - src/frob/vet/_capability_core.py
- - DRIFT002
  - src/frob/vet/_capability_python.py
- - DRIFT002
  - src/frob/vet/_capability_scan.py
- - DRIFT002
  - src/frob/vet/_supplychain.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-3593 at commit 98ffba11436716408dace9fbcb021525cc3b0d57 found 4 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (4), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 48 actual finding(s) across those 4 identit(ies).

New (rule, file) identit(ies) filed here:

- DRIFT002  src/frob/vet/_capability_core.py
- DRIFT002  src/frob/vet/_capability_python.py
- DRIFT002  src/frob/vet/_capability_scan.py
- DRIFT002  src/frob/vet/_supplychain.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DRIFT002  src/frob/vet/_capability_core.py  -> attributed to T-3593 (commit 98ffba114367, already closed/dropped -- filed below) via tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCBindingResolution.test_operation_names_registry_entry_for_macro_alias -> src/frob/vet/_capability.py::_scan_file_operations -> src/frob/vet/_capability_core.py::_non_executable_byte_spans -> src/frob/vet/_capability_core.py::_docstring_byte_spans_from_tree
- DRIFT002  src/frob/vet/_capability_python.py  -> attributed to T-3593 (commit 98ffba114367, already closed/dropped -- filed below) via tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCBindingResolution.test_operation_names_registry_entry_for_macro_alias -> src/frob/vet/_capability.py::_scan_file_operations -> src/frob/vet/_capability.py::_extra_binding_operations -> src/frob/vet/_capability_python.py::_python_binding_operations -> src/frob/vet/_capability_python.py::_python_resolved_candidates -> src/frob/vet/_capability_python.py::_build_py_alias_table -> src/frob/vet/_capability_python.py::_record_py_alias -> src/frob/vet/_capability_python.py::_record_py_destructure_alias
- DRIFT002  src/frob/vet/_capability_scan.py  -> attributed to T-3593 (commit 98ffba114367, already closed/dropped -- filed below) via tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan.test_decode_to_exec_absent_when_separate -> src/frob/vet/_capability_scan.py::_decode_to_exec_signal
- DRIFT002  src/frob/vet/_supplychain.py  -> attributed to T-3593 (commit 98ffba114367, already closed/dropped -- filed below) via tests/vet_suite/test_supply_chain.py::TestSupplyChainCiActionPin.test_no_workflows_dir_not_flagged -> src/frob/vet/_supplychain.py::_unpinned_ci_action_violations -> src/frob/vet/_supplychain.py::_is_full_commit_sha -> src/frob/vet/_supplychain.py::_HEX_DIGITS

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.