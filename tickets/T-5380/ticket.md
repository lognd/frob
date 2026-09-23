---
id: T-5380
title: claude/agent/natives --help no longer cites T-4522/T-4546 flattening note
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
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_cli_single_child_groups.py
- src/frob/__main__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 35819358270 (all 3 platforms); re-verified failing on dev tip 39b89ed091: tests/unit/test_cli_single_child_groups.py::TestClaudeGroupFlattened::test_help_notes_alias, TestAgentGroupFlattened::test_help_notes_alias and TestNativesGroupFlattened::test_help_notes_alias all fail -- 'frob claude --help'/'frob agent --help'/'frob natives --help' no longer print the T-4522/T-4546 single-child-group-flattening note in their description/epilog (help text now just describes the implied subcommand). Likely one shared CLI-description-builder regression, not three independent breaks -- find the common code path before filing 3 separate fixes. Distinct from T-5092/T-5096/T-5205 (those are the '--path' option-parity drift on ops natives, not the help text).