---
id: T-4002
title: scope --remove in one worktree mirrors to the primary and destroys a sibling
  branch's scope (subtractive mirroring has no guard)
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: T-4050
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_scope.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: null
  new_value: T-4050
  reason: one of five independently-reported defects that are all about what set a
    ticket's scope is computed over (universe, breadth, commit range, propagation);
    parenting them so the denominator is answered once rather than narrowed five conflicting
    ways
  actor: logan
  at: '2026-09-06'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2, 2026-09-06 (filed by them as a second F-217; their
numbering collided, the finding is distinct):

  "T-0190's engine half narrowed scope in .claude/worktrees/t-0190 and the main
   checkout's copy narrowed with it, nearly zeroing the shell half's scope.
   Scope mirroring should be per-branch for a ticket that declares work on two
   branches, or scope --remove should refuse when the removed path is not
   present on the current branch."

THIS IS DATA LOSS ON A SHARED TICKET, not a display problem. One branch's
narrowing propagated to the canonical copy and NEARLY ZEROED the other branch's
declared scope. The shell half did not remove anything, did not consent, and had
no notification -- its scope simply shrank underneath it. Since scope is also the
write lease, the consequence is that the other half loses both its evidence
coverage declaration and its authority to edit the files it is actively working
on.

IT COMPLETES A SET. Three reports, three directions, one cause:
  - T-3958: the ROOT is stale after a worktree close (close is not mirrored).
  - T-3958's F-211 addendum: the WORKTREE is stale while the root is current.
  - This: a worktree write mirrors to the root TOO eagerly and clobbers a
    sibling's state.
So mirroring is simultaneously too weak (close), too weak in the other direction
(stale worktree copies), and too strong (scope --remove). That is not three bugs
with three fixes; it is one missing rule about which store is authoritative for
which mutation, showing three faces. T-3983 (ticket-store WRITES resolving from
cwd) is the fourth face. READ ALL FOUR TOGETHER before designing -- fixing this
one in isolation risks making one of the others worse.

THE ASYMMETRY THAT MAKES REMOVAL SPECIAL, and the reason this is the most
dangerous of the four: an ADDITIVE mirror (scope --add, evidence) is safe to
propagate -- the worst case is a scope wider than one branch needs. A
SUBTRACTIVE mirror destroys another branch's declaration. Additive and
subtractive ledger mutations do not deserve the same propagation rule, and today
they share one.

THE CONSUMER OFFERS TWO REMEDIES; PREFER THE SECOND AS THE IMMEDIATE FIX:
  (a) per-branch scope mirroring for a ticket declaring work on two branches --
      correct but requires the authority model above, so it is the design.
  (b) `scope --remove` refuses when the removed path is NOT PRESENT ON THE
      CURRENT BRANCH -- narrow, mechanical, shippable now, and it directly
      prevents the reported incident: the engine half was removing paths that
      only the shell half's branch had.
Ship (b) while (a) is designed. Say plainly that (b) is a guard, not the fix.

VERIFY FIRST: is scope mirroring deliberately whole-ticket? This repo's land flow
depends on mirroring scope and evidence from worktrees, and the routine
"chore(tickets): mirror scope T-xxxx from worktree" commits prove it is
load-bearing. So do NOT simply stop mirroring removals -- establish what the land
flow needs before changing propagation.

MUST-FIRE FIXTURE: removing a path that exists only on a sibling branch is
refused, naming the branch that declares it.
MUST-STAY-QUIET: a ticket worked on ONE branch can still narrow its own scope
freely -- the common case must not become harder.
THIRD FIXTURE: after a refused removal, both halves' scopes are byte-identical to
before.

ACCEPTANCE
- Guard (b) shipped, with the additive/subtractive distinction stated in code.
- The authority question addressed jointly with T-3958 and T-3983, not
  separately.
- All three fixtures committed.