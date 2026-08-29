---
id: T-0148
title: drive frob check gates to zero violations
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/**
- tests/**
- docs/**
- frob.toml
- pyproject.toml
- tickets.md
- strata-core/src/**
- .gitignore
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_excludes.py::test_dup_scanner_honors_exclude
- tests/unit/test_bind.py::test_check_reports_mismatch_for_unbound_binding
- tests/test_stats.py::test_collect_combines_both
- tests/test_mutate.py::test_run_mutations_all_killed_by_strong_test
- tests/test_release.py::test_release_gate_flags_missing_bump
- tests/test_gitio.py::TestWorkingDiff::test_covers_committed_staged_unstaged_and_untracked
- tests/unit/test_logging_quiet.py::TestQuietStdoutLogsReentrance::test_interleaved_enter_exit_across_threads_never_sticks
- tests/system/test_scaffold_dx.py::test_python_toolchain_scaffold_passes_check_immediately[python-tool]
- tests/unit/strata/test_kernel_properties.py::test_worst_age_matches_longest_path_oracle_on_dags
- tests/test_gates.py::TestCoverageLoad::test_parses_line_to_symbol_span
- tests/test_gates.py::TestCoverageLoad::test_joins_via_repo_relative_source
- tests/test_gates.py::TestCoverageLoad::test_multi_source_picks_the_root_that_joins
- tests/test_gates.py::TestCoverageLoad::test_zero_join_is_loud_not_silent
- tests/test_gates.py::TestTestGate::test_test008_fires_on_unjoined_root
- tests/test_gates.py::TestTestGate::test_test008_cannot_be_waived
designated_repro_test: null
evidence_changes:
- old_node: tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately
  new_node: tests/system/test_scaffold_dx.py::test_python_toolchain_scaffold_passes_check_immediately[python-tool]
  reason: T-3277 parametrized this test for multi-scaffold-type coverage; same test
    content for python-tool, new node id
  actor: logan
  at: '2026-08-28'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The gates stage currently reports 87 violation(s), 55 waived on main. End state: the gates line reports 0 violation(s). Triage every reported item: (1) fix it properly, (2) add a narrowly-scoped frob:waive with a specific written reason where the rule genuinely misfires, or (3) file a specific follow-up ticket and mark the site frob:todo T-#### when the fix is real but out of scope. No blanket or file-level waivers; no rule disabling in frob.toml without a written rationale in the Done report. Document the per-rule-family outcome table (family, count, disposition) in the Done report. Run AFTER the current wave lands (T-0140/T-0141/T-0144/T-0145/T-0146 touch overlapping files).

Scope extended during the sweep (self-declared, not a pre-work amendment): `strata-core/src/**` -- the gates baseline includes PERF/TEST violations native to the Rust kernel crate (strata-core/src/lib.rs, parse.rs), which the ticket's original `src/**` glob does not match (that glob roots at the Python `src/` tree; `strata-core/src/` is a sibling top-level directory). `.gitignore` -- fixing TEST006 (regenerating the coverage stamp via `make coverage`) produces `.coverage`/`coverage.xml` build artifacts that were not previously gitignored, tripping SCOPE001; added both plus `htmlcov/` to `.gitignore` per this repo's standard Python ignore list rather than leaving them as stray untracked files.