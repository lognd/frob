---
id: T-2912
title: Instrument agent tool-call histograms to target token cost at measured hotspots
state: done
kind: feature
origin: human
created: '2026-08-25'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/tool-call-telemetry.py
- .claude/settings.json
- src/frob/stats/_agentic.py
- src/frob/app/stats_runner.py
- docs/guides/agentic-time-profiling.md
- tests/test_stats_agentic.py
- docs/modules/stats.md
- src/frob/stats/__init__.py
- tests/test_hook_dispatch_telemetry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .claude/hooks/tool-call-telemetry.py
  reason: 'T-2912: instrument per-tool-call telemetry hook and histogram reporting'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: .claude/settings.json
  reason: 'T-2912: instrument per-tool-call telemetry hook and histogram reporting'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/stats/_agentic.py
  reason: 'T-2912: instrument per-tool-call telemetry hook and histogram reporting'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/app/stats_runner.py
  reason: 'T-2912: instrument per-tool-call telemetry hook and histogram reporting'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/guides/agentic-time-profiling.md
  reason: 'T-2912: instrument per-tool-call telemetry hook and histogram reporting'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_hook_tool_call_telemetry.py
  reason: 'T-2912: instrument per-tool-call telemetry hook and histogram reporting'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_stats_agentic.py
  reason: 'T-2912: instrument per-tool-call telemetry hook and histogram reporting'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/stats.md
  reason: 'T-2912: doc anchors for new histogram fields'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/app.md
  reason: 'T-2912: doc anchors for new histogram fields'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/stats/__init__.py
  reason: 'T-2912: re-export new ToolCallShape model'
  actor: logan
  at: '2026-08-26'
- op: remove
  glob: docs/modules/app.md
  reason: 'T-2912: unused, no edit needed to app.md'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_hook_dispatch_telemetry.py
  reason: 'T-2912: fold tool-call-telemetry hook tests into an already exec-allowlisted
    test file (design/frob.strata is locked by T-2911)'
  actor: logan
  at: '2026-08-26'
- op: remove
  glob: tests/test_hook_tool_call_telemetry.py
  reason: 'T-2912: folded exec-capability tests into already-allowlisted tests/test_hook_dispatch_telemetry.py
    instead'
  actor: logan
  at: '2026-08-26'
evidence:
- tests/test_hook_dispatch_telemetry.py::test_pre_tool_use_records_attempt_event
- tests/test_hook_dispatch_telemetry.py::test_post_tool_use_records_completion_with_token_estimate
- tests/test_hook_dispatch_telemetry.py::test_non_bash_tool_never_gets_a_command_shape
- tests/test_hook_dispatch_telemetry.py::test_bash_command_shape_never_leaks_raw_argument_values
- tests/test_hook_dispatch_telemetry.py::test_bash_command_shape_extends_through_bare_subcommand_words
- tests/test_hook_dispatch_telemetry.py::test_bash_command_shape_chain_stops_at_a_ticket_id
- tests/test_hook_dispatch_telemetry.py::test_tool_call_telemetry_disabled_env_var_writes_nothing
- tests/test_hook_dispatch_telemetry.py::test_tool_call_telemetry_malformed_payload_is_a_silent_noop
- tests/test_hook_dispatch_telemetry.py::test_tool_call_telemetry_unrecognized_hook_event_is_a_silent_noop
- tests/test_hook_dispatch_telemetry.py::test_tool_call_telemetry_outside_git_repo_writes_nothing
- tests/test_stats_agentic.py::test_tool_call_histogram_counts_completed_calls_by_shape
- tests/test_stats_agentic.py::test_tool_call_histogram_counts_unmatched_pre_as_blocked
- tests/test_stats_agentic.py::test_tool_call_histogram_legacy_phaseless_events_count_as_completed
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 3543eab4e7975d7f15cc1e325225e7c11c6ffc46
---
