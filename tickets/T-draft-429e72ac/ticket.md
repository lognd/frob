---
id: T-draft-429e72ac
title: ticket doable drops an explicit blocked_by on an in-progress blocker whenever
  lease scopes do not overlap (T-2104 self-heal), so dispatchers start work on unlanded
  dependencies
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: high
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
- src/frob/tickets/_doable.py
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
Reported by the crunk session (2026-09-26): `frob ticket doable` lists
T-0170, T-0172 and T-0186 as doable although each is blocked_by T-0185,
which is in-progress (not done). Verified on dev e98e686cbc:
`_open_blockers` (src/frob/tickets/_doable.py, T-2104) deliberately drops
a blocked_by entry whose blocker is IN_PROGRESS when the blocker's LIVE
lease scope no longer overlaps the ticket's scope, as a self-heal for
scope-collision auto-blocks; its own docstring admits blocked_by "is a
general dependency-ordering primitive, not exclusively a scope-" one, so
an explicit dependency on unlanded work is silently discarded exactly
when the two tickets touch different files, which is the common case
for a real dependency.

Deliver: record the block's origin on the edge (scope-collision
auto-block from `ticket block --by`/start, vs explicit dependency from
`ticket new --blocked-by`/`ticket block` without a lease holder); the
T-2104 self-heal applies only to scope-origin blocks; explicit blocks
keep the ticket out of `doable` until the blocker is done/dropped, and
`doable --json`/text mark the row "blocker in-progress: T-0185" instead
of omitting the fact. Migration: existing edges with no origin are
treated as explicit (safe default; a dispatcher starting too late beats
starting on unlanded work). Positive control: a fixture with an explicit
blocked_by on an in-progress, non-overlapping blocker; doable excludes
the ticket and names the blocker; a scope-origin block on a narrowed
lease still self-heals.
