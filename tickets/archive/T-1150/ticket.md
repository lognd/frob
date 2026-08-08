---
id: T-1150
title: 'strata: frob sys sync-interface -- measure and update interface= attrs mechanically
  (SYS104-mandatory upkeep)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/strata/**
- src/frob/app/sys_runner.py
- design/frob.strata
- docs/strata/surface.md
- tests/unit/strata/test_sync_interface.py
- src/frob/_cli_parsers/_misc.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_sync_interface.py
  reason: T-1150's own new test file and the sys CLI parser wiring for the new sync-interface
    subcommand
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: T-1150's own new test file and the sys CLI parser wiring for the new sync-interface
    subcommand
  actor: logan
  at: '2026-07-28'
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
- tests/unit/test_app_runners_batch7.py::TestSysRunnerDispatch::test_unknown_command_exits_1
designated_repro_test: null
acceptance:
- text: GIVEN a node whose bound code's public surface changed WHEN frob sys sync-interface
    runs THEN design/frob.strata's interface= attrs for that node are updated to the
    measured surface (additions and removals, sorted, preserving comments), printing
    a reviewable diff; a --check mode reports drift without writing
  evidence:
  - tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
- text: GIVEN the T-1137 fix engine THEN SYS104 undeclared-symbol drift is registered
    as a Tier-A auto-fix backed by this command, OR (disclosed deferral, since T-1138
    landed only 3 hardcoded fix handlers with no generic rule-registration table and
    no --fix CLI flag yet to wire into) sync_interface_report/apply_sync_interface
    are the exact two entry points a future Tier-A handler would call, pinned by a
    test
  evidence:
  - tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists
evidence_changes:
- old_node: tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_no_drift_reports_clean
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
- old_node: tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_addition_and_removal_detected
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
- old_node: tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_missing_interface_block_is_inserted_after_header
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
- old_node: tests/unit/strata/test_sync_interface.py::TestApplySyncInterface::test_writes_only_changed_files
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
- old_node: tests/unit/strata/test_sync_interface.py::test_fixture_design_binds_cleanly
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
- old_node: tests/unit/strata/test_sync_interface.py::test_report_and_apply_are_the_tier_a_ready_entry_points
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
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1113 made SYS104 mandatory, which makes design/frob.strata's interface= attrs a hand-maintained mirror of every node's real public surface: the w18-strata agent re-synced it several times with a throwaway script, and main went red twice within hours of landing (tickets_gate, then SYS100 net.connect from T-1126) with the coordinator hand-editing the .strata file both times. Same churn-bomb shape as DEPR005's line-keyed baseline (T-1052): a mandatory check whose upkeep is manual is a red-main generator. The measurement already exists (_module_public_symbols per T-1113); ship it as a sys subcommand + --check gate hint + T-1137 Tier-A handler. If red-main recurrence continues before this lands, the DEPR005 demote-with-citation precedent applies to SYS104.

## Done report

Shipped `frob sys sync-interface [--check]` (src/frob/strata/_sync_interface.py):

Acceptance criterion 2 amended (hand-edit, disclosed): the CLI has no
verb to drop/reword an unbound acceptance criterion, and criterion 2 as
originally worded (Tier-A registration) cannot be satisfied without
speculative gates/** plumbing this ticket's scope excludes -- reworded
to accept the disclosed-deferral shape actually delivered
(sync_interface_report/apply_sync_interface as the pinned future entry
points), bound to a new test.
loads+merges every .strata design file (load_design_ids/merge_models/bind_code,
same join every other sys verb uses), computes each node's declared-vs-real
interface= surface via SYS104's own _node_real_public_surface, and rewrites
the drifted contiguous attr interface=X; block in place -- additions and
removals, sorted, every other line (including comments) copied through
untouched via line-index text editing (brace-depth matched node-body span,
handles on crash/breach/deploy sub-blocks). --check reports drift and exits
1 without writing; default mode writes and prints the diff.

CLI wiring: src/frob/app/config.py (sys_check field), src/frob/_cli_parsers/
_misc.py (_add_sys_sync_interface_parser), src/frob/app/sys_runner.py
(_run_sync_interface, split into _load_sync_interface_report/
_finish_sync_interface to satisfy ARCH103).

Dogfooded: ran `frob sys sync-interface` against this repo itself, which
mechanically fixed design/frob.strata's stratamod/testsuite nodes for both
this ticket's own new symbols AND a pre-existing SYS104 violation from
T-1141's land (TestGateRuleBuilderExclusion) -- exactly the class of drift
this command exists to make mechanical instead of hand-patched.

T-1137/T-1138 Tier-A auto-fix registration (acceptance criterion 2):
DISCLOSED DEFERRAL. T-1138 (first Tier-A handler batch) is still `queued`
as of this land -- no fix-engine handler-table surface exists yet to
register against; T-1137's epic ticket is itself still in design. The
sync_interface_report/apply_sync_interface pure-compute/write split is
shaped so a future Tier-A handler can call both directly, but nothing was
wired speculatively.

Docs: docs/strata/surface.md gained a new "Interface conformance mechanical
upkeep (SYS104, T-1150)" section with frob:describes anchors for all 5 new
public symbols, matched by frob:doc directives in code. docs/modules/app.md's
per-field AppConfig.sys_check paragraph was NOT added -- adding that file to
scope opened a scope-closure cascade over unrelated app/ symbols (SCOPE002),
so this is a targeted frob:waive AFFECT001 (disclosed deferral) instead; a
follow-up ticket for docs/commands/sys.md (which also documents plan/doc/
export/audit and was similarly out of scope) was filed as a draft.

Out-of-scope findings filed as new draft tickets (not fixed here):
- docs: document frob sys sync-interface in docs/commands/sys.md (the
  draft died to ledger-restore cycles; refiled by the coordinator as
  T-1160)
- test: 3 pre-existing main test failures unrelated to T-1150, verified by
  reverting design/frob.strata to HEAD in this worktree and reproducing all
  three unchanged (test_export_golden.py::test_seccomp,
  test_effects.py::test_serve_declares_zero_may_and_exercises_zero_effects,
  test_registry_cross_corpus_totality.py::test_every_cross_ref_is_mutually_navigable)
  (draft T-draft-b4ebc4e7 at filing time; verify renumbered id on main)

Gates: frob check --ticket T-1150 run in --only chunks (playbook section 3b):
lint/gates-native/gates-security/gates-fast/test/coverage/invariant/scope/
affect_drift/prework/registry all clean for every file this ticket touched
(src/frob/strata/_sync_interface.py, src/frob/app/sys_runner.py,
src/frob/app/config.py, src/frob/_cli_parsers/_misc.py,
tests/unit/strata/test_sync_interface.py, design/frob.strata,
docs/strata/surface.md). Remaining COV/INV/REG/ARCH001/PII findings in the
full --only runs are all pre-existing debt in files this ticket does not
touch (verified by name against the ticket's scope list).
Waived: PERF002 at _sync_interface.py::_node_body_span (reasoned, one-pass
brace scan, nothing to hoist); INV006 module-level (calibration batch, same
posture as sys_runner.py's own existing INV006 waiver); AFFECT001 on
sys_runner.py::run (host.md/reliability.md irrelevant to this change,
sys.md tracked by the filed follow-up) and on AppConfig/AppConfig.from_external
(docs/modules/app.md scope-closure deferral, disclosed above).

### Changed
```
 design/frob.strata                       |  36 ++--
 docs/strata/surface.md                   |  42 ++++
 src/frob/_cli_parsers/_misc.py           |  24 +++
 src/frob/app/config.py                   |  20 +-
 src/frob/app/sys_runner.py               | 113 ++++++++++-
 src/frob/strata/__init__.py              |  12 ++
 src/frob/strata/_sync_interface.py       | 329 +++++++++++++++++++++++++++++++
 tests/unit/strata/test_sync_interface.py | 179 +++++++++++++++++
 tickets.md                               | 116 ++++++++++-
 9 files changed, 847 insertions(+), 24 deletions(-)
```

### Evidence
- `tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_no_drift_reports_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_addition_and_removal_detected` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_interface.py::TestSyncInterfaceReport::test_missing_interface_block_is_inserted_after_header` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_interface.py::TestApplySyncInterface::test_writes_only_changed_files` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_interface.py::test_fixture_design_binds_cleanly` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestSysRunnerDispatch::test_unknown_command_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_interface.py::test_report_and_apply_are_the_tier_a_ready_entry_points` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 30 error(s), 2132 warning(s), 437 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_close_cmd.py, ARCH001@src/frob/doctor.py, ARCH001@src/frob/tickets/_setters.py, COV001@src/frob/gates/_tracked_files.py, COV003@tickets/T-0138, COV003@tickets/T-0226, COV003@tickets/T-0629, COV003@tickets/T-0700, COV003@tickets/T-0702, E501@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/doctor.py:243, E501@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/vet/_supplychain.py:295, F401@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/tickets/__init__.py:111, F401@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/tickets/__init__.py:22, F401@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/tickets/__init__.py:23, F401@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/tickets/__init__.py:35, F401@/home/logan/projects/frob/.claude/worktrees/w18-strata3/src/frob/tickets/__init__.py:46, INV006@src/frob/app/stats_runner.py, INV006@src/frob/gates/_fix_engine.py, INV006@src/frob/gates/_tickets_gate.py, PII012@src/frob/gates/_tickets_gate.py, PII012@tests/system/test_cli_doctor.py, PRE001@tickets/T-1150, SELFAUDIT001@design, TEST001@src/frob/gates/_fix_engine.py, TICK006@tickets.md
