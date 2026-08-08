---
id: T-1617
title: Ledger merge silently drops a frontmatter field changed on main when a worktree
  edited the same ticket
state: dropped
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- .gitattributes
- tests/**
- docs/design/ledger-v2.md
- src/frob/tickets/_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/**
  reason: 'TICK009: narrowing my own over-broad filing-time scope to the files this
    ticket actually names'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_store.py
  reason: narrowed from a package glob to the specific modules named in the ticket
    body
  actor: logan
  at: '2026-08-06'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
A ticket field changed and committed on main was silently dropped when main was merged into a worktree whose copy of that same ticket block had also changed. No conflict, no warning, no log line -- the field simply kept the worktree's older value, and the next command read the stale one.

Observed 2026-08-05, concretely:
1. On main: `frob ticket kind T-1593 feature`, written to tickets.md and committed.
2. In .claude/worktrees/w26-arch-splits: `git merge main` -- reported success, 79 insertions, no conflicts.
3. In that worktree afterwards: `frob ticket show T-1593 --json` still reported kind=bug.
4. `frob ticket land T-1593` consequently refused with a BUG002 finding naming "(kind=bug)", against a ticket that was feature-kind on main.

The worktree's own T-1593 block had been edited locally (Done report, evidence ids) during the agent's work, so both sides touched the same region of the same block. Git merged the file without complaint and the frontmatter field lost.

NOT root-caused, and the distinction matters -- do not assume:
- git's own line-level auto-resolution may have taken the worktree's hunk, or
- the ledger splice / canonicalization may have rewritten the block from a parsed in-memory ticket, discarding whatever the merge produced.
Determine which BEFORE proposing a fix. A git-level resolution is fixed by a merge driver or .gitattributes; a splice-level overwrite is fixed in frob's own code, and they have nothing in common.

Why this is more than a papercut: a semantic field disappearing with no conflict marker means the ledger can silently disagree with itself across checkouts, and the disagreement surfaces only when some gate happens to read the losing side. state, priority, blocked_by, scope, and parent are all exposed to the same shape -- kind was merely the one caught, and only because a gate refused loudly. A silently lost `state` or `blocked_by` would not announce itself at all.

Deliverables:
- Root cause identified (git resolution vs splice overwrite), stated explicitly.
- Whichever layer is responsible, make a losing field change either impossible or LOUD. A conflict a human resolves is an acceptable outcome; a silent drop is not.
- A regression test reproducing the exact sequence above: edit a field on main, edit the same ticket's body in a worktree, merge, and assert the field change survived.

Note for the fix: ledger v2 (tickets/T-####/ticket.md, one file per ticket) narrows this considerably, since concurrent edits to different tickets stop sharing a file at all -- but it does NOT eliminate it, because this case had both sides editing the SAME ticket. Do not close this on the strength of the v2 migration alone.

## Drop reason
- 2026-08-08: Reproduced twice under this repos default ledger v2: same-ticket concurrent edits to disjoint fields (kind vs evidence; priority vs done-report) merge cleanly via gits own 3-way merge, field survives correctly, no custom driver involved. Root cause is v1-monofile-specific (tickets.md merge=frob-ledger driver plus splice_ledger), inside T-1552s deletion blast radius. See T-1617 evidence trail for the two reproduction runs. (absorbed by T-1552)
