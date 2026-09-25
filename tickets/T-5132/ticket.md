---
id: T-5132
title: 'Ticket sizing: points field, frob ticket points setter, refusal at start for
  unsized queued tickets, points-weighted flow and sprint show'
state: done
kind: feature
origin: human
created: '2026-09-20'
priority: high
parent: null
tier: story
sprint: null
runs_last: false
milestone: 1.0.0
flavour: user_story
due: null
rank: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5132
branch: t-5132
scope:
- src/frob/tickets/_models.py
- src/frob/tickets/_setters.py
- src/frob/tickets/_flow.py
- src/frob/tickets/_sprint.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_mutate.py
- docs/commands/ticket.md
- docs/modules/tickets-data-storage.md
- src/frob/app/ticket_runner/_lifecycle.py
- src/frob/tickets/_new_renumber.py
- src/frob/_cli_parsers/_ticket/_metadata.py
- src/frob/_cli_parsers/_ticket/_progress.py
- src/frob/_cli_parsers/_ticket/_new.py
- src/frob/_cli_parsers/_ticket/__init__.py
scope_breadth_ack: true
scope_breadth_ack_reason: one model field threaded through new, setter, flow, sprint
  show and docs; each file is a one-hunk change
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_lifecycle.py
  reason: start-time unsized refusal enforcement point lives in _lifecycle.py alongside
    _refuse_empty_scope_on_start
  actor: logan
  at: '2026-09-22'
- op: add
  glob: src/frob/tickets/_new_renumber.py
  reason: TicketSpec.points validation (validate_points, mirroring validate_milestone)
    lives in _validate_new_ticket_spec here
  actor: logan
  at: '2026-09-22'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_metadata.py
  reason: argparse wiring for --points/--unsized-ack/frob ticket points/tokens verbs
    lives in _cli_parsers/_ticket, implicit_scope's CLI-wiring grant covers __main__.py/config.py/ticket_runner/__init__.py
    but not this sibling parser package
  actor: logan
  at: '2026-09-22'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_progress.py
  reason: argparse wiring for --points/--unsized-ack/frob ticket points/tokens verbs
    lives in _cli_parsers/_ticket, implicit_scope's CLI-wiring grant covers __main__.py/config.py/ticket_runner/__init__.py
    but not this sibling parser package
  actor: logan
  at: '2026-09-22'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_new.py
  reason: argparse wiring for --points/--unsized-ack/frob ticket points/tokens verbs
    lives in _cli_parsers/_ticket, implicit_scope's CLI-wiring grant covers __main__.py/config.py/ticket_runner/__init__.py
    but not this sibling parser package
  actor: logan
  at: '2026-09-22'
- op: add
  glob: src/frob/_cli_parsers/_ticket/__init__.py
  reason: parser registration dispatch table for new points/tokens subcommands
  actor: logan
  at: '2026-09-22'
triage_changes:
- field: milestone
  old_value: null
  new_value: 1.0.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-20'
- field: flavour
  old_value: null
  new_value: user_story
  reason: 'E2 (T-5766): census-based flavour classification (heuristic per E1''s own
    candidate signal)'
  actor: logan
  at: '2026-09-24'
body_changes:
- mode: append
  reason: 'owner 2026-09-20: track agent token usage per ticket, optional, absent
    for human work'
  actor: logan
  at: '2026-09-20'
  old_length: 1402
  new_length: 2640
