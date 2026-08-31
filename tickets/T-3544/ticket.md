---
id: T-3544
title: Batch worktree-ledger mirrors and sweep filings into per-event sync commits
  (109+41 of last 300)
state: queued
kind: feature
origin: human
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_ledger_mirror.py
- src/frob/app/ticket_runner/_ledger_mirror.py
- src/frob/app/ticket_runner/_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
109 of the last 300 main commits are "chore(tickets): mirror <verb> T-x
from worktree" -- one commit per verb per ticket -- plus 41 one-per-ticket
sweep filings and 26 scope/body/evidence transitions. Batch them:
 1. Mirrors: coalesce all pending root-side mirrors into ONE
    "chore(tickets): sync ledger (T-a, T-b, ...)" commit per flush event
    (a land, a sweep completion, or a bounded timer), instead of per verb.
    The fleet reads the root ledger for liveness (leases, doable), so the
    flush cadence must stay prompt -- batch WITHIN an event, do not delay
    across events.
 2. Sweep filings: one commit per sweep run filing N tickets, not N
    commits.
 3. Keep per-verb commits ONLY where a verb's visibility is the fleet
    signal itself (e.g. block/unblock edges that gate another agent's
    doable) -- enumerate these in the Done report.
MUST-STAY-QUIET: a concurrent land between two batched mirrors still sees
a consistent ledger (no torn multi-ticket commit conflicts with the land
splice; reuse the T-3297 merge driver). ACCEPTANCE: the maintenance share
of new main commits drops below 1 maintenance commit per land on average,
measured over 20 consecutive lands.

## Failure log
- 2026-08-31 attempt 1: measured/re-scoped, not implemented: (1) mirror_ledger_change_to_primary commits synchronously per-call from ANY worktree's process against the shared primary under ledger_lock -- batching to one-commit-per-flush-event requires a genuine cross-process queue+flush redesign; too large/risky to build and land safely against a live fleet in one pass without a dedicated design ticket. (2) sweep filings: read _file_regression_ticket's only 2 call sites -- each sweep run already files AT MOST ONE regression ticket in one call, not N tickets per run as the ticket's own body assumes; the 41-commit figure needs re-measurement against the real code path before there is a real batching target here. Recommend re-scoping as (a) a design ticket for the mirror-commit queue and (b) re-measuring the 41 sweep-filing commits.
