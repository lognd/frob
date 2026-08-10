---
id: T-1545
title: 'Tier-A auto-fix: SYS100 EXTENDED-kind capability declaration (eval/process-control/ffi/...)'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine.py
- src/frob/strata/_sync_may.py
- src/frob/gates/_fix_engine_sync.py
- tests/unit/strata/test_sync_may.py
- tests/test_gates_fix_engine.py
- docs/modules/gates.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_fix_engine_sync.py
  reason: the SYS100 handler lives beside fix_sys100_may_via_union in _fix_engine_sync.py
    (T-1531's established split), and needs test coverage in both existing test homes
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/strata/test_sync_may.py
  reason: the SYS100 handler lives beside fix_sys100_may_via_union in _fix_engine_sync.py
    (T-1531's established split), and needs test coverage in both existing test homes
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_gates_fix_engine.py
  reason: the SYS100 handler lives beside fix_sys100_may_via_union in _fix_engine_sync.py
    (T-1531's established split), and needs test coverage in both existing test homes
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/gates.md
  reason: T-1545's own doc section update lives in docs/modules/gates.md (already
    edited); new SYS100-extended tests were added to tests/test_gates.py's TestFixEngineTierA
    class alongside the existing SYS100 tests
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_gates.py
  reason: T-1545's own doc section update lives in docs/modules/gates.md (already
    edited); new SYS100-extended tests were added to tests/test_gates.py's TestFixEngineTierA
    class alongside the existing SYS100 tests
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/strata/test_sync_may.py::TestSyncMayExtendedReport::test_inserts_whole_node_grant_for_extended_kind
- tests/unit/strata/test_sync_may.py::TestSyncMayExtendedReport::test_no_drift_reports_clean
- tests/unit/strata/test_sync_may.py::TestSyncMayExtendedReport::test_no_design_files_reports_empty
- tests/unit/strata/test_sync_may.py::TestApplySyncMayExtended::test_writes_only_changed_files
- tests/test_gates.py::TestFixEngineTierA::test_sys100_extended_whole_node_grant_applies_via_apply_tier_a_fixes
- tests/test_gates.py::TestFixEngineTierA::test_sys100_extended_no_design_dir_is_a_no_op
designated_repro_test: null
threat: null
component: null
---
Follow-up from T-1531: SYS100's EXTENDED case (eval/process-control/ffi/install-hook/sql/deserialize/html_render/fetch_url/client_storage, _selfconform.py::_extended_kind_violations) fires per-NODE with no per-file evidence -- there is no single observed file a Tier-A writer could add to a may via list without guessing which of a node's many bound files actually exercises the capability. Needs either a finer per-file extended-kind scan before an auto-fix is even possible, or a deliberately-conservative whole-node (via-less) grant-insertion policy with its own written justification. T-1531's fix_sys100_may_via_union only handles the CORE (net/fs-write/exec, THREAT004-delegated) case.