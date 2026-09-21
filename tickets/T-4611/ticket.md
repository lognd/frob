---
id: T-4611
title: land's own refusal-avoidance quarantine-raised log line does not name the undisposed
  findings forcing synchronous verification
state: in-progress
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_land_cmd_quarantine.py
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_cmd_quarantine.py
  reason: 'T-4611: TestQuarantineUndisposedSummary already covers _quarantine_undisposed_summary
    in this file; the new (rule,file)-naming test belongs alongside it'
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: the undisposed-findings log line this ticket must enrich is emitted from
    _quarantine_undisposed_summary in this file
  actor: logan
  at: '2026-09-21'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.533.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-4611
branch: t-4611
---
T-4581 why-file finding: T-3233's land spent 27.3s (+3.4s to +30.7s) in fully-synchronous verification because 'ticket land: T-3233 quarantine is raised ... deferred landing is OFF ... 16 finding(s) undisposed' (T-1693) -- the log line names only a COUNT, never which (rule, file) pairs, so triaging requires a separate 'frob verify dispose'/quarantine-read round trip mid-land. This ticket's own T-4581 fix cuts the false-positive share of this cost (lease-file/doc noise), but a real quarantine raise still pays this 27s+ blind. Have the land refusal/degrade log line enumerate (or summarize) the undisposed (rule, file) identities inline, so the very first log line is enough to triage.