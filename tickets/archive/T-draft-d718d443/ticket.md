---
id: T-draft-d718d443
title: Add frob ticket anchor CLI verb prose to docs/modules/tickets.md's Public API
  section
state: dropped
kind: docs
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1867 wired the `frob ticket anchor <id> --set/--clear --reason` CLI
verb (forwarding to frob.tickets._land.set_anchor, T-1856) but could not
touch docs/modules/tickets.md itself -- it was live-leased by T-1691 at
land time. The AFFECT001 finding this defers is waived with a reason
naming this follow-up.

Add a short paragraph to the Public API section (or set_anchor's own
existing entry) documenting the CLI verb by name, its --set/--clear
mutual exclusion, and that it forwards unchanged to set_anchor.

## Drop reason
- 2026-08-09: orphaned WIP ticket record found uncommitted-then-abandoned in this shared series worktree before this session started; its own code changes were reverted (untraceable to a live ticket, see this worktree's wip-preservation-then-revert commits) and its subject (frob ticket anchor CLI docs) is now covered by the real ticket T-1867; blocking every land in this worktree via the cross-worktree renumber-safety lock is worse than dropping a stale duplicate
