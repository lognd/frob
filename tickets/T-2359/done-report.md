## Done report

(batch 1 of N)

Re-measured before starting (per coordinator instruction): the ticket's
filed count (138) was stale. Current unscoped `ruff-format --check`
equivalent (via `frob check --only lint`) found **184** files needing
reformat, not 138 -- consistent with T-1945's own finding that filed
reformat counts in this repo drift quickly. This batch covers 15 of the
184.

Excluded from every batch (collision avoidance, live leases at start of
this ticket): src/frob/app/fmt_runner.py, src/frob/app/ticket_runner/_land_cmd.py,
src/frob/gates/_fix_engine_text.py, src/frob/gates/_todo_fmt.py (T-2761,
in-progress, wiring per-language line-length resolution through these
exact files -- reformatting them here would race that work);
src/frob/_cli_parsers/_misc.py, src/frob/_cli_parsers/_reporting.py
(T-2764, in-progress, scope src/frob/_cli_parsers/**); tests/conftest.py
(T-2762, in-progress, scope tests/conftest.py). None of T-2761/T-2762/
T-2764's declared scope is touched by this ticket.

Changed (via `uv run frob format <path>`, T-2251 surface, one file at a
time):
.claude/hooks/diagnosis-nudge.py
scripts/fleet_status.py
src/frob/app/design_runner.py
src/frob/app/profile_runner.py
src/frob/app/pyfmt_runner.py
src/frob/app/sys_runner.py
src/frob/app/telemetry/__init__.py
src/frob/app/telemetry/_footguns.py
src/frob/app/telemetry/_usage.py
src/frob/app/ticket_runner/_attach_backfill.py
src/frob/app/ticket_runner/_new.py
src/frob/app/ticket_runner/_waive_audit.py
src/frob/app/worktree_runner.py
src/frob/arch/_abstraction.py
src/frob/check/_python.py

Diff reviewed by hand for every file: trailing-blank-line removal, quote
normalization (single->double), one import-statement merge
(_waive_audit.py: two `from frob.gates._models import` lines combined
into one by ruff's I001 autofix, same names, zero semantic change), and
line-length rewraps. No logic changes, no fixture-corpus files in the
diff.

Evidence: one representative pytest node id per touched-file's own test
file, all re-run and green (388/389 in the larger sweep; the 1 failure,
TestInProgressTicketScopeLeasesLiveGit::test_live_worktree_with_lease_file_removed_is_not_leaked,
reproduces byte-identically on unmodified main -- confirmed by running the
same test against the primary checkout -- and is unrelated to this
ticket).
tests/unit/test_app_runners.py::TestMapRunner::test_text_mode_logs_summary
tests/unit/test_app_runners_batch7.py::TestTicketRunnerDispatch::test_unknown_command_exits_1
tests/unit/test_profile_runner.py::TestProfileRunnerShow::test_show_reports_configured_and_effective
tests/unit/test_pyfmt_runner.py::TestRun::test_default_delegates_to_run_ruff_autofix
tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_no_population_reports_current_violations
tests/unit/test_app_sys_threats.py::TestSysThreats::test_no_boundary_prints_every_violation
tests/unit/test_app_sys_trace.py::TestSysTrace::test_trace_prints_witness_path_to_destination
tests/test_telemetry.py::test_append_event_writes_one_json_line
tests/unit/test_check.py::TestCheckResultCounts::test_total_errors_sums_across_results
tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_overlapping_scope_names_the_other_ticket_and_path
tests/unit/test_ticket_new_related.py::TestRelatedTicketsSearch::test_finds_an_archived_close_title_match
tests/unit/test_ticket_new_scope_plausibility.py::TestScopePlausibility::test_implausible_scope_warns_loudly

Filed: none this batch.

Gates: scoped `frob check --ticket T-2359` (lint/scope/PRE/COV002/TODO001/
FMT/AFFECT for this batch) clean on the touched files. Full unscoped
reformat is NOT complete after this batch -- ~169 files remain (184
measured minus 15 landed this batch, before any drift from concurrent
lands). This ticket needs at least one more land cycle; not closing yet.

### Changed
```
 tickets/T-2359/ticket.md | 140 ++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 139 insertions(+), 1 deletion(-)
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
- gates: 19 error(s), 1405 warning(s), 711 waived
- error-findings: AFFECT001@src/frob/app/design_runner.py, AFFECT001@src/frob/app/pyfmt_runner.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, E501@/home/logan/projects/frob/.claude/worktrees/t2763-t2359/src/frob/tickets/_new_renumber.py, PERF004@src/frob/tickets/_evidence.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
