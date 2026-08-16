---
id: T-2198
title: land --plan requires a globally-clean TICK gate, so 9 unrelated rotting-epic
  alarms block every ledger-only land repo-wide -- and decomposing those epics is
  itself ledger-only work
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'Measured: _land_plan_check_ticks_fn (src/frob/app/ticket_runner/_land_cmd.py:2770)
    spawns ''frob check --only tickets'' and returns int(match.group(1)) == 0, so
    --plan proceeds ONLY when the TICK gate reports zero errors globally. The repo
    currently has 9 TICK004 rotting-ticket errors (T-0969, T-1135, T-1136, T-1137,
    T-1219, T-1238, T-1273, T-1382, T-1623 -- all tier=epic, 15-20 days old). An agent''s
    purely-ledger worktree (128 insertions, tickets/T-2197/ only, zero source files)
    was refused with PlanTickGateDirty. This test MUST fail against current main.'
  evidence: []
- text: 'The circularity is the point: --plan is the sanctioned path for design-phase
    and ledger-only work, decomposing a rotting EPIC into leaves IS ledger-only work,
    and TICK004 fires precisely on those undecomposed epics. So the alarm blocks the
    only action that would clear it. Gate --plan on findings ATTRIBUTABLE to the landing
    worktree''s own diff, not on a global count -- a ledger-only land that adds one
    ticket file cannot have caused a 20-day-old rot alarm.'
  evidence: []
- text: Read the gate result from structured output, not by regexing rendered text.
    The current tick_line_re = re.compile(r'gate:TICK\s+(\d+)\s+errors?') parses human-facing
    CLI output, so a wording or formatting change silently flips the result to None
    (treated as 'skip'), and a locale or column change breaks it invisibly. frob check
    --json already exists and scripts/check_summary.py already parses it (key is 'code',
    not 'rule'). Do NOT fix this by making the regex more permissive.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
