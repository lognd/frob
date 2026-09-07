---
id: T-draft-b488ae79
title: evidence --replace/--remove is not mirrored to the primary checkout, so frob
  ticket land refuses on stale evidence it already rebound away from
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_evidence.py
- src/frob/app/ticket_runner/_ledger_mirror.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: measured while landing T-4143 in this session
  actor: logan
  at: '2026-09-07'
  old_length: 1910
  new_length: 2480
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Description: `frob ticket land` refuses with "evidence no longer resolves
post-merge" against evidence ids that DO still resolve on the landing
branch, because `_reverify_evidence_post_merge` (src/frob/tickets/_land.py)
loads the ticket via `_load_one(worktree, ticket_id)` where `worktree` can
resolve stale state: the primary checkout's own mirrored copy of the
ticket (`chore(tickets): mirror scope T-#### from worktree` commits) is
kept current for SCOPE changes only -- `mirror_ledger_change_to_primary`
is invoked from the scope-mutation path but not from
`replace_evidence`/`remove_evidence`. A ticket that runs
`frob ticket evidence --replace OLD NEW` after an earlier scope mirror has
already run ends up with its evidence rebind invisible to the primary
checkout, so a subsequent `frob ticket land` on that ticket refuses citing
the OLD (already-rebound-away) node id, even though the actual landing
branch's own ticket.md has the correct, current evidence list.

Measured live: T-4143 (this session) hit this exactly -- `replace_evidence`
rebound two evidence ids to a new test file (to resolve an unrelated
CrossTicketLeakage against a sibling ticket), the ticket's own worktree
branch showed the correct evidence immediately, but `frob ticket land`
repeatedly refused with the OLD ids across three retries, and the primary
checkout's tickets/T-4143/ticket.md was confirmed (read-only) to still
list the pre-replace ids.

What to do: audit every ledger-mutating verb for whether it calls
`mirror_ledger_change_to_primary` (or should) -- `replace_evidence`/
`remove_evidence` at minimum need it, and this may be a broader gap
(other mutation verbs worth auditing too). Do NOT hand-fix by editing the
primary checkout's ticket file directly -- that is the exact anti-pattern
this repo's "coordinator never dirties root" rule exists to prevent; the
fix belongs in the mirroring call sites themselves.


Refined finding (measured across 3+ retries, no intervening changes): the worktree's OWN tickets/T-4143/ticket.md is confirmed correct (new evidence ids) at every retry, yet frob ticket land repeatedly refuses citing the OLD (already-rebound-away) ids as 'no longer resolves post-merge'. This suggests _load_one(worktree, ticket_id) inside _reverify_evidence_post_merge is not reading the current tip of the --worktree path at that point in _land_locked -- possibly a squash/compose stage reads a stale snapshot. Needs real instrumentation, not more black-box retries.