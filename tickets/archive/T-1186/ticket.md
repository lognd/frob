---
id: T-1186
title: 'arch: split tickets/_land.py (4973 lines) -- T-1171 residue'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- docs/modules/tickets.md
- src/frob/tickets/_land_merge.py
- src/frob/tickets/_land_verify.py
- src/frob/tickets/_land_finalize.py
- tests/test_ticket_land.py
- tests/test_tickets_collision.py
- tests/test_evidence_integrity.py
- tests/test_tickets_cmd_evidence.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/gates/_tickets_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_merge.py
  reason: T-1186 verbatim-move split of _land.py (4973 lines) into _land_merge/_land_verify/_land_finalize
    per the ticket's own lineage note -- callers importing moved private symbols (tests,
    _land_cmd.py, _tickets_gate.py) needed repointing to the new module paths, and
    the new modules themselves are the direct output of this ticket's split
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/tickets/_land_verify.py
  reason: T-1186 verbatim-move split of _land.py (4973 lines) into _land_merge/_land_verify/_land_finalize
    per the ticket's own lineage note -- callers importing moved private symbols (tests,
    _land_cmd.py, _tickets_gate.py) needed repointing to the new module paths, and
    the new modules themselves are the direct output of this ticket's split
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/tickets/_land_finalize.py
  reason: T-1186 verbatim-move split of _land.py (4973 lines) into _land_merge/_land_verify/_land_finalize
    per the ticket's own lineage note -- callers importing moved private symbols (tests,
    _land_cmd.py, _tickets_gate.py) needed repointing to the new module paths, and
    the new modules themselves are the direct output of this ticket's split
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_ticket_land.py
  reason: T-1186 verbatim-move split of _land.py (4973 lines) into _land_merge/_land_verify/_land_finalize
    per the ticket's own lineage note -- callers importing moved private symbols (tests,
    _land_cmd.py, _tickets_gate.py) needed repointing to the new module paths, and
    the new modules themselves are the direct output of this ticket's split
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_tickets_collision.py
  reason: T-1186 verbatim-move split of _land.py (4973 lines) into _land_merge/_land_verify/_land_finalize
    per the ticket's own lineage note -- callers importing moved private symbols (tests,
    _land_cmd.py, _tickets_gate.py) needed repointing to the new module paths, and
    the new modules themselves are the direct output of this ticket's split
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_evidence_integrity.py
  reason: T-1186 verbatim-move split of _land.py (4973 lines) into _land_merge/_land_verify/_land_finalize
    per the ticket's own lineage note -- callers importing moved private symbols (tests,
    _land_cmd.py, _tickets_gate.py) needed repointing to the new module paths, and
    the new modules themselves are the direct output of this ticket's split
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_tickets_cmd_evidence.py
  reason: T-1186 verbatim-move split of _land.py (4973 lines) into _land_merge/_land_verify/_land_finalize
    per the ticket's own lineage note -- callers importing moved private symbols (tests,
    _land_cmd.py, _tickets_gate.py) needed repointing to the new module paths, and
    the new modules themselves are the direct output of this ticket's split
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: T-1186 verbatim-move split of _land.py (4973 lines) into _land_merge/_land_verify/_land_finalize
    per the ticket's own lineage note -- callers importing moved private symbols (tests,
    _land_cmd.py, _tickets_gate.py) needed repointing to the new module paths, and
    the new modules themselves are the direct output of this ticket's split
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/gates/_tickets_gate.py
  reason: T-1186 verbatim-move split of _land.py (4973 lines) into _land_merge/_land_verify/_land_finalize
    per the ticket's own lineage note -- callers importing moved private symbols (tests,
    _land_cmd.py, _tickets_gate.py) needed repointing to the new module paths, and
    the new modules themselves are the direct output of this ticket's split
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_ticket_land.py::TestLandCompleteness::test_land_brings_tracked_edit_untracked_new_file_and_deletion
- tests/test_ticket_land.py::TestLandCompleteness::test_incomplete_land_fails_loudly_and_commits_nothing
- tests/test_ticket_land.py::TestLandCompleteness::test_worktree_pointed_at_same_branch_as_main_is_refused_not_silently_empty
- tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land
- tests/test_ticket_land.py::TestSyncGateRulesCallback::test_sync_gate_rules_none_is_noop
- tests/test_ticket_land.py::TestSyncGateRulesCallback::test_sync_gate_rules_applies_and_stages
- tests/test_ticket_land.py::TestSyncGateRulesCallback::test_sync_gate_rules_failure_unwinds
- tests/test_ticket_land.py::TestUnionZoneMerge::test_keyed_lines_union_composes
- tests/test_ticket_land.py::TestUnionZoneMerge::test_keyed_lines_union_refuses
- tests/test_ticket_land.py::TestUnionZoneMerge::test_resolve_stages
- tests/test_ticket_land.py::TestUnionZoneMerge::test_append_only_union_concatenates
- tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry
- tests/test_ticket_land.py::TestLandRefusesOnTerminalStateRegression::test_land_refuses_and_unwinds_when_sweep_finds_a_regression
- tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr::test_describe_git_failure_includes_argv_and_stderr
- tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr::test_describe_git_failure_includes_spawn_error
- tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr::test_wip_commit_failure_logs_stderr
- tests/test_ticket_land.py::TestLandInternalEnvThroughHook::test_land_through_changelog_guard_hook_succeeds
- tests/test_ticket_land.py::TestLandInternalEnvThroughHook::test_land_internal_git_env_restores_prior_value
- tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_id_title_mismatch_is_refused_not_silently_overwritten
- tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_same_id_same_title_still_resolves_via_newer
designated_repro_test: null
threat: null
component: null
---
T-1171 landed the __init__.py half of its own scope (the done-report/
review/drop/attach family, extracted into src/frob/tickets/_reporting.py:
mutate_labels, brief_ticket, compose_done_report/_capture_done_report_
claims/set_done_report, record_failure, _resolve_review_commit/
record_review/has_approved_review_for_commit, drop_ticket, and the
attach/_attachment_bytes/_next_attachment_path/_record_attachment
quartet -- __init__.py: 1266 -> ~640 lines).

The _land.py half of T-1171's own scope was NOT touched this dispatch,
budget did not allow both in one land: src/frob/tickets/_land.py is
still 4973 lines (unchanged across T-1108/T-1122/T-1123/T-1151/T-1152/
T-1171), still triggering LARGE001, and still needs the preflight/
merge-splice/verify/sweep submodule split T-1108's original plan called
for.

Follow the same verbatim-move pattern as _evidence.py/_reporting.py:
private module(s) re-exported from _land.py or __init__ via explicit
imports, zero caller-visible behavior change, existing tests as the
safety net, carry frob:ticket/frob:doc/frob:tests directives verbatim,
repoint docs/modules/tickets.md's frob:describes anchors and any
tests/*.py frob:tests directives at the new module path(s), add
frob:ticket edges to any test class/method a directive-repoint touches
(COV002), carry a file-level INV006 split-module waiver (T-0585
calibration-batch precedent) if the moved prose trips it, watch for
tests that monkeypatch a moved function via the PACKAGE attribute
(land_mod.<name> or tickets_mod.<name>) -- those need a late `from
frob.tickets import <name>` / `from frob.tickets._land import <name>`
inside the moved function body instead of a module-top-level binding
(the same write_ticket/bare-subprocess hazards T-1152 hit).

Given the file's size (4973 lines), this is likely its OWN multi-land
series rather than one land -- consider splitting the plan itself into
2-3 tickets (e.g. preflight+merge-splice as one family, verify+sweep as
another) rather than one ticket trying to move the whole file at once.