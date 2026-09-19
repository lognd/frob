---
id: T-4421
title: Clean system, scripts, and remaining test docstrings of change-narrative (DOCARCH001)
state: queued
kind: docs
origin: human
created: '2026-09-11'
priority: medium
parent: T-2994
tier: story
sprint: v0.534.0
runs_last: false
milestone: 0.534.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/__init__.py
- tests/system/conftest.py
- tests/system/test_artifact_smoke.py
- tests/system/test_ci_hang_guard_positive_control.py
- tests/system/test_cli_arch.py
- tests/system/test_cli_check.py
- tests/system/test_cli_cycle.py
- tests/system/test_cli_doctor.py
- tests/system/test_cli_dup.py
- tests/system/test_cli_evidence_enforcement.py
- tests/system/test_cli_exports.py
- tests/system/test_cli_gitlog.py
- tests/system/test_cli_graph.py
- tests/system/test_cli_map.py
- tests/system/test_cli_native_missing.py
- tests/system/test_cli_outline.py
- tests/system/test_cli_parse.py
- tests/system/test_cli_perf.py
- tests/system/test_cli_render_golden.py
- tests/system/test_cli_scaffold_apply.py
- tests/system/test_cli_scale.py
- tests/system/test_cli_sys_audit.py
- tests/system/test_cli_sys_doc.py
- tests/system/test_cli_sys_export.py
- tests/system/test_cli_sys_plan.py
- tests/system/test_cli_test.py
- tests/system/test_cli_ticket.py
- tests/system/test_cli_ticket_land.py
- tests/system/test_cli_ticket_promote.py
- tests/system/test_cli_ticket_worktree_root.py
- tests/system/test_cli_vet.py
- tests/system/test_cli_xref.py
- tests/system/test_coverage_sigterm.py
- tests/system/test_faulthandler_ci_hygiene.py
- tests/system/test_fleet_status_ground_truth.py
- tests/system/test_fleet_status_ticket_readiness_arch001.py
- tests/system/test_frob_self_model.py
- tests/system/test_natives_build_integration.py
- tests/system/test_packaging_py_typed.py
- tests/system/test_public_api_from_wheel.py
- tests/system/test_run_helper_env_leak.py
- tests/system/test_scaffold_dx.py
- tests/system/test_scaffold_pool.py
- tests/system/test_scaffold_pool_cli.py
- tests/system/test_spawn_budget.py
- scripts/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/system/__init__.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/conftest.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_artifact_smoke.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_ci_hang_guard_positive_control.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_arch.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_check.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_cycle.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_doctor.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_dup.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_evidence_enforcement.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_exports.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_gitlog.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_graph.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_map.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_native_missing.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_outline.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_parse.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_perf.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_render_golden.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_scaffold_apply.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_scale.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_sys_audit.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_sys_doc.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_sys_export.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_sys_plan.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_test.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_ticket.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_ticket_land.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_ticket_promote.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_ticket_worktree_root.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_vet.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_cli_xref.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_coverage_sigterm.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_faulthandler_ci_hygiene.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_fleet_status_ground_truth.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_fleet_status_ticket_readiness_arch001.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_frob_self_model.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_natives_build_integration.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_packaging_py_typed.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_public_api_from_wheel.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_run_helper_env_leak.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_scaffold_dx.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_scaffold_pool.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_scaffold_pool_cli.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/system/test_spawn_budget.py
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: scripts/**
  reason: 'split: remaining corpora go to child tickets (measured denominator 500+
    repo-wide, ~15-20 for this subset); tests/system/test_system.py excluded (leased
    by T-4612 via tests/**/test_sys*.py glob overlap, no DOCARCH001 finding in it
    anyway)'
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: sprint
  old_value: v0.533.0
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-16'
- field: milestone
  old_value: 0.533.0
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-16'
designated_repro_test: null
acceptance:
- text: Given a full frob check on tests/system, scripts/, and the remaining test
    corpora, when DOCARCH001 is measured, then their combined finding count is 0
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DOCARCH001 measured tests/system 12 + scripts/fleet_status.py 7 + remaining tests ~100 = ~119 findings (owner's estimate ~130) on a full check today (2026-09-11), outside src/frob, tests/unit and the land+gates suites. Rewrite each flagged docstring to state WHAT the symbol/test does. Denominator: ~130 (system+scripts+rest).