evidence:
- tests/test_tickets_points.py::TestValidatePoints::test_valid_value_accepted
- tests/test_tickets_points.py::TestValidatePoints::test_invalid_value_refused
- tests/test_tickets_points.py::TestSetPoints::test_valid_value_sets_field
- tests/test_tickets_points.py::TestSetPoints::test_invalid_value_refused
- tests/test_tickets_points.py::TestSetUnsizedAck::test_ack_sets_both_fields
- tests/test_tickets_points.py::TestSetUnsizedAck::test_reason_missing_refuses
- tests/test_tickets_points.py::TestSetTokens::test_sets_fields
- tests/test_tickets_points.py::TestStartUnsizedRefusal::test_unsized_queued_ticket_refuses
- tests/test_tickets_points.py::TestStartUnsizedRefusal::test_sized_ticket_starts_cleanly
- tests/test_tickets_points.py::TestStartUnsizedRefusal::test_unsized_ack_bypasses_refusal
- tests/test_tickets_points.py::TestStartUnsizedRefusal::test_full_start_cli_refuses_on_unsized_ticket
- tests/test_tickets_points.py::TestTicketPointsPerHour::test_unsized_or_unstarted_ticket_excluded
- tests/test_tickets_points.py::TestTicketTokensPerPoint::test_sized_and_tokened_calibrates
- tests/test_tickets_points.py::TestTicketTokensPerPoint::test_no_qualifying_ticket_returns_none
- tests/test_tickets_points.py::TestSprintViewPoints::test_points_rollup_and_eta
designated_repro_test: null
acceptance:
- text: given a ticket with points=None, when frob ticket start runs without --unsized-ack,
    then it refuses with the remedy naming frob ticket points ID N
  evidence:
  - tests/test_tickets_points.py::TestValidatePoints::test_valid_value_accepted
  - tests/test_tickets_points.py::TestValidatePoints::test_invalid_value_refused
  - tests/test_tickets_points.py::TestSetPoints::test_valid_value_sets_field
  - tests/test_tickets_points.py::TestSetPoints::test_invalid_value_refused
  - tests/test_tickets_points.py::TestSetUnsizedAck::test_ack_sets_both_fields
  - tests/test_tickets_points.py::TestSetUnsizedAck::test_reason_missing_refuses
  - tests/test_tickets_points.py::TestSetTokens::test_sets_fields
  - tests/test_tickets_points.py::TestStartUnsizedRefusal::test_unsized_queued_ticket_refuses
  - tests/test_tickets_points.py::TestStartUnsizedRefusal::test_sized_ticket_starts_cleanly
  - tests/test_tickets_points.py::TestStartUnsizedRefusal::test_unsized_ack_bypasses_refusal
  - tests/test_tickets_points.py::TestStartUnsizedRefusal::test_full_start_cli_refuses_on_unsized_ticket
  - tests/test_tickets_points.py::TestTicketPointsPerHour::test_unsized_or_unstarted_ticket_excluded
  - tests/test_tickets_points.py::TestTicketTokensPerPoint::test_sized_and_tokened_calibrates
  - tests/test_tickets_points.py::TestTicketTokensPerPoint::test_no_qualifying_ticket_returns_none
  - tests/test_tickets_points.py::TestSprintViewPoints::test_points_rollup_and_eta
- text: given --points 4, when frob ticket new or frob ticket points runs, then it
    refuses with the allowed set 1 2 3 5 8 13
  evidence:
  - tests/test_tickets_points.py::TestValidatePoints::test_valid_value_accepted
  - tests/test_tickets_points.py::TestValidatePoints::test_invalid_value_refused
  - tests/test_tickets_points.py::TestSetPoints::test_valid_value_sets_field
  - tests/test_tickets_points.py::TestSetPoints::test_invalid_value_refused
  - tests/test_tickets_points.py::TestSetUnsizedAck::test_ack_sets_both_fields
  - tests/test_tickets_points.py::TestSetUnsizedAck::test_reason_missing_refuses
  - tests/test_tickets_points.py::TestSetTokens::test_sets_fields
  - tests/test_tickets_points.py::TestStartUnsizedRefusal::test_unsized_queued_ticket_refuses
  - tests/test_tickets_points.py::TestStartUnsizedRefusal::test_sized_ticket_starts_cleanly
  - tests/test_tickets_points.py::TestStartUnsizedRefusal::test_unsized_ack_bypasses_refusal
  - tests/test_tickets_points.py::TestStartUnsizedRefusal::test_full_start_cli_refuses_on_unsized_ticket
  - tests/test_tickets_points.py::TestTicketPointsPerHour::test_unsized_or_unstarted_ticket_excluded
  - tests/test_tickets_points.py::TestTicketTokensPerPoint::test_sized_and_tokened_calibrates
  - tests/test_tickets_points.py::TestTicketTokensPerPoint::test_no_qualifying_ticket_returns_none
  - tests/test_tickets_points.py::TestSprintViewPoints::test_points_rollup_and_eta
- text: given a sprint whose tickets carry points, when frob ticket sprint show LABEL
    runs, then it prints total points, points done and a points-weighted ETA
  evidence:
  - tests/test_tickets_points.py::TestValidatePoints::test_valid_value_accepted
  - tests/test_tickets_points.py::TestValidatePoints::test_invalid_value_refused
  - tests/test_tickets_points.py::TestSetPoints::test_valid_value_sets_field
  - tests/test_tickets_points.py::TestSetPoints::test_invalid_value_refused
  - tests/test_tickets_points.py::TestSetUnsizedAck::test_ack_sets_both_fields
  - tests/test_tickets_points.py::TestSetUnsizedAck::test_reason_missing_refuses
  - tests/test_tickets_points.py::TestSetTokens::test_sets_fields
  - tests/test_tickets_points.py::TestStartUnsizedRefusal::test_unsized_queued_ticket_refuses
  - tests/test_tickets_points.py::TestStartUnsizedRefusal::test_sized_ticket_starts_cleanly
  - tests/test_tickets_points.py::TestStartUnsizedRefusal::test_unsized_ack_bypasses_refusal
  - tests/test_tickets_points.py::TestStartUnsizedRefusal::test_full_start_cli_refuses_on_unsized_ticket
  - tests/test_tickets_points.py::TestTicketPointsPerHour::test_unsized_or_unstarted_ticket_excluded
  - tests/test_tickets_points.py::TestTicketTokensPerPoint::test_sized_and_tokened_calibrates
  - tests/test_tickets_points.py::TestTicketTokensPerPoint::test_no_qualifying_ticket_returns_none
  - tests/test_tickets_points.py::TestSprintViewPoints::test_points_rollup_and_eta
