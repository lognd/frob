---
id: T-3852
title: 'a container ticket cannot close: MissingEvidence demands pytest ids a story
  or epic structurally cannot own'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
Reported as logand.app-v2 FROBLEMS F-040. This repo has the SAME defect live in
its own fleet right now, so it reproduces in two repos independently.

THE REPORT: `frob ticket close T-0006` (tier=story, owns only its L5 doc) ->
MissingEvidence. The reporter had to start it, bind one of its LEAVES' pytest
ids as the story's own "evidence", write a done report, then close. Their words:
"ceremony that says nothing new". It blocks `doable` for every dependent story
until a coordinator performs the dance.

LOCAL CORROBORATION, measured 2026-09-05 via scripts/fleet_status.py on frob:

    NEEDS CLOSE (1):
      T-2982 tier=epic priority=high state=queued age=10d (threshold 7d) --
      every child ticket is terminal (done/dropped, active ledger + archive)
      but T-2982 itself is still open; write a rollup Done report and close it

Same shape one tier up. A container ticket owns no code, so it can produce no
pytest evidence of its own, but close demands evidence anyway.

WHY BINDING A LEAF'S EVIDENCE IS THE WRONG WORKAROUND, not just an annoying
one. Evidence is meant to be a fail-then-pass repro for the change the ticket
made. A story made no change; its leaves did. Citing a leaf's node id on the
parent creates a second, false owner for that test and dilutes what evidence
means -- and this repo has a documented history of tickets reaching `state:
done` with nothing real behind them, which is exactly what the evidence
requirement exists to prevent. Making the requirement satisfiable by borrowing
is worse than making it inapplicable.

THE TENSION THIS TICKET MUST RESOLVE, AND IT IS THE WHOLE DESIGN QUESTION. The
reporter asks for auto-close when every child is done. DO NOT IMPLEMENT THAT
BLINDLY. Measured counter-example from this repo, recorded on T-1382:

    fleet_status reported T-1382 as NEEDS CLOSE -- every child terminal. Its
    five real children (T-2240/2241/2242/2244/2245) had all wired Makefile
    targets to call frob subcommands. NONE of them scoped the Makefile for
    deletion, which is the work the epic actually exists to do. The root
    Makefile was still 574 lines, unchanged. A rollup would have reported a
    Makefile-decoupling epic as done with the Makefile undeleted.

So "all children terminal" does NOT imply "the parent's work is done" -- it can
equally mean the decomposition never covered the real work. An auto-close would
have converted that gap into a silent false completion, which is the dominant
defect shape in this codebase.

WHAT TO BUILD, therefore, is a narrower thing than the report asks for:
  1. A container-tier ticket (story/epic, or more precisely one with children
     and no scope of its own) must be CLOSEABLE WITHOUT pytest evidence. Its
     done report is a rollup: what the children delivered, and the statement
     that the parent's stated goal is met. Decide the precise predicate --
     "tier in (story, epic)" is the crude version; "has children and declares
     no scope" is probably the honest one, since a story that DOES own code
     should still owe evidence for it. State which and why.
  2. It must still require an EXPLICIT close with a real rollup report. Not
     automatic. The human or agent closing it asserts the goal is met; that
     assertion is the thing T-1382 shows cannot be inferred from child states.
  3. `blocked_by` a container should resolve when the container closes -- which
     step 1 makes reachable. Do not separately teach `blocked_by` to look
     through to children; that would re-introduce the same inference.
  4. The MissingEvidence refusal on a container must SAY all this. Today it
     names a requirement the ticket structurally cannot satisfy, with no remedy
     -- the same unwaivable-by-construction shape as T-3843.

DO NOT relax the evidence requirement for leaf tickets. That requirement is
load-bearing and is the reason done-reports are trustworthy here.

MUST-FIRE FIXTURES:
  - a LEAF ticket with no evidence still refuses to close
  - a container whose children are NOT all terminal still refuses to close
MUST-STAY-QUIET FIXTURES:
  - a container with all children terminal closes with a rollup report and no
    pytest evidence
  - a ticket blocked_by that container becomes doable once it closes
  - a container that owns its own scope still owes evidence for that scope

ACCEPTANCE
- The container predicate chosen and justified (tier-based vs scope-based).
- Close remains EXPLICIT; no auto-close on child terminality, with T-1382 cited
  as the reason in the code comment so this is not re-litigated.
- The refusal message rewritten to name the rollup path.
- All fixtures committed.
- T-2982 closed as the first real exercise of the new path, or a statement of
  why it should not be.
