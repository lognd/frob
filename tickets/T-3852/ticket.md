---
id: T-3852
title: 'a container ticket cannot close: MissingEvidence demands pytest ids a story
  or epic structurally cannot own'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: critical
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
triage_changes:
- field: priority
  old_value: high
  new_value: critical
  reason: 'no exit state: a container ticket cannot be closed by any path, and the
    only way to keep dependents flowing is to park it in-progress on main'
  actor: logan
  at: '2026-09-05'
body_changes:
- mode: append
  reason: 'reporter addendum: the leaf-evidence workaround also fails with EvidenceScopeUnbound,
    so a container is unclosable by any path; plus blocked_by appears to resolve on
    start'
  actor: logan
  at: '2026-09-05'
  old_length: 4744
  new_length: 7555
- mode: append
  reason: third sighting (stpone F-019, epic tier); the leaf-evidence workaround succeeds
    or fails depending on container scope breadth, which rewards over-broad scope
  actor: logan
  at: '2026-09-05'
  old_length: 7555
  new_length: 10247
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



ADDENDUM FROM THE REPORTER, 2026-09-05. Two facts that change this ticket.

FACT 1 -- THE WORKAROUND DOES NOT EXIST. I described binding a leaf's evidence
as an available-but-wrong escape. It is not available:

    "with leaf evidence bound the close then fails EvidenceScopeUnbound
     (the story's scope is only its L5 doc)"

So the sequence is: close refuses with MissingEvidence; the operator borrows a
leaf's pytest id to satisfy it; close then refuses with EvidenceScopeUnbound,
because that test file is not in the story's scope. A container ticket is
UNCLOSEABLE BY ANY PATH. Two gates each enforcing a reasonable rule compose into
a state with no exit -- the same shape as T-3843's unwaivable DOC006, and it
means the priority here is higher than "friction".

Widening the story's scope to cover a leaf's test file would be the next
workaround, and it must NOT be recommended: scope is also the write lease, so
that hands the parent a lease over its child's files and creates exactly the
cross-ticket contention the lease system exists to prevent.

FACT 2 -- AND THIS ONE IS ITS OWN QUESTION. The reporter's coping strategy:

    "The dependent stories became doable anyway once the story was STARTED, so
     I left T-0006/T-0010 in-progress on main."

So `blocked_by` resolves when the blocker is STARTED, not when it is DONE.
Measure and confirm that before acting on it; if true, decide explicitly whether
it is intended:
  - If intended, the dependency is "work has begun", which is a much weaker
    guarantee than the name suggests, and the docs should say so plainly.
  - If unintended, dependents are being released early, and every ticket that
    ever unblocked this way did so on a premise that had not been met.
Either way the reporter's workaround leaves container tickets PERMANENTLY
in-progress on main to keep their dependents flowing. That is ledger corruption
adopted out of necessity, and it will read to any later audit as abandoned work.
It also means the NEEDS CLOSE rot signal cannot distinguish "container waiting
on a rollup" from "container deliberately parked to unblock dependents".

REVISED PRIORITY. This is not friction. A container ticket cannot be closed, and
the only way to keep dependent work moving is to leave it permanently
in-progress. Fixing the close path (the main body above) also fixes the
incentive to park them.

ADDITIONAL FIXTURE REQUIRED:
  - a container whose scope does not cover a leaf's test file can still close
    via the rollup path, WITHOUT widening its scope and WITHOUT borrowing
    evidence.

ADDITIONAL ACCEPTANCE:
  - The blocked_by-resolves-on-start behaviour measured and reported, with a
    stated verdict on whether it is intended. Do not change it under this
    ticket if it turns out to be deliberate -- file it separately.



THIRD INDEPENDENT SIGHTING, 2026-09-05: stpone FROBLEMS F-019, "An epic cannot
close on its own terms". `frob ticket close T-0001` (tier=epic, every leaf done)
-> MissingEvidence. They cross-referenced this ticket themselves.

That makes three repos plus frob's own fleet:
    logand.app-v2 F-040   story tier
    stpone        F-019   epic tier
    frob          T-2982  epic, NEEDS CLOSE, 10d past threshold

ONE NEW FACT, AND IT CHANGES THE PICTURE. In stpone the leaf-evidence workaround
WORKED: "Binding one evidence node id from each leaf to the epic was accepted
and the close then succeeded." In logand.app-v2 the same workaround FAILED with
EvidenceScopeUnbound, because that story's scope was only its own L5 doc.

So the escape is available or not depending on how broad the container's scope
happens to be. That is worse than a uniform refusal, for two reasons:

  1. It is inconsistent in a way nobody can predict from the error message. Two
     operators hitting the same MissingEvidence get different outcomes from the
     same remedy, decided by a scope declaration that has nothing to do with
     evidence.
  2. Where it DOES work, it works by making the container's scope broad enough
     to cover a leaf's test file -- which means the workaround's availability is
     proportional to how over-broad the container's scope already is. frob is
     effectively rewarding the wider scope declaration. Since scope is also the
     write lease, that is the opposite of the incentive we want, and it is the
     same hazard flagged earlier in this ticket against widening scope
     deliberately.

stpone also states the expected behaviour slightly differently from
logand.app-v2, and the difference is worth keeping: "an epic/story closes when
all children are done (OR WITH `--evidence-cmd` PROOF THAT THEY ARE)". That
second clause is a better answer than either auto-close or a bare rollup: it
keeps close explicit and evidenced, while letting the evidence be a command that
demonstrates child terminality rather than a pytest node id the container cannot
own. `--evidence-cmd` already exists for docs-kind tickets, so the mechanism is
present -- check whether extending it to containers is cheaper than a new
rollup path, and say which you chose.

This does not change the ticket's core requirement (close stays EXPLICIT, no
auto-close on child terminality, per the T-1382 counter-example above). It adds:
the fix must produce the SAME outcome regardless of the container's scope
breadth, and must not leave the leaf-evidence borrow as a working alternative
path -- if borrowing is wrong, it should stop working everywhere, not only where
scope happens to be narrow.
