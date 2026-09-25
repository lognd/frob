---
id: T-5817
title: 'ticket set flavour: CLI setter for story flavour'
state: planned
kind: feature
origin: agent
created: '2026-09-24'
priority: medium
blocked_by:
- T-5749
parent: T-5748
tier: ticket
sprint: null
runs_last: false
milestone: null
points: 2
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
- src/frob/tickets/_setters.py
- src/frob/_cli_parsers/_ticket/_metadata.py
- src/frob/app/ticket_runner/_lifecycle.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: the frob ticket set dispatch table (_SET_FIELD_HANDLERS) lives in _lifecycle.py,
    not _mutate.py -- correcting the initial filing guess
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/app/ticket_runner/_lifecycle.py
  reason: the frob ticket set dispatch table (_SET_FIELD_HANDLERS) lives in _lifecycle.py,
    not _mutate.py -- correcting the initial filing guess
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: parent
  old_value: null
  new_value: T-5748
  reason: part of the ledger-tiers story (T-5748), unblocks E2
  actor: logan
  at: '2026-09-24'
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
flavour: null
due: null
rank: null
---
found while working E2 (T-5766, ledger-tiers): frob ticket set has no flavour field -- A1 (T-5749) added StoryFlavour to the model but deferred the CLI setter verb. Add flavour as the seventh field in _TICKET_SET_FIELDS (_metadata.py), a set_flavour setter (_setters.py, mirroring set_tier's shape), and its runner dispatch (_mutate.py), so E2 can reclassify the 41 live stories through the normal accountable write path instead of a direct ledger edit.