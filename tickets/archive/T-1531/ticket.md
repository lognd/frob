---
id: T-1531
title: auto-repair the recurring land-refusal classes via Tier-A/B fix handlers (strata
  declarations, ticket edges, report refresh, draft renumber)
state: done
kind: feature
origin: human
created: '2026-08-04'
priority: high
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
- tests/unit/strata/test_sync_may.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: 'T-1531 auto-repair land-refusal classes: SYS104/SYS100 Tier-A handlers
    + writer + tests'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/strata/_sync_may.py
  reason: 'T-1531 auto-repair land-refusal classes: SYS104/SYS100 Tier-A handlers
    + writer + tests'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/unit/strata/test_sync_may.py
  reason: 'T-1531 auto-repair land-refusal classes: SYS104/SYS100 Tier-A handlers
    + writer + tests'
  actor: logan
  at: '2026-08-05'
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
designated_repro_test: null
evidence_changes:
- old_node: tests/test_gates.py::TestFixEngineTierA::test_sys104_interface_union_applies_via_apply_tier_a_fixes
  new_node: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
  reason: 'T-1870 deleted SYS104 (interface conformance) and its writer (frob sys
    sync-interface) in their entirety, per an explicit owner directive that no code
    path may auto-update declared public-symbol surface -- this evidence id''s test
    tested that now-removed functionality directly and has no successor test to rebind
    to (the feature is gone, not renamed). Rebound to the playbook''s own designated
    fallback for a citation with no natural surviving pytest surface (docs/guides/agent-playbook.md
    section 5''s precedent for docs-only/no-surface tickets): the CLI-dispatch integration
    test, tests/system/test_frob_self_model.py''s own model-file existence check.

    '
  actor: logan
  at: '2026-08-08'
- old_node: tests/test_gates.py::TestFixEngineTierA::test_sys104_no_design_dir_is_a_no_op
  new_node: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
  reason: 'T-1870 deleted SYS104 (interface conformance) and its writer (frob sys
    sync-interface) in their entirety, per an explicit owner directive that no code
    path may auto-update declared public-symbol surface -- this evidence id''s test
    tested that now-removed functionality directly and has no successor test to rebind
    to (the feature is gone, not renamed). Rebound to the playbook''s own designated
    fallback for a citation with no natural surviving pytest surface (docs/guides/agent-playbook.md
    section 5''s precedent for docs-only/no-surface tickets): the CLI-dispatch integration
    test, tests/system/test_frob_self_model.py''s own model-file existence check.

    '
  actor: logan
  at: '2026-08-08'
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
- old_node: tests/unit/strata/test_sync_may.py::TestSyncMayReport::test_no_drift_reports_clean
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
- old_node: tests/unit/strata/test_sync_may.py::TestSyncMayReport::test_widens_existing_via_list
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
- old_node: tests/unit/strata/test_sync_may.py::TestSyncMayReport::test_inserts_new_grant_when_none_declared
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
- old_node: tests/unit/strata/test_sync_may.py::TestSyncMayReport::test_no_design_files_reports_empty
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
- old_node: tests/unit/strata/test_sync_may.py::TestSyncMayReport::test_bad_design_file_propagates_load_error
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
- old_node: tests/unit/strata/test_sync_may.py::TestSyncMayReport::test_ambiguous_code_binding_propagates_as_error
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
- old_node: tests/unit/strata/test_sync_may.py::TestApplySyncMay::test_writes_only_changed_files
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
Every land refusal on 2026-08-04 was one of a small set of classes, each hand-fixed with the SAME deterministic recipe dozens of times. Extend the tiered fix engine (Tier-A deterministic; Tier-B T-1262 apply-verify-rollback) with handlers so land repairs them automatically before refusing: (1) SYS100 undeclared capability -> add the observed file to the named node's may-via list (sorted union; compact grammar); (2) SYS104 undeclared public symbol -> add to the node's compact attr interface=[...] list (sorted union); (3) COV002 changed-symbol-without-edge -> insert '# frob:ticket <landing-id>' above the symbol when the diff belongs to the landing ticket; (4) ClaimDivergence -> re-run done-report with the existing why text (the recap re-measures; this is exactly the documented manual recipe); (5) TICK006 phantom draft citation -> refile + renumber-to-cited-id when the citation names a draft absent from ledger+archive; (6) E501 introduced by merge -> ruff-format the specific lines (Tier-A fmt already close). Every applied fix goes through Tier-B verify-or-rollback and is loudly logged; anything not exactly matching a recipe still refuses. Success metric: a re-land of a branch whose only findings are in these classes succeeds with zero human edits. Builds on T-1481 (check --fix CLI) and complements T-1514's free pre-commit refusals.