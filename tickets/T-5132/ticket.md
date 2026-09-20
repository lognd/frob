---
id: T-5132
title: 'Ticket sizing: points field, frob ticket points setter, refusal at start for
  unsized queued tickets, points-weighted flow and sprint show'
state: queued
kind: feature
origin: human
created: '2026-09-20'
priority: high
parent: null
tier: story
sprint: v0.534.0
runs_last: false
milestone: 1.0.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_models.py
- src/frob/tickets/_setters.py
- src/frob/tickets/_flow.py
- src/frob/tickets/_sprint.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_mutate.py
- docs/commands/ticket.md
- docs/modules/tickets-data-storage.md
scope_breadth_ack: true
scope_breadth_ack_reason: one model field threaded through new, setter, flow, sprint
  show and docs; each file is a one-hunk change
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: milestone
  old_value: null
  new_value: 1.0.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-20'
body_changes:
- mode: append
  reason: 'owner 2026-09-20: track agent token usage per ticket, optional, absent
    for human work'
  actor: logan
  at: '2026-09-20'
  old_length: 1402
  new_length: 2640
designated_repro_test: null
acceptance:
- text: given a ticket with points=None, when frob ticket start runs without --unsized-ack,
    then it refuses with the remedy naming frob ticket points ID N
  evidence: []
- text: given --points 4, when frob ticket new or frob ticket points runs, then it
    refuses with the allowed set 1 2 3 5 8 13
  evidence: []
- text: given a sprint whose tickets carry points, when frob ticket sprint show LABEL
    runs, then it prints total points, points done and a points-weighted ETA
  evidence: []
- text: given a closed ticket, when frob ticket flow runs, then it reports actual
    hours from start to close and points per hour for the window
  evidence: []
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
Owner directive 2026-09-20: tickets need story points and/or effort hours, linted. Design decision (agreed default, revisit if the owner objects): points only, no hours field. points: int | None on Ticket and TicketSpec, allowed values 1 2 3 5 8 13 (Fibonacci, validated at write time like validate_milestone, never at ledger load). --points N on frob ticket new; frob ticket points ID N setter with T-1615 auto-commit. Hours are DERIVED, not entered: actual wall from the start transition to the close transition (already mined by _flow for velocity) is reported per ticket and as points-per-hour calibration in frob ticket flow, so the human enters one small number and the system measures the rest. ENFORCEMENT is at the state transition, not a repo-wide lint: frob ticket start refuses a ticket with points=None (single override flag --unsized-ack REASON, recorded on the ticket like scope_breadth_ack), frob ticket new WARNs when --points is omitted. This makes every ticket that actually enters work sized, needs no backfill of the 666 existing queued tickets, and never touches done/dropped/archived tickets -- the backwards-compat question disappears because old tickets only meet the check when someone starts them. frob ticket flow, sprint show, epic and board gain a points column and a points-weighted burn-down ETA next to the count-based one. Epics/stories roll up the sum of leaf points.

AMENDMENT (owner, 2026-09-20): optional token usage per ticket. Field tokens_in / tokens_out: int | None on Ticket (None = human or unmeasured, never 0). Manual path: frob ticket close --tokens-in N --tokens-out N and a frob ticket tokens ID setter, same auto-commit as points. Automatic path (automatic-over-commands directive): at frob ticket start, record the driving session id on the lease (CLAUDE_SESSION_ID or the Claude Code transcript path if exposed in env; else None); at close/land, sum the usage.input_tokens and usage.output_tokens fields of every assistant message in that session's transcript jsonl under ~/.claude/projects/<slug>/ between the start and close timestamps and write them, logging the transcript path and message count. Cache-read tokens recorded separately (tokens_cache_read) since they dominate long sessions and cost differently. frob stats already estimates frob's OWN output tokens per invocation (stats/_agentic.py output_tokens_est); that is a different number and stays where it is, but the flow report gains tokens per point and tokens per landed ticket next to hours per point, so points are calibrated against both wall time and spend. Nothing is enforced: a None tokens field is valid forever.