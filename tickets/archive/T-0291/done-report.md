## Done report

Changed (every function extracted; each new helper carries a one-line
docstring, no behavior change):

src/frob/app/app.py::_dispatch_table (extracted `_SUBCOMMAND_RUNNER_NAMES` module dict)
src/frob/app/deploy_runner.py::_run_generate (extracted `_mismatched_generated_files`, `_run_generate_check`, `_write_generated_files`)
src/frob/app/deploy_runner.py::_run_audit (extracted `_require_audit_flags`, `_build_vm_audit_config`, `_report_audit_result`)
src/frob/app/check_runner.py::_deploy_drift_result (extracted `_deploy_drift_tool_result`)
src/frob/app/check_runner.py::_deploy_conformance_result (extracted `_deploy_conformance_tool_result`)
src/frob/app/check_runner.py::run (extracted `_handle_stamp_modes`, `_stdout_log_ctx`, `_run_all_stages`, `_run_auto_detected_stages`, `_run_pinned_stage`, `_append_deploy_stages`)
src/frob/app/ticket_runner.py::_land (extracted `_require_land_args`, `_report_land_result`)
src/frob/app/ticket_runner.py::_apply_evidence (extracted `_log_evidence_result`)
src/frob/app/sys_runner.py::_run_export (extracted `_require_export_format`, `_require_export_design_path`)
src/frob/app/sys_runner.py::_print_audit_report (extracted `_log_waived_gaps`, `_log_proved_summary`, `_log_gaps`)
src/frob/app/sys_runner.py::_print_selfconform_report (extracted `_log_waived_selfconform`, `_log_selfconform_proved`, `_log_selfconform_violations`)
src/frob/app/sys_runner.py::_run_audit (extracted `_load_audit_model`, `_evaluate_audit`)
src/frob/gates/__init__.py::_waive002_violations (extracted `_waive002_violation_for`)
src/frob/gates/__init__.py::_match_waiver (moved historical rationale from docstring to a leading comment; logic unchanged)
src/frob/gates/__init__.py::_cov002 (extracted `_cov002_check_symref`)
src/frob/gates/__init__.py::_cov003 (extracted `_cov003_evidence_violation`)
src/frob/gates/__init__.py::_todo001_bare (extracted `_todo001_bare_comment`)
src/frob/gates/__init__.py::scope_gate (extracted `_scope_gate_check_file`)
src/frob/gates/__init__.py::_test001_002_one (extracted `_test001_no_unit_test`, `_test002_below_min`)
src/frob/gates/__init__.py::_test003 (extracted `_test003_check_package`)
src/frob/gates/__init__.py::_test007_pairs (extracted `_test007_check_pair`)
src/frob/gates/__init__.py::_test005_symbols (extracted `_test005_symbol_violation`)
src/frob/gates/__init__.py::_test005_systems (extracted `_test005_system_violation`)
src/frob/gates/__init__.py::_test008_unjoined_root (moved rationale to leading comment)
src/frob/gates/__init__.py::_test005 (extracted `_exclude_filtered_coverage`)
src/frob/gates/__init__.py::_sys001 (extracted `_sys001_check_edge`)
src/frob/gates/__init__.py::_claims_markers (extracted `_claims_markers_in_file`)
src/frob/gates/__init__.py::_doc003 (moved rationale to leading comment)
src/frob/gates/__init__.py::sys_gate (extracted `_log_sys_gate_summary`; moved rationale to leading comment)
src/frob/gates/__init__.py::dup_gate (extracted `_dup_gate_violations`)
src/frob/gates/__init__.py::release_gate (extracted `_rel001_missing_changelog`)
src/frob/gates/__init__.py::fuzz_gate (extracted `_fuzz_gate_violations`)
src/frob/gates/__init__.py::doclink_gate (extracted `_doc001_orphan`)
src/frob/gates/__init__.py::docanchor_gate (extracted `_docanchor_check_edge`)
src/frob/gates/__init__.py::perf_gate (extracted `_perf_gate_candidate_paths`, `_perf_gate_parse_files`)
src/frob/gates/__init__.py::_load_inputs (extracted `_load_required_state`, `_load_graph_queue_lock`, `_require`, `_assemble_gate_inputs`)
src/frob/gates/__init__.py::_build_jobs (extracted `_build_ticket_scoped_jobs`)
src/frob/gates/__init__.py::run_gates (extracted `_assemble_gate_report`)

Residual: none -- both files report 0 long-function warnings after this
pass (`frob-arch`'s remaining `large-file`/`abstraction-opportunity`
findings on these files are separate categories, out of this ticket's
declared scope: only long-function/god-class was targeted, no god-class
findings existed in this slice to begin with).

Evidence: `uv run pytest tests/test_gates.py tests/unit/test_check.py
tests/system/test_cli_check.py tests/system tests/test_tickets_collision.py
tests/test_tickets_cmd_evidence.py tests/test_tickets_evidence_cli.py
tests/test_ticket_land.py tests/test_tickets.py tests/unit/test_ticket_store.py
tests/unit/deploy tests/unit/strata/test_deploy.py` -> all green (full
system suite plus every touched-module unit suite). 4 pytest node ids
recorded via `frob ticket evidence` (see `evidence:` above).

Gates: `uv run frob arch .` filtered to
`src/frob/gates/__init__.py`/`src/frob/app/**`: BEFORE 36 long-function
warnings (26 in gates/__init__.py, 10 across app/**); AFTER 0 in both.
`uv run frob check` (full, post-merge-to-d900bd5): `ruff-check`/`ruff-
format`/`ty`/`gates` all 0 errors on the touched slice; the run's overall
exit 1 is a single pre-existing E501 in `src/frob/strata/_audit.py`
(confirmed via `git diff main -- src/frob/strata/_audit.py` empty --
untouched by this ticket, landed via the main merge, out of scope).
`git diff main --diff-filter=D --stat` empty after resolving the
ledger-conflict splice against the newer main tip (d900bd5). Cargo.lock:
no churn (`make core` no-op rebuild). No non-ASCII characters. Not closing
this ticket -- leaving for the reviewer per the review-gated workflow.
