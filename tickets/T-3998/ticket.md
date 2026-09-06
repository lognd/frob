---
id: T-3998
title: 'F-212: a finished worktree''s lease can only be broken by stealing the whole
  ticket; there is no release verb'
state: queued
kind: ux
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_leases.py
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
Consumer logand.app-v2 F-212, 2026-09-06:

  "Adding wasm-engine/build.rs to T-0181's scope from the sub-17-rust worktree
   failed with TicketOwnershipViolation because the lease sat with the sibling
   t-0181-shell worktree (finished, but never released). frob ticket scope
   offers no --steal-equivalent of its own; the only way forward was
   frob ticket start --steal on the ticket as a whole, which invalidates the
   other worktree's ability to close/land it."

THE DEFECT IS THAT THE ONLY AVAILABLE REMEDY IS DESTRUCTIVE AND OVER-BROAD. To
perform a small additive operation -- add one path to scope -- the user had to
seize the WHOLE ticket, revoking a sibling worktree's ability to close or land.
It happened to be safe there because that worktree was finished, but the user had
to determine that themselves, and nothing in the tool would have stopped them if
it had not been.

A CAPABILITY GAP, NOT A POLICY DISAGREEMENT: THERE IS NO RELEASE VERB. A lease is
acquired implicitly by `ticket start` and released implicitly by landing. A
worktree that finishes WITHOUT landing -- merged by hand, superseded, abandoned,
or simply done in sequence before a sibling branch continues -- holds its lease
forever, and the only way to break it is to steal the entire ticket. The
consumer's own suggested remedy is the right shape: `frob ticket release
<worktree>` once that worktree's work is merged.

NOTE THE SPECIFIC SHAPE THAT MAKES THIS COMMON RATHER THAN EXOTIC: two branches
sharing ONE ticket IN SEQUENCE. That is a normal workflow (do the shell half,
then the rust half), and it is exactly the case with no non-destructive path
today.

RELATED BUT DISTINCT -- do not merge these:
  - T-3949 / T-3927 are about lease GRANULARITY (whole-file leases serialising
    disjoint edits). This ticket is about lease LIFECYCLE (no way to release
    one). T-3927 already records that the lease has no lifecycle independent of
    ticket state; this is that gap, reported from the field.
  - T-3983 is about a stale worktree capturing ledger WRITES via cwd. Same
    underlying condition -- worktrees outliving their usefulness -- different
    symptom. A release verb would reduce both populations.

WHAT TO DETERMINE FIRST: is the implicit acquire/release pair deliberate? An
explicit release verb introduces a way to release a lease while work is still
live, which is a new footgun. So the release must be SAFE BY CONSTRUCTION, not
merely available: refuse (or loudly warn) when the worktree still has uncommitted
or unlanded work, and say what it found. A release that can silently strand
in-flight work would be worse than today's steal.

PREFER A RELEASE VERB OVER A SCOPE-ONLY STEAL. The consumer offers both. A
scope-only steal still takes something from another holder; a release is the
holder relinquishing. Where the holder is a finished worktree, release is the
honest operation and needs no adjudication of who deserves the lease.

MUST-FIRE FIXTURE: releasing a lease held by a worktree with unlanded work is
refused, naming what it found.
MUST-STAY-QUIET: releasing a lease held by a finished, merged worktree succeeds,
and a sibling worktree can then add scope without stealing the ticket.
THIRD FIXTURE: after release, the original worktree cannot silently continue to
act as the owner.

ACCEPTANCE
- A release path that does not revoke a sibling's ability to close or land.
- Refusal (not just a warning) when the holder still has live work.
- All three fixtures committed.