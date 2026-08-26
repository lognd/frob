---
id: T-2912
title: Instrument agent tool-call histograms to target token cost at measured hotspots
state: queued
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
- tests/test_hook_tool_call_telemetry.py
- tests/test_stats_agentic.py
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
