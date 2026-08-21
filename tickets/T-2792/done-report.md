## Done report

Changed:
tests/unit/test_process_lock.py
tests/unit/test_process_reap.py
tests/unit/test_require_python.py
tests/unit/test_research_assets.py
tests/unit/test_main_entry.py
tests/unit/test_makefile_coverage.py
tests/unit/test_native_table_schema.py
tests/unit/test_test_table_schema.py
tests/unit/test_gitattributes_crlf_normalization.py
tests/unit/test_confinement_lattice.py
tests/unit/test_cycle_runner_root_resolution.py
tests/unit/test_cycle_waiver.py
tests/unit/test_dup_core.py

Evidence: 13 pytest node ids bound, one per touched file, all pass.
Full-batch run: 163 collected, 0 failed.

Filed: this is child batch 8 of T-2359 (the parent reformat epic-tracking
ticket, still open pending further batches).

Gates: frob format applied ruff-check-fix (test_test_table_schema.py
picked up an import-wrap fix, no format change needed after) +
ruff-format-write per file; diff reviewed by hand, format-only
(whitespace/quote-style/import-wrap/paren-collapse), no semantic
changes.

### Changed
```
 tickets/T-2792/ticket.md | 56 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 56 insertions(+)
```

### Evidence
- `tests/unit/test_process_lock.py::TestDerivedStateLock::test_lock_file_created_under_frob_dir` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestReapActiveChildren::test_terminates_and_joins_active_children` (pytest node id, verified passing when recorded)
- `tests/unit/test_require_python.py::TestRequiredVersion::test_parses_a_real_requires_python_line` (pytest node id, verified passing when recorded)
- `tests/unit/test_research_assets.py::test_mcp_json_parses_and_declares_required_servers` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestMainSigint::test_keyboard_interrupt_prints_clean_message_and_exits_130` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestCoverageRecipeDelegatesToFrobCoverageFull::test_recipe_body_is_at_most_two_non_comment_lines` (pytest node id, verified passing when recorded)
- `tests/unit/test_native_table_schema.py::TestNativeSchemaGate::test_must_now_fire_reports_the_undeclared_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_test_table_schema.py::TestTestRunnerSchemaGate::test_must_now_fire_reports_the_undeclared_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_gitattributes_crlf_normalization.py::TestGitattributesEolNormalization::test_sampled_source_files_are_pinned_to_lf` (pytest node id, verified passing when recorded)
- `tests/unit/test_confinement_lattice.py::TestConfinementLatticePositiveControl::test_absolute_literal_write_is_escaped` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle_waiver.py::TestCycleWaiverPipeline::test_unwaived_cycle_reports` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_core.py::test_core_available_returns_bool` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution::test_all_path_shapes_agree_on_a_real_cycle[src/pkg]` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: 19 error(s), 956 warning(s), 711 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2792, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
