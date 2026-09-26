---
id: T-6580
title: frob ticket reopen accepts dropped tickets with --reason so a transient-collision
  drop does not force a duplicate ticket
state: queued
kind: feature
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
- src/frob/tickets/_reporting.py
- src/frob/tickets/_models.py
- docs/modules/tickets.md
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
Reported by the crunk session (2026-09-26): crunk T-0171 was dropped purely
because of a transient scope-lease collision; `frob ticket reopen` refuses
with ReopenRequiresDone (verified on dev b41443f46d: `_reporting.py`
requires `state is DONE`; reopen exists to repair a false close), so the
agent filed a duplicate T-0187 with --ack-related and the history split.

Deliver (explicit-flag tier, --reason already required): reopen also
accepts DROPPED, returning the ticket to queued, keeping the drop reason
and the reopen reason in the ledger trail, clearing worktree/branch/lease
fields, and refusing when a newer ticket already cites this one as its
duplicate (point the caller at that id). Positive control: a dropped
fixture ticket reopens to queued with both reasons recorded; an
in-progress one still refuses with the existing error.