- text: given a closed ticket, when frob ticket flow runs, then it reports actual
    hours from start to close and points per hour for the window
  evidence:
  - tests/test_tickets_points.py::TestValidatePoints::test_valid_value_accepted
  - tests/test_tickets_points.py::TestValidatePoints::test_invalid_value_refused
  - tests/test_tickets_points.py::TestSetPoints::test_valid_value_sets_field
  - tests/test_tickets_points.py::TestSetPoints::test_invalid_value_refused
  - tests/test_tickets_points.py::TestSetUnsizedAck::test_ack_sets_both_fields
  - tests/test_tickets_points.py::TestSetUnsizedAck::test_reason_missing_refuses
  - tests/test_tickets_points.py::TestSetTokens::test_sets_fields
  - tests/test_tickets_points.py::TestStartUnsizedRefusal::test_unsized_queued_ticket_refuses
  - tests/test_tickets_points.py::TestStartUnsizedRefusal::test_sized_ticket_starts_cleanly
  - tests/test_tickets_points.py::TestStartUnsizedRefusal::test_unsized_ack_bypasses_refusal
  - tests/test_tickets_points.py::TestStartUnsizedRefusal::test_full_start_cli_refuses_on_unsized_ticket
  - tests/test_tickets_points.py::TestTicketPointsPerHour::test_unsized_or_unstarted_ticket_excluded
  - tests/test_tickets_points.py::TestTicketTokensPerPoint::test_sized_and_tokened_calibrates
  - tests/test_tickets_points.py::TestTicketTokensPerPoint::test_no_qualifying_ticket_returns_none
  - tests/test_tickets_points.py::TestSprintViewPoints::test_points_rollup_and_eta
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
Owner directive 2026-09-20: tickets need story points and/or effort hours, linted. Design decision (agreed default, revisit if the owner objects): points only, no hours field. points: int | None on Ticket and TicketSpec, allowed values 1 2 3 5 8 13 (Fibonacci, validated at write time like validate_milestone, never at ledger load). --points N on frob ticket new; frob ticket points ID N setter with T-1615 auto-commit. Hours are DERIVED, not entered: actual wall from the start transition to the close transition (already mined by _flow for velocity) is reported per ticket and as points-per-hour calibration in frob ticket flow, so the human enters one small number and the system measures the rest. ENFORCEMENT is at the state transition, not a repo-wide lint: frob ticket start refuses a ticket with points=None (single override flag --unsized-ack REASON, recorded on the ticket like scope_breadth_ack), frob ticket new WARNs when --points is omitted. This makes every ticket that actually enters work sized, needs no backfill of the 666 existing queued tickets, and never touches done/dropped/archived tickets -- the backwards-compat question disappears because old tickets only meet the check when someone starts them. frob ticket flow, sprint show, epic and board gain a points column and a points-weighted burn-down ETA next to the count-based one. Epics/stories roll up the sum of leaf points.

AMENDMENT (owner, 2026-09-20): optional token usage per ticket. Field tokens_in / tokens_out: int | None on Ticket (None = human or unmeasured, never 0). Manual path: frob ticket close --tokens-in N --tokens-out N and a frob ticket tokens ID setter, same auto-commit as points. Automatic path (automatic-over-commands directive): at frob ticket start, record the driving session id on the lease (CLAUDE_SESSION_ID or the Claude Code transcript path if exposed in env; else None); at close/land, sum the usage.input_tokens and usage.output_tokens fields of every assistant message in that session's transcript jsonl under ~/.claude/projects/<slug>/ between the start and close timestamps and write them, logging the transcript path and message count. Cache-read tokens recorded separately (tokens_cache_read) since they dominate long sessions and cost differently. frob stats already estimates frob's OWN output tokens per invocation (stats/_agentic.py output_tokens_est); that is a different number and stays where it is, but the flow report gains tokens per point and tokens per landed ticket next to hours per point, so points are calibrated against both wall time and spend. Nothing is enforced: a None tokens field is valid forever.