## Done report

Split src/frob/tickets/_land.py (4973 lines) into four cohesive modules
following the verbatim-move pattern _evidence.py/_reporting.py set at
T-1171, per this ticket's own lineage note:

- src/frob/tickets/_land_merge.py: ledger merge/splice machinery
  (splice_ledger, newest-wins per-ticket resolution, union-zone conflict
  resolution, out-of-scope auto-resolve, wip-commit staging) plus the
  small git-primitive helpers (_land_internal_git_env,
  _describe_git_failure, _is_ignored_path_refusal, _rev_parse,
  _true_merge_base) shared with the finalize stage.
- src/frob/tickets/_land_verify.py: post-merge claim/evidence
  reverification (_reverify_evidence_post_merge,
  _reverify_done_report_claims_post_merge, _reverify_test_count_claim,
  _reverify_gate_state_claim, _reverify_gate_findings_by_identity).
- src/frob/tickets/_land_finalize.py: finalize/close/squash-apply/release
  (draft finalization, sibling-draft renumbering, close, squash-and-
  splice, completeness assertion, release-bump/uv.lock/native-rebuild).
- src/frob/tickets/_land.py: retains the land lock/repair-marker
  machinery, the land()/_land_locked orchestrator, and the pre-merge
  preflight validators, importing the split-out families back in
  explicitly. 4973 -> ~1170 lines; the other three modules are
  ~1720/~515/~1730 lines respectively (still over LARGE001's 800-line
  threshold individually -- filed as residue, see below; follow-up
  filed and landed as T-1189).

Every moved function keeps its original body, docstring, and
frob:ticket/frob:tests directives verbatim (zero caller-visible behavior
change). Fixed two verbatim-move mechanics this exposed:
- A frob:doc anchor and two frob:ticket comments were orphaned at chunk
  boundaries during the mechanical line-range extraction (land's own
  frob:doc docs/modules/tickets.md#frob-ticket-land header, and
  frob:ticket T-0907/T-0761 comments above _verified_reset_root/
  _rev_parse) -- reattached to the correct function in the correct file.
- tests/test_ticket_land.py, tests/test_tickets_collision.py,
  tests/test_evidence_integrity.py, and tests/test_tickets_cmd_evidence.py
  monkeypatched/imported several moved private symbols via the
  frob.tickets._land module attribute directly (run_argv, current_branch,
  _render_ledger, _merge_ledger_tickets, _rev_parse, _worktree_full_
  changeset, _tick005_land_regressions, _splice_only_ticket, and others)
  -- the exact T-1152-class hazard this ticket's own body warned about.
  Repointed each to the module the real call site now lives in (verified
  per-site by reading the actual git-subprocess call each patch targets,
  not a blanket find/replace), and updated docs/modules/tickets.md's
  frob:describes anchors for splice_ledger/_assert_land_complete/
  _worktree_full_changeset/_apply_release_bump/_maybe_rebuild_natives to
  their new module paths.

Widened T-1186's scope (frob ticket scope --add) to cover the new
modules plus the four test files and the two non-test call sites
(_land_cmd.py, _tickets_gate.py) that imported a moved private symbol --
this is what the split's own caller-repoint touched, not new work beyond
the split.

Added three frob:waive DUP001 and one frob:waive DUP002 comments where
the split's file-move (not a body change) caused the dup-detector to
pair a moved function against unrelated code it was never paired against
before (or, for DUP002, against its own pre-existing same-shape sibling
now living in a different file) -- same disposition T-1171 set precedent
for at src/frob/tickets/_reporting.py:254.

Filed: T-1186 residue -- _land_merge.py (~1720 lines) and
_land_finalize.py (~1730 lines) still exceed LARGE001's 800-line
threshold individually; a further split was out of this land's budget
per the ticket's own note ("likely its own multi-land series"). New
ticket filed for the remaining split.

Gates: frob check --ticket T-1186 clean (0 errors, 590 warnings, 685
waived) after ruff format on the three touched land modules + the test
file, and frob ticket sweep T-1186 refreshed. frob test --base main:
exit 0.

### Changed
```
 tickets.md | 145 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 143 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLandCompleteness::test_land_brings_tracked_edit_untracked_new_file_and_deletion` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandCompleteness::test_incomplete_land_fails_loudly_and_commits_nothing` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandCompleteness::test_worktree_pointed_at_same_branch_as_main_is_refused_not_silently_empty` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSyncGateRulesCallback::test_sync_gate_rules_none_is_noop` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSyncGateRulesCallback::test_sync_gate_rules_applies_and_stages` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSyncGateRulesCallback::test_sync_gate_rules_failure_unwinds` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUnionZoneMerge::test_keyed_lines_union_composes` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUnionZoneMerge::test_keyed_lines_union_refuses` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUnionZoneMerge::test_resolve_stages` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUnionZoneMerge::test_append_only_union_concatenates` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSigkillMidStaging::test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandRefusesOnTerminalStateRegression::test_land_refuses_and_unwinds_when_sweep_finds_a_regression` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr::test_describe_git_failure_includes_argv_and_stderr` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr::test_describe_git_failure_includes_spawn_error` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr::test_wip_commit_failure_logs_stderr` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandInternalEnvThroughHook::test_land_through_changelog_guard_hook_succeeds` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandInternalEnvThroughHook::test_land_internal_git_env_restores_prior_value` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_id_title_mismatch_is_refused_not_silently_overwritten` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestSpliceOnlyTicketIdTitleMismatchRefusal::test_same_id_same_title_still_resolves_via_newer` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 20 passed (from 20 evidence id(s))
- gates: 0 error(s), 589 warning(s), 685 waived
- error-findings: none (measured, zero errors)
