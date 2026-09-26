---
id: T-draft-45b3adc4
title: 'ticket merge driver: auto-resolve tickets/<id>/ticket.md state conflicts with
  terminal-state-wins when syncing a closed ticket worktree'
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
- src/frob/app/ticket_runner/_merge_driver.py
- src/frob/tickets/
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
Reported by the crunk session (2026-09-26): `frob ticket work <id>` run to
sync a closed ticket's worktree onto main stops on a tickets/<id>/ticket.md
`state:` conflict every time: the branch carries `done`, main still has
the pre-close `in-progress` snapshot. The agent resolved it by hand and the
resolution is always the same (the terminal state on the ticket's own
branch wins). Verified on dev b41443f46d: `frob ticket merge-driver` is
registered for tickets.md (the ledger mirror) only; per-ticket ticket.md
frontmatter has no driver, so consumer repos see a raw text conflict.

Deliver: extend the merge driver (and the .gitattributes line `frob ticket
merge-driver` installs) to tickets/*/ticket.md; on a `state:` conflict
prefer the terminal state (done/dropped/archived) from either side, and
for other frontmatter fields keep the side with the later `updated`
stamp; body conflicts still surface. Positive control: a fixture with
`done` on the branch and `in-progress` on main merges clean to `done`,
and a real body conflict still stops the merge.
