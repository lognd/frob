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
body_changes:
- mode: set
  reason: 'F-211 is the mirror image of this ticket (worktree stale, root current)
    with the same root cause: two stores and no stated authority rule. Recorded here
    rather than as a duplicate, with the caveat that their cp -r mirroring was unsanctioned
    and only the MASKING half is ours'
  actor: logan
  at: '2026-09-06'
  old_length: 3700
  new_length: 5926
- mode: set
  reason: 'F-236 and F-237 escalate this from a stale-query defect to a workflow blocker:
    a co-located passenger ticket cannot be landed without hand-copying ledger files
    onto main, which is exactly the hand-editing this repo forbids. F-236 also adds
    a third, distinct staleness mechanism (an in-process cache never reread after
    a write)'
  actor: logan
  at: '2026-09-06'
  old_length: 5926
  new_length: 8601
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
## THE MIRROR-IMAGE CASE: F-211, 2026-09-06

Same consumer, same day, same fault line, opposite direction. This ticket records
the ROOT being stale after a worktree close. F-211 records the WORKTREE being
stale while the root is current:

  "T-0181 was mirrored into two worktrees with plain cp -r at different times;
   the main checkout's copy had since gained scope_changes and a body append that
   the earlier mirror did not have, so `frob check --only scope --ticket T-0181`
   on that worktree flagged files as out-of-scope even though the ticket's
   canonical state already covered them. `frob ticket show` against the main
   checkout reported the up-to-date scope, MASKING the staleness until the
   worktree-local check ran."

BE PRECISE ABOUT FAULT: they mirrored with a plain `cp -r`, which is not a
sanctioned operation, so the divergence is partly self-inflicted and this should
NOT be filed as a separate defect. What is genuinely ours is the second half --
the MASKING. Querying from the main checkout returned the canonical state and
gave no indication that the worktree the work was actually happening in held a
different one. The user had no way to see the disagreement; they discovered it as
a confusing scope-gate failure.

WHY IT BELONGS HERE RATHER THAN ON ITS OWN TICKET: both directions have one
cause. There are two stores and no stated rule about which is authoritative for
which operation, so a query answers from whichever one it happens to resolve, and
never says which. That is why remedy (b) on this ticket -- have show/list NAME
the checkout they read -- is worth doing REGARDLESS of how the mirroring question
is settled: it makes both directions visible instead of only fixing one.

THEIR ADDITIONAL ASK, worth folding into the design: a staleness check at
`ticket start` comparing the worktree's ticket-file hash against the tracked
branch's copy. That catches the divergence at the moment work begins rather than
at the moment a gate fails confusingly, and it needs no decision about which
store wins.

ADDITIONAL FIXTURE: a worktree whose ticket copy differs from the tracked
branch's is reported at start, naming both hashes -- not discovered later as an
unexplained scope violation.

## ESCALATION: THIS BLOCKS A WORKFLOW, IT IS NOT A DISPLAY BUG (F-236, F-237)

Two further reports, same day, upgrade this ticket's severity. It is no longer
"a query shows stale state"; it is "a shared-worktree land cannot proceed".

F-236: "T-0203 and T-0197 shared one worktree; after `frob ticket close T-0197`
(ticket.md shows done) the CROSSTICKET check still said T-0197 IN_PROGRESS
across THREE RUNS. The check reads a cached ledger; reread after any ledger
write in the same process tree."

  Note this is a THIRD staleness mechanism, distinct from the two already on this
  ticket. Not root-vs-worktree divergence -- an in-process CACHE not invalidated
  by a write that the same process tree performed. Three runs in a row returned
  the stale answer, so it is not a race; the cache is simply never reread.

F-237: "The land refused 'T-0197 is still open on main' although T-0197 was
closed in the worktree; the coordinator had to COPY THE TICKET FILES ONTO MAIN BY
HAND first."

  That is the operational cost of the unmirrored close, stated plainly. The
  documented remedy for a co-located passenger ticket does not exist, so a human
  hand-copied ledger files into the primary checkout to get a land through. This
  repo has a standing rule that the ledger must never be hand-edited -- so the
  missing mirror forces exactly the operation the rules forbid. That is the
  strongest possible argument that the gap is real and load-bearing.

WHAT THIS CHANGES ABOUT THE FIX. The earlier analysis offered (a) mirror the
close and (b) have queries name the checkout they read, and asked first whether
the close is deliberately unmirrored because a worktree's terminal state should
not publish before its code lands. F-237 answers that question from the field:
for a CO-LOCATED PASSENGER ticket, main genuinely needs the closed state BEFORE
the shared land, so "never mirror a close" cannot be the rule. Their alternative
-- have `land --allow-cross-ticket` CARRY the passenger's close -- is the more
conservative shape and does not require closes to publish speculatively. Weigh
it against (a); either is defensible, but doing nothing is not.

ADD TO THE ACCEPTANCE:
- The in-process cache is reread (or invalidated) after any ledger write in the
  same process tree -- F-236's mechanism, which neither remedy above addresses.
- A co-located passenger ticket can be closed and landed WITHOUT hand-copying
  ledger files into the primary checkout.

ADDITIONAL FIXTURE: two tickets sharing one worktree -- closing the passenger
then landing the driver succeeds with no manual file movement, and CROSSTICKET001
reflects the close on its next run in the same process.
