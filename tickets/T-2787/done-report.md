## Done report

Changed:
src/frob/gates/_profile_schema.py
src/frob/gates/_rule_id_scan.py
src/frob/gates/_testing_schema.py
src/frob/gates/_waive.py
src/frob/gates/_wire.py
tests/gates/test_rule_id_scan_branches.py
src/frob/tickets/_accept.py
src/frob/tickets/_draft_finalize.py
src/frob/tickets/_evidence.py
src/frob/tickets/_leases.py
src/frob/verify/_attribution.py
src/frob/verify/_drain.py
src/frob/verify/_watermark.py

Read T-2557's diff (9b6c83d0a) and T-2778's diff (74304eff6) before
reformatting -- both added real functional content (TICK013 gate in
_tickets_gate.py/_waive.py; the keyword-argument-value WIRE001 pattern
in _wire.py) that had already been auto-formatted by their own lands'
Tier-A fix step, so no separate reformat was needed/possible for
_tickets_gate.py (dropped from this batch's file list -- already
clean per `ruff format --check`); _waive.py and _wire.py still had
pending format drift elsewhere in the file and were reformatted here.

Evidence: 13 pytest node ids bound, one covering each touched file
(module-level test files run in full: 120 collected/0 failed across
test_profile_table_schema.py, test_testing_table_schema.py,
test_waive_gate.py, test_draft_finalize_attachments.py,
test_tickets_acceptance.py, test_wire001_callback_keyword_argument.py;
plus 68 collected/0 failed across test_rule_id_scan_branches.py,
test_tick013_gate.py, test_attribution.py,
test_attribution_module_scope.py, test_drain.py, test_watermark.py).

Pre-existing failures (reproduced on unmodified main at the primary
checkout, not caused by this change -- this batch's diffs to
_evidence.py/_leases.py are pure whitespace, no logic touched):
tests/test_ticket_leases.py::TestCommitFullLedgerChange::test_archive_cli_leaves_repo_clean
tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for
tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_verb_leaves_repo_clean[component/kind/priority/tier]
tests/test_ticket_evidence.py::TestEvidenceCmdCwd::test_relative_probe_only_succeeds_from_worktree

Filed: this is child batch 6 of T-2359 (the parent reformat epic-tracking
ticket, still open pending further batches).

Gates: frob format applied ruff-check-fix (all-clean, no lint fixes
needed this batch) + ruff-format-write per file; diff reviewed by
hand, format-only (whitespace/line-wrap/quote-style/string-literal
folding), no semantic changes.

### Changed
```
 tickets/T-2787/ticket.md | 73 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 73 insertions(+)
```

### Evidence
- `tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::test_must_now_fire_reports_the_undeclared_key` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_commented_out_rule_literal_is_skipped` (pytest node id, verified passing when recorded)
- `tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_testing_known_keys_reads_test_policy_model_fields` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive009Violations::test_known_gate_rule_ids_includes_waive009` (pytest node id, verified passing when recorded)
- `tests/unit/test_wire001_callback_keyword_argument.py::TestWire001CallbackKeywordArgument::test_function_passed_as_keyword_argument_value_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestUnboundAcceptance::test_empty_acceptance_list_is_never_unbound` (pytest node id, verified passing when recorded)
- `tests/unit/test_draft_finalize_attachments.py::TestFinalizeDraftRelocatesAttachmentRecords::test_attachment_path_follows_the_rename` (pytest node id, verified passing when recorded)
- `tests/test_tick013_gate.py::TestTick013EmptyScope::test_in_progress_empty_scope_fires` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_attribution.py::TestAttributeBatch::test_caller_break_attributes_to_the_caller_commit` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_drain.py::TestRunDrainAsync::test_declines_while_a_land_is_in_progress` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_watermark.py::TestCommitsSinceWatermark::test_counts_raw_git_commits_not_queue_entries` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRefusesTerminalState::test_refuses_done_ticket` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestSetKind::test_updates_kind_field` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: 25 error(s), 1379 warning(s), 712 waived
- error-findings: AFFECT001@src/frob/gates/_profile_schema.py, AFFECT001@src/frob/gates/_rule_id_scan.py, AFFECT001@src/frob/gates/_testing_schema.py, AFFECT001@src/frob/gates/_waive.py, AFFECT001@src/frob/verify/_drain.py, AFFECT001@src/frob/verify/_watermark.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2202-mega-cluster.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
