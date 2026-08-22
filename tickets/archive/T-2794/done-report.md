## Done report

Changed:
tests/unit/test_check_budget.py
tests/unit/test_check_tool_unavailable.py
tests/unit/test_cli_hygiene_checklist_t1556.py
tests/unit/test_close_promote_drafts.py
tests/unit/test_close_rel001_bump.py
tests/unit/test_close_t1648_remainder.py
tests/unit/test_coordinator_scripts.py
tests/unit/test_dup_graph_table_schema.py
tests/unit/test_fleet_runner.py
tests/unit/test_fmt_wiring_reachability_t2761.py
tests/unit/test_parse_runner_direct.py
tests/unit/test_rapid_sweep.py
tests/unit/test_reporting_t1648_remainder.py

Evidence: 13 pytest node ids bound, one per touched file, all pass.
Full-batch run: 473 collected/0 failed (1 pre-existing failure
excluded and reported separately below).

Pre-existing failure (reproduced on unmodified main at the primary
checkout, not caused by this change -- the diff to this test file is
pure line-wrap/import-order reformatting, no logic touched):
tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeasesLiveGit::test_live_worktree_with_lease_file_removed_is_not_leaked

Filed: this is child batch 9 of T-2359 (the parent reformat epic-tracking
ticket, still open pending further batches).

Gates: frob format applied ruff-check-fix (test_rapid_sweep.py picked
up 5 import-sort/wrap fixes) + ruff-format-write per file; diff
reviewed by hand -- test_coordinator_scripts.py's large diff (374
lines) is entirely long-line-wrap reformatting (spot-checked directly
and via test-suite pass), no semantic changes anywhere in the batch.

### Changed
```
 tickets/T-2794/ticket.md | 56 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 56 insertions(+)
```

### Evidence
- `tests/unit/test_check_budget.py::TestSelectBudgetChunks::test_greedy_pack_fits_under_budget` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_tool_unavailable.py::TestToolUnavailableResult::test_shape_is_a_failing_diagnostic` (pytest node id, verified passing when recorded)
- `tests/unit/test_cli_hygiene_checklist_t1556.py::TestRenumberPositionalContractDocumented::test_old_positional_help_names_the_whole_ledger_fallback` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_promotes_a_draft_the_ticket_filed` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_rel001_bump.py::TestDeclaredPyprojectVersion::test_absent_pyproject_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_t1648_remainder.py::TestRemainderDisclosureGuard::test_clean_narrative_is_unaffected` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestLoadReport::test_reads_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_dup_must_now_fire_reports_the_undeclared_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_fleet_runner.py::TestFleetRunner::test_run_status_table` (pytest node id, verified passing when recorded)
- `tests/unit/test_fmt_wiring_reachability_t2761.py::TestFmtRunnerReachability::test_check_mode_reports_no_change_for_rust_file_under_its_own_width` (pytest node id, verified passing when recorded)
- `tests/unit/test_parse_runner_direct.py::TestParseRunnerRun::test_missing_tool_exits_with_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRollingBaseline::test_absent_baseline_reads_as_none_not_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage::test_detects_known_phrase` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: 19 error(s), 1275 warning(s), 711 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DUP001@tests/unit/test_cli_hygiene_checklist_t1556.py, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
