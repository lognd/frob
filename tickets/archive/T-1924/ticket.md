---
id: T-1924
title: Finish T-1911's Tier-A snapshot-param drop on the 5 handlers in _fix_engine_sync.py
state: done
kind: bug
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fix_engine_sync.py
- src/frob/gates/_fix_engine.py
- tests/test_gates.py
- tests/unit/gates/test_sys_interface_canonical_order.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: AFFECT001 requires the affects()-closure doc anchor to move with the code
    in the same diff; docs/modules/gates.md is the doc the touched handlers' own frob:doc
    directives point at
  actor: logan
  at: '2026-08-09'
evidence:
- tests/test_gates.py::TestFixEngineTierABatch2::test_reg010_files_missing_entries_and_reverifies_clean
- tests/test_gates.py::TestFixEngineTierABatch2::test_reg010_already_in_sync_is_a_no_op
- tests/test_gates.py::TestFixEngineTierABatch2::test_rel002_resyncs_pyproject_and_uv_lock_from_manifest
- tests/test_gates.py::TestFixEngineTierABatch2::test_rel002_already_in_sync_touches_nothing
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
designated_repro_test: tests/test_gates.py::TestFixEngineTierABatch2::test_reg010_files_missing_entries_and_reverifies_clean
evidence_changes:
- old_node: tests/test_gates.py::TestFixEngineTierA::test_sys100_may_via_union_applies_via_apply_tier_a_fixes
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
- old_node: tests/test_gates.py::TestFixEngineTierA::test_sys100_no_design_dir_is_a_no_op
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
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-1911 fixed the too-strict-for-purpose Tier-A dispatch signature on the
two handlers reachable from this worktree without a lease conflict
(fix_fmt001_directive_wrap, fix_e501_merge_introduced in
src/frob/gates/_fix_engine_text.py: dropped their unused GraphSnapshot
parameter entirely so a call site can no longer pass bare None -- ty now
statically refuses too-many-positional-arguments instead).

The SAME pattern (a `del snapshot  # signature uniformity only` body with
a non-Optional GraphSnapshot parameter no caller needs) also exists on
five more handlers in src/frob/gates/_fix_engine_sync.py:
fix_reg010_registry_sync, fix_rel002_release_sync, fix_sys100_may_via_union,
fix_sys100_extended_whole_node_grant, and fix_sys_interface_canonical_order
(the exact function T-1896/T-1900/T-1906 repeatedly re-broke -- the
motivating incident for T-1911 itself). That file was held by T-1904's
live cross-worktree lease for this ticket's entire duration, so none of
these five could be touched here.

Apply the identical fix to all five once T-1904's lease clears: drop the
GraphSnapshot parameter, update TIER_A_HANDLERS' lambda wrappers in
src/frob/gates/_fix_engine.py to stop forwarding snapshot to them, and
update every test call site (tests/test_gates.py,
tests/unit/gates/test_sys_interface_canonical_order.py, and any others
`grep -n "fix_reg010_registry_sync\|fix_rel002_release_sync\|fix_sys100_may_via_union\|fix_sys100_extended_whole_node_grant\|fix_sys_interface_canonical_order" tests/` finds).

frob:no-behavior-change reason="pure dispatch-signature refactor, same shape T-1911 already established as behavior-preserving: drops an unused, del-ed GraphSnapshot parameter from 4 Tier-A handlers and stops TIER_A_HANDLERS' lambdas from forwarding it -- no handler body's actual logic changes, so the designated repro test genuinely passes at both the parent and the fix; a FAILED_AT_PARENT result would falsify this claim, not confirm it"