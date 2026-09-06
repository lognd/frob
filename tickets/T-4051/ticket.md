---
id: T-4051
title: 'F-250: verify dispose performs a disposal then discards it when the batch
  cannot clear, so sequential disposals never converge'
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
- src/frob/app/verify_runner.py
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
Consumer logand.app-v2 F-250, 2026-09-06:

  "Disposing a 4-finding quarantine with four sequential `frob verify dispose
   --file-ticket ...` calls NEVER PERSISTS: each call disposes one finding, then
   `clear_quarantine refused -- 3 finding(s) still undisposed` and THE WHOLE CALL
   EXITS 1 WITH THE DISPOSAL DISCARDED, so the next call sees the same 3 (really
   4) undisposed. Only passing all four --file-ticket flags in ONE call works."

THE COMMAND DOES ITS WORK AND THEN THROWS IT AWAY. Each invocation successfully
disposes a finding, then discovers it cannot ALSO clear the quarantine, treats
that as a failure of the whole invocation, and rolls back the disposal it had
already made. So N sequential calls accomplish nothing, and each one appears to
have done something before undoing it. The user cannot converge by repeating,
which is the natural response.

TWO DEFECTS, AND THE FIRST IS THE REAL ONE:

1. A SUCCESSFUL SUB-OPERATION IS DISCARDED BECAUSE A LATER, DIFFERENT OPERATION
   REFUSED. Disposing a finding and clearing the quarantine are separate acts
   with separate preconditions. Coupling them so the second's refusal voids the
   first makes incremental progress impossible. Either persist per-finding
   disposals independently of whether the batch completes, or -- if the coupling
   is deliberate -- refuse UP FRONT with "all findings must be disposed in one
   invocation" instead of doing work and reverting it. Determine which is
   intended before choosing; the current behaviour is neither.

   NOTE THE T-4022 RELATIONSHIP: that ticket is about a KILLED ledger verb
   leaving a partial write. This is the mirror image -- a COMPLETED sub-write
   deliberately discarded. Both are "the ledger's transaction boundary does not
   match the user's unit of work". Read together.

2. THE REAL ERROR IS HIDDEN BY OUR OWN WARNING. Their words: "the FAST_EXIT1
   warning hides the real error line unless you scroll". FAST_EXIT1 exists to
   catch a fast failure being mistaken for a fast success -- a genuinely good
   diagnostic -- but it PRINTS LAST, pushing the actual cause off the bottom of
   the output. So the mechanism built to prevent misreading a failure is what
   makes this failure hard to read.

   I HIT THIS EXACT TRAP THREE TIMES TODAY from the other side: reading a tail
   and missing the real error above it (an argparse rejection whose echo looked
   like output, a truncated offender list, and a facet line I concluded was
   ignored). My rule was "never diagnose from a tail" -- but the tool should not
   make the tail misleading in the first place. FAST_EXIT1 should either repeat
   the error it is warning about, or print BEFORE it, so the last thing on screen
   is the cause and not the meta-commentary.

ALSO REPORTED, worth verifying: `--reason` became mandatory on this verb and was
not in earlier sessions. If that changed, it is a CLI break; confirm whether it
was intended and whether anything documents it.

MUST-FIRE FIXTURE: disposing findings one at a time converges -- four sequential
single-finding calls leave four findings disposed.
MUST-STAY-QUIET: a quarantine with undisposed findings still refuses to CLEAR.
THIRD FIXTURE: a refusal's cause is the last thing printed, or is repeated by
FAST_EXIT1 rather than buried above it.

ACCEPTANCE
- Whether the dispose/clear coupling is deliberate, answered before the fix.
- Per-finding disposals persist, or an up-front refusal that never does
  discardable work.
- FAST_EXIT1 no longer displaces the error it is commenting on.
- All three fixtures committed.