---
id: T-4120
title: a generated artifact leased by one ticket blocks the mandatory regeneration
  a sibling must perform, and per-worktree regeneration is wrong even when it succeeds
state: queued
kind: bug
origin: agent
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
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given two sibling tickets that both must regenerate the same declared generated
    artifact, when each lands, then both land and the final artifact reflects both
    tickets' source contributions
  evidence: []
- text: given a hand-written file contended by two tickets, when the second attempts
    to take it, then the ordinary lease conflict is still raised
  evidence: []
- text: given a worktree-local regeneration of a declared artifact, when the ticket
    lands, then that copy is discarded and the landed artifact matches a regeneration
    from the merged tree
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A GENERATED FILE HELD BY ONE TICKET'S LEASE BLOCKS THE MANDATORY REGENERATION A
SIBLING TICKET IS REQUIRED TO PERFORM. Reported as logand.app-v2 F-309, on a
generated model artifact contended between two sibling tickets. The consumer
marks it a REPEAT of an earlier report of the same shape, and the coordinator
had to regenerate the artifact by hand on the main branch after the land to
unwedge it.

THE CONTRADICTION IS STRUCTURAL, AND IT IS A NO-EXIT: the tooling REQUIRES a
ticket to regenerate a derived artifact as part of its work, and the lease system
FORBIDS it because a sibling ticket touched the same file. There is no action
available to the second agent that satisfies both rules. That makes it the
thirteenth instance of the no-exit class -- a rule demanding something the
subject structurally cannot provide -- and the second time this exact instance
has been reported.

THE CONSUMER NAMES BOTH VIABLE FIXES and they are not equivalent. Decide between
them deliberately rather than picking the easier one:

  OPTION A, LEASE-EXEMPT THE GENERATED ARTIFACTS. Simple, but it means two agents
  can regenerate concurrently and the last writer wins silently -- the file is
  derived, so a lost write is invisible until the next reader disagrees with the
  source. Exempting a file from leases does not make concurrent writes safe; it
  makes them unpoliced.

  OPTION B, REGENERATE AT LAND TIME. The land already has exclusive access, it
  already composes the final tree, and it is the one moment where regeneration
  from the merged sources is actually correct. A regeneration performed inside
  either ticket's worktree is derived from THAT worktree's partial view, so even
  with no lease conflict it can produce an artifact that matches neither final
  state.

OPTION B IS ALMOST CERTAINLY RIGHT, and the second paragraph is the argument: a
generated file edited in a worktree is a derived artifact computed from an
incomplete input. The lease conflict is the visible symptom; the invisible defect
is that per-worktree regeneration of a shared derived artifact is WRONG EVEN WHEN
IT SUCCEEDS. Two agents each regenerating from their own partial view produce two
different correct-looking files, and whichever lands second silently discards the
other's source contribution.

THERE IS ALREADY PRECEDENT IN THIS REPO for exactly this treatment: the changelog
is land-owned, and worktree edits to it are deliberately discarded by the
release-artifact reset. That mechanism exists, it is understood, and a generated
model artifact is the same kind of object. Reuse the pattern rather than
inventing a second one -- and if it cannot be reused, say why in the fix.

WHAT TO DO
  1. Establish how a generated artifact is DECLARED as generated. This is the
     part with no existing answer, and everything else depends on it. If there is
     no declaration today, the fix begins there rather than with the lease.
  2. Make land regenerate declared artifacts from the merged tree, and make a
     worktree edit to one a no-op rather than an error -- an agent that
     regenerates locally to check its work should not be punished for it.
  3. Only then decide whether the lease should still cover them. With land-time
     regeneration in place the lease may be moot; verify that rather than
     assuming it.
  4. Report how many generated artifacts exist in this repo and in the consumer's.
     A fix that handles one file and not the class will be reported a third time.

MUST-FIRE FIXTURE:   two sibling tickets whose work both require regenerating the
                     same declared artifact can each land, and the final artifact
                     reflects BOTH tickets' source contributions.
MUST-STAY-QUIET:     a hand-written file contended by two tickets still raises the
                     ordinary lease conflict -- this must not become a general
                     lease escape hatch.
THIRD FIXTURE:       a worktree-local regeneration is discarded at land rather
                     than refused, and the landed artifact matches a regeneration
                     from the merged tree.

ACCEPTANCE
- Generated artifacts are declared explicitly, not inferred from a path pattern.
- Land regenerates them from the merged tree.
- The lease question is decided after that, with the reasoning recorded.
- The full population of generated artifacts is counted and reported.
- All three fixtures committed.
