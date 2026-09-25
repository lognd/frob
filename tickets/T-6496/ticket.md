---
id: T-6496
title: 'land finalize: dir/id mismatch after promotion fails every later land (T-5817
  case)'
state: queued
kind: bug
origin: agent
created: '2026-09-25'
priority: critical
parent: T-5630
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
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
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_land.py
- src/frob/gates/_tickets.py
- tests/test_ticket_renumber_atomicity.py
- docs/modules/
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
Measured 2026-09-25 on dev: after the T-5813 "full recompose" land,
tickets/T-5817/ticket.md still carried `id: T-draft-a9c4460e` (the
directory was renamed by promotion, the id field was not). Every later
land then failed at sibling-draft finalization:

  ERROR: tickets: renumber_one_v2: T-draft-a9c4460e not found
  ERROR: land: sibling draft T-draft-a9c4460e finalize failed (NotFound)
         after T-5332 already finalized -- inspect ... and retry

Two lands (T-5469, T-5332) burned ~15 min each on this before the cause
was found; T-5332's worktree was left with staged promotions of unrelated
drafts (T-6392 -> T-5821 etc.) that had to be reset by hand.
`frob ticket admin renumber T-draft-a9c4460e T-5817` could not repair it
because lookup is by directory/index, so the fix required a git mv of the
directory back to the draft name (a hand edit the ledger rules forbid)
followed by the renumber verb.

Deliver:
1. Root cause in the recompose/promotion path: the directory rename and
   the id-field rewrite must be one atomic step (write the file, then
   rename, or rename then rewrite, under the same lock), with a test that
   kills the process between the two and shows the ledger is still
   consistent or fully rolled back.
2. Ledger invariant + gate: a TICK rule that refuses (in `frob check` and
   at land pre-check) any tickets/<dir>/ticket.md whose `id:` differs
   from <dir>, naming both; positive control plants one.
3. Self-heal: `frob ticket admin renumber` (or `reconcile --apply`)
   resolves a ticket by EITHER directory or id field and repairs a
   dir/id mismatch in one verb, so the fix never needs a hand git mv.
4. Land finalize: a sibling-draft finalize failure must not leave staged
   renames of unrelated drafts in the worktree; roll the worktree ledger
   back to the merge commit on failure (the same "worktree left clean"
   posture the pre-land refusals already have).
5. Land finalize must skip a sibling draft whose id no longer exists in
   the ledger (already promoted by an earlier land) with a WARN, not fail
   the whole land after the ticket itself finalized.
