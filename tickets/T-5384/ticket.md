---
id: T-5384
title: 'Windows CI: fake dotnet/Unity test-double binaries are POSIX shell scripts,
  unexecutable on Windows (6 test failures)'
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_dotnet_runner.py
- tests/unit/test_unity_batchmode.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 35819358270 windows job (107047697037) only; re-verified locally the root cause via code read on dev tip 39b89ed091 (cannot exec-test on this Linux host, but the mechanism is unambiguous). Common root cause for tests/unit/test_dotnet_runner.py::TestRunDotnetTests::{test_maps_passing_and_failing_ids,test_requested_id_missing_from_results_is_err} and tests/unit/test_unity_batchmode.py::TestRunUnityBatchmode::{test_maps_passing_and_failing_ids,test_requested_id_missing_from_results_is_err,test_crash_with_no_results_file_is_run_failed_distinct_from_a_test_failure}: both files' _write_fake_dotnet/_write_fake_unity (and their crashing variants) write a fake executable named 'dotnet'/the unity editor stub as a '#!/bin/sh ...' text file plus chmod +x, then rely on run_dotnet_tests/run_unity_batchmode spawning it off PATH. Windows process creation has no shebang interpreter and does not treat an extensionless file as executable (PATHEXT requires .exe/.bat/.cmd); the subprocess spawn therefore fails, surfacing as TestingError.DotnetRunFailed (observed in the windows log) instead of the test's expected outcome. Fix: give the fixture-writer a platform branch that emits a '.cmd' (Windows) alongside the POSIX script, or invoke through 'sh <script>' explicitly instead of relying on OS exec. NOT the full Windows-only failure set from this run (65 total) -- this ticket covers only the 6 dotnet/unity fake-binary failures where the shebang-script root cause is directly readable in the fixture code; the remaining ~29 windows-only failures (test_ticket_leases.py cluster, test_hook_frob_suggest.py, test_cli_evidence_enforcement.py, test_cli_ticket.py, test_land_cas_ledger_retry.py, test_leases_staleness_perf.py, test_token_usage.py, test_docarch_structural.py, test_config_path_defaults.py, test_bulk.py, test_ticket_verbs_wait.py collection error) do NOT share this pattern and need a separate Windows-focused triage pass.