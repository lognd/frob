---
id: T-2284
title: Land's Tier-A auto-fix edits files outside the landing ticket's scope (and
  under other tickets' live leases), forcing CrossTicketLeakage refusals and manual
  reverts
state: queued
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'A Tier-A handler that would modify a file outside the landing ticket''s scope
    is skipped, with the skip reported naming handler/file/reason (fails today: it
    writes and the land is refused afterwards)'
  evidence: []
- text: A file under another ticket's live lease is never modified; state which check
    takes precedence and why
  evidence: []
- text: 'MUST-STILL-PASS: a handler fixing a file the landing ticket owns still runs
    and commits (SYS111 ratchet bump is the shape); a land with no out-of-scope activity
    is byte-identical to today'
  evidence: []
- text: The skip is visible in the land's own output, not only in a log
  evidence: []
- text: State whether any handler is inherently repo-wide (REL002 is the candidate)
    and what it should do instead of being silently exempt
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
# Land's Tier-A auto-fix edits files outside the landing ticket's scope, including files under another ticket's live lease, forcing a CrossTicketLeakage refusal and a manual revert

## Measured evidence (2026-08-17)

While landing T-2274, the agent hit `CrossTicketLeakage` **twice**. One
occurrence was self-inflicted by the land itself:

> hit `CrossTicketLeakage` twice -- once from land's own Tier-A auto-fix
> reformatting `scripts/fleet_status.py` (T-2236's live scope) as an undisclosed
> passenger; reverted that file back to main's content before landing.

So the sequence is: the land runs its Tier-A auto-fix, the auto-fix reformats a
file the landing ticket does not own and another ticket holds a live lease on,
the land's own `CrossTicketLeakage` guard then refuses the land, and the agent
has to revert a file it never chose to touch before it can proceed.

The guard is working correctly -- that is the good news, and this is friction
rather than an integrity hole. The cost is a refused land plus a manual revert
per occurrence, twice in a single land here.

The handlers do not consult scope or lease at all. `git grep -nE "lease" --
src/frob/gates/_fix_engine.py` returns exactly three hits: an `import` of
`fix_rel002_release_sync`, a docstring aside about `new_ticket` failing under a
worktree-lease, and a dispatch-table entry naming the same function. Nothing
gates a handler on what the landing ticket is allowed to modify.

## Do NOT fix it this way

- **Do NOT disable or narrow the Tier-A auto-fix.** It does real work; T-1137/
  T-1138 built it deliberately, and several tickets this session relied on it
  (the SYS111 capability-ratchet bump landed automatically as part of a land).
  The defect is WHERE it writes, not that it writes.
- **Do NOT weaken `CrossTicketLeakage`.** It is the only reason this was caught
  rather than published as an unattributed passenger -- exactly the class T-2274
  just fixed for the bookkeeping-staging path. Loosening it to accommodate the
  auto-fix would reopen that hole from a different direction.
- **Do NOT have the land silently revert the out-of-scope edit.** The agent must
  know a fix was skipped or undone; a silent revert means the finding the
  handler was addressing quietly persists with nobody informed. T-2255's whole
  lesson was that a silent skip is worse than a loud one.
- **Do NOT decide ownership by comparing scope strings.** Scope entries are
  globs; expand and compare resolved paths, reusing the machinery T-2225 built
  (`_expand_scope_globs_to_paths`) rather than a second implementation. Token/
  grammar, never lexical.

## Acceptance criteria

1. (MUST FAIL FIRST) A Tier-A handler that would modify a file outside the
   landing ticket's declared scope does not do so; it is skipped and the skip is
   reported naming the handler, the file, and why. Fails today: the handler
   writes and `CrossTicketLeakage` refuses the land afterwards.
2. A file under ANOTHER ticket's live lease is never modified, even if it is
   somehow within the landing ticket's scope -- state which check takes
   precedence and why.
3. MUST-STILL-PASS CONTROLS: a Tier-A handler fixing a file the landing ticket
   DOES own still runs and still commits (verify with a real case -- the SYS111
   capability-ratchet bump is the shape); and a land with no out-of-scope
   handler activity behaves byte-identically to today.
4. The skip is visible in the land's own output, not only in a log nobody reads.
5. State whether any handler is INHERENTLY repo-wide and cannot be scoped
   (REL002/release-sync is the obvious candidate). If one exists, say what it
   should do instead rather than silently exempting it.

## Scope note

`src/frob/gates/_fix_engine.py` owns the Tier-A handler dispatch table
(`:538`). `src/frob/gates/_fix_engine_tier_b.py` is the sibling; check whether
it shares the defect and say so. The scope/lease information already exists --
the land knows its own ticket, and T-2225 built resolved-path expansion -- so
this is a wiring fix, not new detection.
