---
id: T-1787
title: 'Wire T-1724''s dispatch telemetry: hooks call record_dispatch_event, CLI renders
  dispatch_cost_report'
state: done
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
- .claude/settings.json
- tests/test_stats_agentic.py
- docs/guides/agentic-time-profiling.md
- docs/modules/stats.md
- src/frob/app/telemetry.py
- src/frob/stats/_agentic.py
- tests/test_telemetry.py
- tests/test_hook_dispatch_telemetry.py
- design/frob.strata
- tickets/T-1787/**
- tickets/T-1836/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: .claude/settings.json
  reason: hook registration is required to actually wire the SessionStart/Stop dispatch
    hooks; the script alone under .claude/hooks/** is inert without this
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/app.md
  reason: 'closure: doc/test edges reachable from stats_runner.py touch + new hook
    tests'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_app_daemon_proxy.py
  reason: 'closure: doc/test edges reachable from stats_runner.py touch + new hook
    tests'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_app_style.py
  reason: 'closure: doc/test edges reachable from stats_runner.py touch + new hook
    tests'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_stats_agentic.py
  reason: 'closure: doc/test edges reachable from stats_runner.py touch + new hook
    tests'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/guides/agentic-time-profiling.md
  reason: 'closure: doc/test edges reachable from stats_runner.py touch + new hook
    tests'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/stats.md
  reason: 'closure: doc/test edges reachable from stats_runner.py touch + new hook
    tests'
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: tests/test_app_daemon_proxy.py
  reason: closure warnings there are pre-existing edges unrelated to this ticket's
    actual changes; not touching those files
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: tests/unit/test_app_style.py
  reason: closure warnings there are pre-existing edges unrelated to this ticket's
    actual changes; not touching those files
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/telemetry.py
  reason: must remove now-stale WIRE001 waivers claiming no caller exists, once this
    ticket adds one
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/stats/_agentic.py
  reason: must remove now-stale WIRE001 waivers claiming no caller exists, once this
    ticket adds one
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_telemetry.py
  reason: must remove now-stale WIRE001 waivers claiming no caller exists, once this
    ticket adds one
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_hook_dispatch_telemetry.py
  reason: new test file for the hook script
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: docs/modules/app.md
  reason: not actually needed; only pulled in by an unrelated closure suggestion,
    mega-glob explosion
  actor: logan
  at: '2026-08-08'
- op: add
  glob: design/frob.strata
  reason: declare testsuite capabilities (exec, fs.read) for the new hook test file,
    SELFAUDIT001
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1787/**
  reason: 'SCOPE001: this repo''s per-ticket ticket.md (tickets/T-1787/ticket.md)
    is not covered by the stale LEDGER_PATH=tickets.md always-in-scope constant; scoping
    this ticket''s own dir directly'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1836/**
  reason: 'SCOPE001: the draft ticket filed from this ticket''s own work (documenting
    the LEDGER_PATH gap) writes to its own dir'
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_hook_dispatch_telemetry.py::test_session_start_records_dispatch_start_event
- tests/test_hook_dispatch_telemetry.py::test_session_start_resume_is_not_cold_start
- tests/test_hook_dispatch_telemetry.py::test_session_start_unrecognized_source_omits_cold_start
- tests/test_hook_dispatch_telemetry.py::test_stop_records_dispatch_end_event
- tests/test_hook_dispatch_telemetry.py::test_stop_skips_reentrant_stop_hook_active
- tests/test_hook_dispatch_telemetry.py::test_start_and_end_share_dispatch_id_across_the_session
- tests/test_hook_dispatch_telemetry.py::test_unrecognized_hook_event_name_is_a_silent_noop
- tests/test_hook_dispatch_telemetry.py::test_never_blocks_on_malformed_stdin
- tests/test_hook_dispatch_telemetry.py::test_no_git_repo_is_a_silent_noop
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