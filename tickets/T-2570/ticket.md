---
id: T-2570
title: 'ledger mirror makes main a second writer of per-ticket files: decide the v2
  merge strategy'
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/guides/agent-playbook.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/guides/agent-playbook.md
  reason: fix stale merge-driver instruction now contradicting .gitattributes
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/guides/agent-playbook.md
  reason: fix stale merge-driver instruction now contradicting .gitattributes
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/guides/agent-playbook.md
  reason: fix stale merge-driver instruction now contradicting .gitattributes
  actor: logan
  at: '2026-08-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## What changed

T-2563 (`b8b4fddaa`) made ledger-only ticket edits from a worktree mirror
to the primary checkout, so they reach main instead of stranding on the
branch. That fix is correct and needed -- scope IS the write lease, and a
stranded ledger edit leaves the rest of the fleet reasoning off a stale
scope.

Its consequence is that **main is now a second writer of
`tickets/T-####/ticket.md`**. A worktree that later runs `git merge main`
can now conflict on its own ticket file. The agent that built T-2563 hit
exactly this while building it.

## Why the obvious fix is wrong here

The natural reaction is "register the `frob ticket merge-driver`". Do NOT
do that without a decision, because this repo retired it deliberately.
`.gitattributes` records why (T-1258/T-2356): ledger v2 replaced the
`tickets.md` monofile with disjoint `tickets/T-####/` directories --
ordinary git objects that git's native per-file 3-way merge already
resolves correctly -- and the driver plus the `.gitattributes` lines
routing files through it were retired for THIS repo. The driver remains
in frob's source only for other repos still on v1/monofile mode.

Measured on this clone: `git config --get merge.frob-tickets.driver` is
empty, and `git check-attr merge` reports `unspecified` for both
`tickets/tickets.md` and a v2 per-ticket file. So the driver is
unregistered AND unrouted -- consistent with the documented retirement,
not with a missed setup step.

Note also `docs/guides/agent-playbook.md:969` still instructs agents to
register the driver once per clone. That instruction predates the v2
migration and now contradicts `.gitattributes`. Whatever is decided
below, that line needs to be corrected or removed -- an agent following
it today would be re-enabling retired machinery.

## The actual question to decide

Under v2, what merges a per-ticket file when both main (via the T-2563
mirror) and a worktree have edited it?

1. Native 3-way is sufficient -- conflicts are rare and genuinely need a
   human/agent, because two writers changed the same YAML key. Then the
   fix is documentation plus the playbook correction, nothing more.
2. Per-ticket files need a merge strategy of their own. If so it should
   be chosen the way `rapid-debt.jsonl` chose `merge=union`: a BUILT-IN
   git driver where the semantics fit, explicitly because a built-in
   needs no per-clone `git config` registration, and a worktree that
   skipped that setup silently falls back to the conflicting default --
   the exact failure mode that argument was made to close. A ticket file
   is not append-only, so `union` is almost certainly WRONG here; say so
   explicitly rather than copying the pattern.
3. Reduce the second writer. Narrow what the mirror writes so main and
   the worktree touch disjoint regions of the file.

## Evidence required

Reproduce the conflict first -- two branches, one edit each to the same
`tickets/T-####/ticket.md`, merged -- and report whether native 3-way
actually conflicts or resolves. Measure before designing. If it resolves
cleanly, option 1 wins and this ticket is mostly a docs correction.

Do NOT hand-edit a ledger file to resolve a conflict. A space-hash in
prose once broke tickets.md YAML and took every gate down.
