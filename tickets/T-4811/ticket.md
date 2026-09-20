---
id: T-4811
title: Wire frob run/build --help into _build_parser's subcommand tree
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4546
parent: T-4757
tier: ticket
sprint: v1.1.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_root.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.537.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
- field: sprint
  old_value: v0.537.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4759 added frob.app.run_runner.run/run_build (frob run <name> [--dry-run], frob build [--dry-run]), dispatched directly from frob.__main__._dispatch (same non-uniform shape as bind/agent/worktree) so they already work end to end. Their --help-only parser builders (_add_run_parser/_add_build_parser in src/frob/_cli_parsers/_run.py, re-exported through the package __init__.py and frob.__main__) could not be registered into _add_analysis_subparsers/_add_workflow_subparsers in src/frob/_cli_parsers/_root.py because that file was leased by T-4546 at the time T-4759 landed. Once that lease clears: call _add_run_parser(sub) and _add_build_parser(sub) from the appropriate _root.py registration function (mirroring bind/agent/worktree's own --help-only registration) so 'run'/'build' show up in top-level frob --help.