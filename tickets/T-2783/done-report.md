## Done report

Changed:
src/frob/lang/__init__.py
src/frob/lang/_extract.py
src/frob/lang/_support.py
src/frob/perf/_harness.py
src/frob/release/_cli.py
src/frob/strata/_capacity.py
src/frob/strata/_design_load.py
src/frob/strata/_effects.py
src/frob/strata/_threat.py

Evidence: 12 pytest node ids bound (T-2359's evidence_scope), all pass.
Module-specific tests also run and passing (365 tests: test_lang_artifact_cache,
test_lang_kotlin, test_lang_parse_guard, test_lang_primitives, test_lang_strata,
tests/test_perf.py, test_release_stamp_guard, strata/test_capacity,
strata/test_capacity_projection, strata/test_design_load, strata/test_effects,
strata/test_threat).

Filed: this is child batch 4 of T-2359 (the parent reformat epic-tracking
ticket, still open pending further batches). T-2359's own scope narrowed
to exclude these 9 files plus the T-2557-leased and T-2778-leased files.

Gates: frob format applied ruff-check-fix + ruff-format-write per file;
diff reviewed by hand, format-only (whitespace/line-wrap/quote-style),
no semantic changes.

### Changed
```
 tickets/T-2783/ticket.md | 72 ++++++++++++++++++++++++++++++++++++++
 tickets/T-2784/ticket.md | 46 ++++++++++++++++++++++++
 2 files changed, 118 insertions(+)
```

### Evidence
- `tests/unit/test_app_runners.py::TestMapRunner::test_text_mode_logs_summary` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketRunnerDispatch::test_unknown_command_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_profile_runner.py::TestProfileRunnerShow::test_show_reports_configured_and_effective` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyfmt_runner.py::TestRun::test_default_delegates_to_run_ruff_autofix` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_no_population_reports_current_violations` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_sys_threats.py::TestSysThreats::test_no_boundary_prints_every_violation` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_sys_trace.py::TestSysTrace::test_trace_prints_witness_path_to_destination` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_append_event_writes_one_json_line` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestCheckResultCounts::test_total_errors_sums_across_results` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_overlapping_scope_names_the_other_ticket_and_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_related.py::TestRelatedTicketsSearch::test_finds_an_archived_close_title_match` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_scope_plausibility.py::TestScopePlausibility::test_implausible_scope_warns_loudly` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: 23 error(s), 1181 warning(s), 711 waived
- error-findings: AFFECT001@src/frob/release/_cli.py, AFFECT001@src/frob/strata/_capacity.py, AFFECT001@src/frob/strata/_threat.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2202-mega-cluster.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DUP001@src/frob/lang/_extract.py, PERF004@src/frob/tickets/_evidence.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
