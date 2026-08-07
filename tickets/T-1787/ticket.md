---
id: T-1787
title: 'Wire T-1724''s dispatch telemetry: hooks call record_dispatch_event, CLI renders
  dispatch_cost_report'
state: queued
kind: feature
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- .claude/hooks/**
- src/frob/app/stats_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1724 added `frob.app.telemetry.record_dispatch_event` (the recording
API for a dispatch's start/end boundary, with an explicit `cold_start`
field) and `frob.stats.dispatch_cost_report`/`DispatchCostReport` (the
join of that against `kind="tool"`/`kind="ticket"` telemetry events,
producing tokens-per-landed-ticket, cold-start floor, marginal
per-resume cost, and zero-delivery dispatch ids).

Neither has a caller yet. Two wiring gaps remain, deliberately left out
of T-1724's own scope (`src/frob/stats/_agentic.py`,
`src/frob/app/telemetry.py`, `tests/test_stats_agentic.py`,
`docs/modules/stats.md`):

1. Nothing calls `record_dispatch_event` at a real dispatch boundary.
   The natural call sites are Claude Code hooks
   (`.claude/hooks/**`) -- a `SessionStart`-shaped hook for
   `event="start"` (recording `worktree`, `branch`, and whether this is
   a cold start or a resume -- Claude Code's own session-start payload
   should say which, mirroring the investigation T-1734 already did for
   the Stop-event payload) and a `Stop`-shaped hook for `event="end"`.

2. Nothing calls `dispatch_cost_report` from the CLI.
   `src/frob/app/stats_runner.py`'s `_run_agentic`/`_agentic_*_lines`
   family renders `AgenticReport` today; it needs a matching
   `_dispatch_cost_lines` section (or an equivalent) so
   `frob stats --agentic`'s human-readable output surfaces
   tokens-per-landed-ticket, the cold-start floor, marginal run deltas,
   and zero-delivery dispatch ids -- today these are only reachable via
   `--json` (the `DispatchCostReport` pydantic model dumps automatically
   through the existing `model_dump_json()` path, but the text renderer
   was not touched since `stats_runner.py` is outside T-1724's declared
   scope).

Acceptance: a real Claude Code session start/stop appends
`kind="dispatch"` events to `.frob/telemetry.jsonl`, `frob stats
--agentic` (plain text, not just `--json`) shows the T-1724 report
sections, and at least one dispatch in this repo's own telemetry stream
resolves through the full pipeline end to end.
