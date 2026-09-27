---
id: T-6605
title: promoting a draft at land leaves follow_up="T-draft-..." and other repo-wide
  references stale, so WIRE002 fires on the next land; promotion rewrites the references
  or WIRE002 resolves the promoted alias
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
due: null
rank: null
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
- src/frob/tickets/
- src/frob/gates/_wire.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: DOC006 inline waivers (T-draft-7ee140de)
  actor: logan
  at: '2026-09-26'
  old_length: 1258
  new_length: 1258
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by the crunk session (2026-09-26): after a stranded worktree
draft was promoted at land (T-draft-15f11db9 became T-0264), waivers
elsewhere that still name the draft id (`follow_up="T-draft-15f11db9"`)
fired WIRE002 on the next land. Verified on dev c897d821a6: promotion
renumbers the ticket directory and ledger row but nothing rewrites
draft-id references in source directives or docs, and WIRE002 resolves
the literal id only. frob's own coordinator hit the same shape all day
(this session's file-crunk.log maps 25 drafts to numbered ids by hand).

Deliver (automatic tier): (1) promotion records the alias (draft id ->
numbered id) in the ledger and rewrites `frob:ticket`, `follow_up=`,
`ticket "..."` and `[[...]]` references across tracked text files in the
same commit, logging each file; (2) WIRE002, TICK and DOC pointer
resolution accept a recorded alias as the numbered ticket for the
transition window (a stale reference is then a warning naming the new
id, never an error); (3) `frob ticket show T-draft-x` answers with the
numbered id. Positive control: a fixture with a waiver naming a draft
id; after promotion the waiver names the numbered id and WIRE002 stays
quiet; a reference in an untracked file is reported, not rewritten.
