---
id: T-4022
title: 'F-235: a killed ledger verb leaves its partial write, so lock-wait kills produce
  duplicate entries'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: T-3928
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: null
  new_value: T-3928
  reason: 'pass2 backlog org: theme bucket consumer-audit'
  actor: logan
  at: '2026-09-11'
body_changes:
- mode: set
  reason: 'second independent consumer report of the same mechanism (logand.app-v2
    F-313), which usefully narrows it: the orphaned LOCK reclamation already works,
    only the partial LEDGER write is left behind. Also records that the residue dirties
    the shared root and so converts one killed land into a fleet-wide land stall'
  actor: logan
  at: '2026-09-06'
  old_length: 3900
  new_length: 5660
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2 F-235, 2026-09-06:

  "T-0200's agent killed three 'stuck' accepts (they were waiting on the lock
   held by orphaned scope processes, F-209/F-138) and ended up with three
   duplicate acceptance entries to remove. Ledger writes should be atomic with
   the lock (write-then-unlock, never observable half-done) and `accept` should
   refuse an identical criterion text."

THIS COMPLETES A CAUSAL CHAIN THAT HAS NOW BITTEN AT LEAST THREE PARTIES,
INCLUDING ME. Read the three findings together, because fixing any one alone
leaves the failure reachable:

  1. A ledger verb runs for minutes IN SILENCE (T-3993 / F-209 / F-138). Nothing
     reports what it is doing or that it is waiting on a lock.
  2. A human, agent, or harness therefore cannot distinguish "slow" from "hung",
     and KILLS IT. The consumer killed three. I killed two `frob ticket new`
     calls myself in this session, at 300s and at 900s.
  3. THE KILL LANDS MID-WRITE and the ledger keeps the partial effect. Here:
     three duplicate acceptance criteria, requiring manual removal.

So silence produces kills, and non-idempotency turns kills into corruption. The
observability fix (T-3993) reduces how often step 2 happens; ONLY this ticket
prevents step 3 from damaging the ledger when it does. Both are needed -- do not
let either be closed as covering the other.

THE TWO ASKS ARE DIFFERENT IN KIND AND BOTH ARE RIGHT:

  A. ATOMICITY -- "write-then-unlock, never observable half-done". This is the
     real fix. A ledger mutation should either be fully applied or not applied,
     with no window in which a SIGTERM leaves half of it. VERIFY WHAT THE WRITE
     PATH ACTUALLY DOES before designing: if it already writes to a temp file and
     renames, the window may be elsewhere (the in-memory model, the auto-commit,
     or a multi-step sequence that is individually atomic but not collectively
     so). A multi-step sequence with atomic steps is NOT an atomic operation --
     that distinction is likely the whole bug.
  B. `accept` SHOULD REFUSE AN IDENTICAL CRITERION TEXT. This is a cheap
     independent guard and worth doing regardless of (A): duplicate acceptance
     criteria are almost never intended, and refusing them makes the retry of a
     killed command safe by construction rather than by luck. It also makes the
     verb IDEMPOTENT for the common case, which is what the ticket title asks
     for.

WHAT I VERIFIED ON OUR SIDE, and it narrows the blast radius usefully: after both
of my killed `ticket new` calls I checked `git status --porcelain` on the shared
root and it was CLEAN both times -- no untracked ticket directory, no modified
ledger. So `ticket new` appears not to leave the residue this repo has seen
before from killed retry loops. That is one verb; it says nothing about `accept`,
`scope`, `evidence` or `body`. ENUMERATE WHICH LEDGER VERBS ARE SAFE TO KILL and
report the list -- the answer is operationally useful immediately, before any fix
lands, because agents will keep killing slow commands until T-3993 is done.

DO NOT fix this by making the verbs uninterruptible or by trapping SIGTERM to
finish the write. A command that ignores a kill is worse than one that leaves a
duplicate; the goal is that an interrupted write leaves NOTHING, not that it
cannot be interrupted.

MUST-FIRE FIXTURE: a second `accept` with identical criterion text is refused.
MUST-STAY-QUIET: a genuinely different criterion is still appended.
THIRD FIXTURE: a ledger write interrupted (SIGTERM) between its steps leaves the
ledger byte-identical to before -- the atomicity claim, made checkable rather
than asserted.

ACCEPTANCE
- What the write path does today, measured, before choosing the atomicity fix.
- Identical-criterion refusal shipped (independently useful).
- A stated list of which ledger verbs are currently safe to kill.
- All three fixtures committed.
SECOND CONSUMER REPORT, WITH THE RESIDUE ENUMERATED. logand.app-v2 F-313, after
an interrupted land: main was left carrying an UNTRACKED ticket directory -- a
sweep ticket the land was in the middle of filing -- plus both the land lock and
the ledger lock. Their observation splits the failure cleanly, and the split is
the useful part:

    frob reclaims the orphaned LOCKS itself. It does not clean up the
    half-filed TICKET, which had to be removed by hand.

So the lock half of the recovery is already built and works; the ledger half is
missing. That narrows this ticket considerably -- the fix is not a new recovery
mechanism, it is extending the existing orphan reclamation to cover a partial
ledger write.

WHY THE LEFTOVER DIRECTORY IS WORSE THAN UNTIDY, and the reason to prioritise
this above its apparent severity: an untracked directory under the ledger path
makes the shared checkout DIRTY. A dirty main blocks every other agent's land.
So a single killed land does not just fail itself -- it silently converts into a
fleet-wide stall that presents as unrelated agents parking on a monitor, with no
message anywhere naming the real cause. This repo has hit that exact chain
before from a different source (a killed ticket-creation loop leaving an
untracked ticket dir), which is corroborating evidence that the residue shape,
not the specific verb, is what does the damage.

NOTE FOR THE FIX: the half-filed ticket here was a SWEEP ticket the land filed
on its own initiative, not work the user asked for. That matters twice over --
it means the residue can appear on a land the operator never associated with
ticket creation, and it means the recovery must not assume the leftover
directory corresponds to anything the operator knows about.
