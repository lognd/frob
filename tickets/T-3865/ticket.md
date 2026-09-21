---
id: T-3865
title: 'waiver-hygiene family (WAIVE004/010) burn-down: 265 unwaived findings'
state: queued
kind: bug
origin: agent
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: v0.541.0
runs_last: false
milestone: v0.541.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/diagnosis-nudge.py
- .claude/hooks/frob-directive-guard.py
- scripts/artifact_smoke.py
- scripts/branch_stranded_work_analysis.py
- scripts/check_summary.py
- scripts/measure_evidence_reach.py
- scripts/verify_release_ci_status.py
- scripts/wait_for_land_slot.py
- src/frob/_cli_parsers/_core.py
- src/frob/_cli_parsers/_design.py
- src/frob/_cli_parsers/_explore.py
- src/frob/_cli_parsers/_quality.py
- src/frob/_cli_parsers/_reporting.py
- src/frob/app/_check_chunking_baseline.py
- src/frob/app/_daemon_proxy.py
- src/frob/app/_json_guard.py
- src/frob/app/agent_runner.py
- src/frob/app/pyfmt_runner.py
- src/frob/app/telemetry/_state.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/arch/_abstraction.py
- src/frob/check/_python.py
- src/frob/cycle/graph.py
- src/frob/deploy/_conform.py
- src/frob/doctor.py
- src/frob/dup/_pipeline/_probe.py
- src/frob/dup/_pipeline/_smt.py
- src/frob/findings.py
- src/frob/gates/_coverage_sites.py
- src/frob/gates/_dead_symbols.py
- src/frob/gates/_debt_deprecated.py
- src/frob/gates/_doclink_docanchor.py
- src/frob/gates/_docstatus.py
- src/frob/gates/_fix_engine_sync.py
- src/frob/gates/_fix_engine_text.py
- src/frob/gates/_fix_engine_tier_b.py
- src/frob/gates/_fmt_directives.py
- src/frob/gates/_land_parity.py
- src/frob/gates/_pii_structural/_keywords.py
- src/frob/gates/_pkg_resources.py
- src/frob/gates/_refs.py
- src/frob/gates/_rule_id_scan.py
- src/frob/gates/_waive.py
- src/frob/gates/_wire.py
- src/frob/graph/dsl.py
- src/frob/graph/lock.py
- src/frob/lang/__init__.py
- src/frob/mutate/__init__.py
- src/frob/outline/__init__.py
- src/frob/process/parsers/ruff.py
- src/frob/process/parsers/valgrind.py
- src/frob/serve/_events.py
- src/frob/strata/_claims.py
- src/frob/strata/_facts.py
- src/frob/strata/_host_isolation_shared.py
- src/frob/strata/_mode_conformance.py
- src/frob/tickets/_done_report.py
- src/frob/tickets/_land_git_ops.py
- tests/conftest.py
- tests/gates/test_scan_timeout_enforcement.py
- tests/test_app_daemon_proxy.py
- tests/test_ci_workflow_job_summary.py
- tests/test_lang.py
- tests/test_ticket_leases.py
- tests/test_tickets_gate_claim_evidence.py
- tests/test_worktree_guard.py
- tests/test_worktree_pythonpath.py
- tests/unit/gates/test_pkg_resources.py
- tests/unit/rapid_sweep_suite/test_sweep_run.py
- tests/unit/rapid_sweep_suite/test_window.py
- tests/unit/test_close_promote_drafts.py
- tests/unit/test_conftest_suite_result_status.py
- tests/unit/test_daemon_proxy_error_paths_t1457.py
- tests/unit/test_dotnet_runner.py
- tests/unit/test_dup_legacy_cpp.py
- tests/unit/test_lifecycle_work_base.py
- tests/unit/test_pyfmt_runner.py
- tests/unit/test_verify_language_buckets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .claude/hooks/diagnosis-nudge.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: .claude/hooks/frob-directive-guard.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: scripts/artifact_smoke.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: scripts/branch_stranded_work_analysis.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: scripts/check_summary.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: scripts/measure_evidence_reach.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: scripts/verify_release_ci_status.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: scripts/wait_for_land_slot.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/_cli_parsers/_core.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/_cli_parsers/_design.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/_cli_parsers/_explore.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/_cli_parsers/_quality.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/_cli_parsers/_reporting.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/app/_check_chunking_baseline.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/app/_daemon_proxy.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/app/_json_guard.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/app/agent_runner.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/app/pyfmt_runner.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/app/telemetry/_state.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/arch/_abstraction.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/check/_python.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/cycle/graph.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/deploy/_conform.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/doctor.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/dup/_pipeline/_probe.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/dup/_pipeline/_smt.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/findings.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_coverage_sites.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_dead_symbols.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_debt_deprecated.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_doclink_docanchor.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_docstatus.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_fix_engine_sync.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_fix_engine_text.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_fix_engine_tier_b.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_fmt_directives.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_land_parity.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_pii_structural/_keywords.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_pkg_resources.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_refs.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_rule_id_scan.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_waive.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_wire.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/graph/dsl.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/graph/lock.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/lang/__init__.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/mutate/__init__.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/outline/__init__.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/process/parsers/ruff.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/process/parsers/valgrind.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/serve/_events.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/strata/_claims.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/strata/_facts.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/strata/_host_isolation_shared.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/strata/_mode_conformance.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/tickets/_done_report.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/conftest.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/gates/test_scan_timeout_enforcement.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/test_app_daemon_proxy.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/test_ci_workflow_job_summary.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/test_lang.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/test_ticket_leases.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/test_tickets_gate_claim_evidence.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/test_worktree_guard.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/test_worktree_pythonpath.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/gates/test_pkg_resources.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/rapid_sweep_suite/test_sweep_run.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/rapid_sweep_suite/test_window.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/test_close_promote_drafts.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/test_conftest_suite_result_status.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/test_daemon_proxy_error_paths_t1457.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/test_dotnet_runner.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/test_dup_legacy_cpp.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/test_lifecycle_work_base.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/test_pyfmt_runner.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/test_verify_language_buckets.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: .claude/hooks/diagnosis-nudge.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: .claude/hooks/frob-directive-guard.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: scripts/artifact_smoke.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: scripts/branch_stranded_work_analysis.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: scripts/check_summary.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: scripts/measure_evidence_reach.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: scripts/verify_release_ci_status.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: scripts/wait_for_land_slot.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/_cli_parsers/_core.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/_cli_parsers/_design.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/_cli_parsers/_explore.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/_cli_parsers/_quality.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/_cli_parsers/_reporting.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/app/_check_chunking_baseline.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/app/_daemon_proxy.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/app/_json_guard.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/app/agent_runner.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/app/pyfmt_runner.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/app/telemetry/_state.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/arch/_abstraction.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/check/_python.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/cycle/graph.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/deploy/_conform.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/doctor.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/dup/_pipeline/_probe.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/dup/_pipeline/_smt.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/findings.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_coverage_sites.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_dead_symbols.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_debt_deprecated.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_doclink_docanchor.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_docstatus.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_fix_engine_sync.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_fix_engine_text.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_fix_engine_tier_b.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_fmt_directives.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_land_parity.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_pii_structural/_keywords.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_pkg_resources.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_refs.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_rule_id_scan.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_waive.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_wire.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/graph/dsl.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/graph/lock.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/lang/__init__.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/mutate/__init__.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/outline/__init__.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/process/parsers/ruff.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/process/parsers/valgrind.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/serve/_events.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/strata/_claims.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/strata/_facts.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/strata/_host_isolation_shared.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/strata/_mode_conformance.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/tickets/_done_report.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/conftest.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/gates/test_scan_timeout_enforcement.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/test_app_daemon_proxy.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/test_ci_workflow_job_summary.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/test_lang.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/test_ticket_leases.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/test_tickets_gate_claim_evidence.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/test_worktree_guard.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/test_worktree_pythonpath.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/gates/test_pkg_resources.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/rapid_sweep_suite/test_sweep_run.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/rapid_sweep_suite/test_window.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/test_close_promote_drafts.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/test_conftest_suite_result_status.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/test_daemon_proxy_error_paths_t1457.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/test_dotnet_runner.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/test_dup_legacy_cpp.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/test_lifecycle_work_base.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/test_pyfmt_runner.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
- op: add
  glob: tests/unit/test_verify_language_buckets.py
  reason: WAIVE004/WAIVE010 waiver-hygiene fixes touched these 79 files this pass
    (T-3865); comment-only frob:waive deletions/rewords, no behavior change
  actor: logan
  at: '2026-09-20'
evidence:
- tests/test_waive_gate.py::TestWaive010Violations::test_plain_permanent_reason_does_not_warn
- tests/unit/gates/test_pkg_resources.py::TestPkg001DeclaredLongDescription::test_relative_markdown_image_in_declared_readme_fires_error
- tests/test_tickets_gate_claim_evidence.py::TestCriterionGateClaimDetection::test_t1276_shaped_criterion_matches
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_never_sweeps_a_draft_it_did_not_claim
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3844 burn-down: this rule/cluster (WAIVE004,WAIVE010) carried 265 unwaived warning-level findings on the 2026-09-05 full unscoped 'frob check --no-cache' baseline measured for T-3844 (see that ticket's body for the full histogram). It is intentionally NOT promoted to error by T-3844 -- promoting a rule that still fires reds the build for everyone. This ticket's job: drive the live unwaived finding count for WAIVE004,WAIVE010 to zero (real fixes and/or reasoned frob:waive entries), then promote WAIVE004,WAIVE010 from warn to error in frob.toml's [gates.severity] T-1002 managed zone as a follow-up to this same campaign.