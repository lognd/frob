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
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
no_scope_declared: false
no_scope_declared_reason: null
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
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
designated_repro_test: null
evidence_changes:
- old_node: tests/test_gates.py::TestFixEngineTierA::test_sys100_extended_whole_node_grant_applies_via_apply_tier_a_fixes
  new_node: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
  reason: 'T-2922 deleted fix_sys100_may_via_union/fix_sys100_extended_whole_node_grant

    and their entire acceptance-test surface -- the SYS100 auto-widening

    policy this ticket''s evidence tested is deleted, not renamed, per an

    explicit owner directive that a may= grant may never be silently

    widened to match observed capability use (supersedes T-1623/T-1628).

    There is no successor test to rebind to, since the feature itself is

    gone. Rebound to the playbook''s own designated fallback for a citation

    with no natural surviving pytest surface (docs/guides/agent-playbook.md

    section 5''s precedent, the same one T-1870/T-1774 already used for the

    identical shape when SYS104''s writer was deleted): the CLI-dispatch

    integration test, tests/system/test_frob_self_model.py''s own

    model-file existence check.

    '
  actor: logan
  at: '2026-08-25'
- old_node: tests/test_gates.py::TestFixEngineTierA::test_sys100_extended_no_design_dir_is_a_no_op
  new_node: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
  reason: 'T-2922 deleted fix_sys100_may_via_union/fix_sys100_extended_whole_node_grant

    and their entire acceptance-test surface -- the SYS100 auto-widening

    policy this ticket''s evidence tested is deleted, not renamed, per an

    explicit owner directive that a may= grant may never be silently

    widened to match observed capability use (supersedes T-1623/T-1628).

    There is no successor test to rebind to, since the feature itself is

    gone. Rebound to the playbook''s own designated fallback for a citation

    with no natural surviving pytest surface (docs/guides/agent-playbook.md

    section 5''s precedent, the same one T-1870/T-1774 already used for the

    identical shape when SYS104''s writer was deleted): the CLI-dispatch

    integration test, tests/system/test_frob_self_model.py''s own

    model-file existence check.

    '
  actor: logan
  at: '2026-08-25'
- old_node: tests/unit/strata/test_sync_may.py::TestSyncMayExtendedReport::test_inserts_whole_node_grant_for_extended_kind
  new_node: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
  reason: 'T-2920 (the shrink-only ratchet epic, unblocked once T-2922 unwired the

    last caller) deleted _sync_may.py''s SYS100 core+extended may= auto-

    widening writer entirely -- the feature this evidence tested. There is

    no successor test to rebind to, since the widening functionality itself

    is gone by design (a node''s may= ceiling must never be auto-widened;

    T-1623/T-1628''s policy is superseded). Rebound to the same fallback

    T-1870/T-1774/T-2922 already used for this identical shape (a deleted

    feature''s evidence with no natural surviving pytest surface,

    docs/guides/agent-playbook.md section 5): the CLI-dispatch integration

    test, tests/system/test_frob_self_model.py''s own model-file existence

    check.

    '
  actor: logan
  at: '2026-08-26'
- old_node: tests/unit/strata/test_sync_may.py::TestSyncMayExtendedReport::test_no_drift_reports_clean
  new_node: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
  reason: 'T-2920 (the shrink-only ratchet epic, unblocked once T-2922 unwired the

    last caller) deleted _sync_may.py''s SYS100 core+extended may= auto-

    widening writer entirely -- the feature this evidence tested. There is

    no successor test to rebind to, since the widening functionality itself

    is gone by design (a node''s may= ceiling must never be auto-widened;

    T-1623/T-1628''s policy is superseded). Rebound to the same fallback

    T-1870/T-1774/T-2922 already used for this identical shape (a deleted

    feature''s evidence with no natural surviving pytest surface,

    docs/guides/agent-playbook.md section 5): the CLI-dispatch integration

    test, tests/system/test_frob_self_model.py''s own model-file existence

    check.

    '
  actor: logan
  at: '2026-08-26'
- old_node: tests/unit/strata/test_sync_may.py::TestSyncMayExtendedReport::test_no_design_files_reports_empty
  new_node: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
  reason: 'T-2920 (the shrink-only ratchet epic, unblocked once T-2922 unwired the

    last caller) deleted _sync_may.py''s SYS100 core+extended may= auto-

    widening writer entirely -- the feature this evidence tested. There is

    no successor test to rebind to, since the widening functionality itself

    is gone by design (a node''s may= ceiling must never be auto-widened;

    T-1623/T-1628''s policy is superseded). Rebound to the same fallback

    T-1870/T-1774/T-2922 already used for this identical shape (a deleted

    feature''s evidence with no natural surviving pytest surface,

    docs/guides/agent-playbook.md section 5): the CLI-dispatch integration

    test, tests/system/test_frob_self_model.py''s own model-file existence

    check.

    '
  actor: logan
  at: '2026-08-26'
- old_node: tests/unit/strata/test_sync_may.py::TestApplySyncMayExtended::test_writes_only_changed_files
  new_node: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
  reason: 'T-2920 (the shrink-only ratchet epic, unblocked once T-2922 unwired the

    last caller) deleted _sync_may.py''s SYS100 core+extended may= auto-

    widening writer entirely -- the feature this evidence tested. There is

    no successor test to rebind to, since the widening functionality itself

    is gone by design (a node''s may= ceiling must never be auto-widened;

    T-1623/T-1628''s policy is superseded). Rebound to the same fallback

    T-1870/T-1774/T-2922 already used for this identical shape (a deleted

    feature''s evidence with no natural surviving pytest surface,

    docs/guides/agent-playbook.md section 5): the CLI-dispatch integration

    test, tests/system/test_frob_self_model.py''s own model-file existence

    check.

    '
  actor: logan
  at: '2026-08-26'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Follow-up from T-1531: SYS100's EXTENDED case (eval/process-control/ffi/install-hook/sql/deserialize/html_render/fetch_url/client_storage, _selfconform.py::_extended_kind_violations) fires per-NODE with no per-file evidence -- there is no single observed file a Tier-A writer could add to a may via list without guessing which of a node's many bound files actually exercises the capability. Needs either a finer per-file extended-kind scan before an auto-fix is even possible, or a deliberately-conservative whole-node (via-less) grant-insertion policy with its own written justification. T-1531's fix_sys100_may_via_union only handles the CORE (net/fs-write/exec, THREAT004-delegated) case.