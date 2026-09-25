---
id: T-draft-b756915c
title: frob ticket due/rank CLI verbs with default-rank derivation
state: queued
kind: feature
origin: agent
created: '2026-09-24'
priority: medium
parent: T-5748
tier: ticket
sprint: null
runs_last: false
milestone: 0.536.0
flavour: null
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
worktree: null
branch: null
scope:
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_mutate.py
- src/frob/_cli_parsers/_ticket/_new.py
- src/frob/tickets/_setters.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: null
  new_value: T-5748
  reason: part of the ledger-tiers story (T-5748); the due/rank CLI verbs deferred
    out of T-5751's model-only scope
  actor: logan
  at: '2026-09-24'
- field: milestone
  old_value: null
  new_value: 0.536.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-5751 (A2, ledger-tiers): the model fields Ticket.due/Ticket.rank landed model-only; CLI verbs 'frob ticket due <id> <date>' and 'frob ticket rank <id> --top|--before <id>|--after <id>' with a default rank derivation (priority, then blocked_by depth, then age) are still needed and were out of T-5751's declared scope (src/frob/tickets/_models.py only).