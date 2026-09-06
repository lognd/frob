---
id: T-3958
title: 'F-191: ticket show/list read a stale root mirror after a worktree close, corrupting
  the coordinator audit surface'
state: queued
kind: bug
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
- src/frob/app/ticket_runner/_query.py
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
Consumer logand.app-v2 F-191, 2026-09-06:

  "After a successful close in .claude/worktrees/t-0173, `frob ticket show
   T-0173` from the main checkout still said in-progress/UNBOUND; only
   `--path <worktree>` showed the truth. Either the close should mirror the
   state (as scope/evidence do) or `show` should say which checkout's ledger it
   read."

CONFIRMED INDEPENDENTLY IN THIS REPO, SAME DAY, and it produced a wrong
conclusion by a coordinator -- me. An implementer reported "T-3941 is closed",
which was TRUE in its worktree. From the shared root, tickets/T-3941/ticket.md
read state: in-progress. I read that as the agent overclaiming. It was not; the
root mirror was stale exactly as this report describes.

WHY THIS IS WORSE THAN A DISPLAY BUG. The root ledger is what a COORDINATOR reads
to audit what agents have actually done. A stale mirror means the audit surface
disagrees with reality in the direction that manufactures false accusations of
incomplete work -- and, symmetrically, could hide a real gap. It corrupts the one
view used to supervise a fleet.

NOTE THE ASYMMETRY, which is the actual defect and the strongest evidence it is a
bug rather than a design choice: SCOPE AND EVIDENCE ARE MIRRORED FROM THE
WORKTREE ALREADY. This repo's own history is full of "chore(tickets): mirror
scope T-xxxx from worktree" commits. So the mirroring mechanism exists, is
routine, and is simply not applied to the close transition. That inconsistency is
the ticket: two kinds of ledger mutation, one mirrored and one not, with nothing
saying which is which.

THE TWO REMEDIES ARE NOT EQUIVALENT -- do not treat the consumer's "either/or" as
a free choice:
  (a) MIRROR THE CLOSE, matching scope and evidence. This makes the root ledger
      correct, which is what every reader already assumes.
  (b) HAVE `show`/`list` NAME THE CHECKOUT they read. This makes the staleness
      visible but leaves it present.
PREFER (a), and note that (b) is worth doing ANYWAY and independently: a query
that silently reads one of several possible ledgers should say which, whether or
not it is stale. (b) is a small, safe change that reduces the cost of every
future instance of this class.

WHAT TO DETERMINE FIRST: is the close deliberately NOT mirrored? There may be a
real reason -- a close is a terminal transition and mirroring it from a worktree
that has not landed could publish a "done" state for code that is not on main,
which would be a worse bug than the one being fixed. IF THAT IS THE REASON, then
(a) is wrong and the answer is (b) plus a message stating that the root cannot
know the worktree's terminal state until the land. Establish this before
implementing; the two paths have opposite shapes.

THE VERIFICATION LESSON WORTH ENCODING SOMEWHERE, because it is what saved the
conclusion here: my "not landed" call was right despite the stale ledger, because
I checked GIT facts (`git merge-base --is-ancestor <sha> main`, and grepping
`git show main:<file>` for the changed content) rather than the ledger's state
field. Ledger state is a claim; ancestry and file content are facts. Any tooling
or guidance for verifying agent work should point at git, not at `ticket show`.

MUST-FIRE FIXTURE: a close performed in a worktree is visible (or explicitly
reported as unknowable) from the primary checkout.
MUST-STAY-QUIET: a ticket genuinely still in progress does not read as done from
either checkout.
THIRD FIXTURE: `show`/`list` name the ledger they read.

ACCEPTANCE
- The "is the close deliberately unmirrored" question answered before a fix is
  chosen, with the reason.
- Root and worktree agree, or the disagreement is stated in the output.
- All three fixtures committed.