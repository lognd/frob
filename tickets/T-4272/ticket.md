---
id: T-4272
title: 'multi-contributor epic claims: a remote collaborator claims an epic, everyone
  else sees it advisorily, and an abandoned claim expires without starving the ticket'
state: queued
kind: feature
origin: human
created: '2026-09-07'
priority: medium
parent: null
tier: epic
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
acceptance:
- text: given a claimed epic and a collaborator with no network access, when they
    run any frob verb, then nothing is refused and the claim view reports its own
    age rather than appearing empty
  evidence: []
- text: given a claim whose holder has produced no evidence of work for the configured
    duration, when another contributor claims it, then the claim transfers and the
    steal is recorded with the previous holder's last evidence
  evidence: []
- text: given two contributors claiming different epics at the same time, when both
    publish, then neither publish conflicts with the other and no shared record is
    rewritten
  evidence: []
- text: given a ticket whose scope overlaps a claimed epic's open leaves, when work
    on it is started, then the overlap is reported using the existing scope-collision
    machinery rather than a second implementation
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MULTI-CONTRIBUTOR EPIC CLAIMS: LET A REMOTE COLLABORATOR CLAIM AN EPIC, LET
EVERYONE ELSE SEE IT, AND LET AN ABANDONED CLAIM EXPIRE. Owner request, scheduled
AFTER the alpha publish. This ticket is the design record; leaves come later.

THE CONSTRAINTS THE OWNER SET, WHICH ARE THE HARD PART. The check must not run on
every invocation, because that would put the network in the path of routine work.
It must never be load-bearing: frob works offline today and must keep working
offline, with no verb blocked by an unreachable remote. And an unworked claim must
not starve the ticket it holds.

THE CENTRAL OBSERVATION: THE LEDGER IS ALREADY DISTRIBUTED. Tickets live in git.
A claim does not need a server, a database, or an account system -- it needs a
place two people's repositories can both see. Git already provides one, and the
project already pushes and fetches it.

THE RECOMMENDED SHAPE: ONE REF PER CLAIM, NOT ONE FILE LISTING CLAIMS. Publish a
claim as its own ref under a dedicated namespace, named for the ticket it claims,
carrying the claimant, the claim time, the last heartbeat, and the intended
duration. One ref per ticket gives mutual exclusion for free: a claim is a
compare-and-swap push that fails if someone already holds it, and two people
claiming different epics never touch the same object, so there is nothing to
merge.

DO NOT IMPLEMENT THIS AS A SINGLE SHARED FILE OF ALL CLAIMS. This repository
already carries a defect of exactly that shape, where one record holds one entry
in a world that produces several, so the file names whichever writer went last and
a reader cannot tell a live entry from a finished one. A per-claim ref cannot
develop that failure.

LIVENESS MUST BE DEFINED BY WORK, NOT BY A HEARTBEAT ALONE. This project has
already been bitten by the opposite: a daemon polled faithfully for nineteen
hours while doing nothing useful, and any heartbeat-based check would have called
it healthy the whole time. A claim should be considered alive on evidence of
progress -- commits on the claimant's branch, a landed leaf, a ticket transition
-- and a bare periodic refresh should not by itself hold an epic indefinitely.
Expect to combine the two: a heartbeat proves the person still exists, evidence of
work proves the claim is still doing something.

EXPIRY MUST BE OBSERVABLE AND STEALING MUST BE AUDITABLE. When a claim goes
stale, anyone may take it, and taking it should be recorded rather than silent:
who took it, when, and what the previous claim's last evidence was. A silent steal
turns a coordination tool into a source of surprise merges.

THE NETWORK RULES, STATED AS REQUIREMENTS RATHER THAN INTENTIONS.
  Refresh opportunistically, on verbs where the person is already coordinating --
  starting work, landing, asking what is available -- and never on the checking
  path.
  Bound every remote call by a short timeout and fall back to the cached view
  without complaint.
  Cache the last fetched view with the time it was fetched.
  DISPLAY THAT AGE. An empty claim set because nobody has claimed anything and an
  empty claim set because the network was unreachable must never look identical.
  That is this project's dominant defect class and it would be inexcusable to
  introduce a fresh instance of it here.
  Never refuse a verb because a claim could not be fetched.

WHAT A CLAIM SHOULD DO WHEN IT IS SEEN. Advisory pressure, escalating with how
much the action costs to undo. Starting work on a claimed epic, or on a ticket
whose scope overlaps a claimed epic's open leaves, warns and asks for an explicit
acknowledgement that records why. Landing is the point where firmness is
reasonable, because landing already requires the network. Reading, checking, and
searching are never affected.

REUSE, DO NOT REBUILD. The overlap computation already exists: filing a ticket
already reports which other tickets' scopes it collides with. An epic's claimed
surface is the union of its open leaves' scopes, which makes the file-level
question a reuse of that same machinery rather than a new one. The existing
worktree-keyed lease layer stays exactly as it is and must NOT be conflated with
this: a lease is mutual exclusion inside one checkout, a claim is coordination
between people, and they answer different questions on different timescales.

OPEN QUESTIONS TO SETTLE BEFORE BUILDING.
  Whether a claim requires push access to the main repository, which decides
  whether outside contributors can claim at all or only collaborators can.
  How clock skew between contributors is handled, since expiry compares
  timestamps written on different machines; prefer generous durations and
  commit-based evidence over precise wall-clock arithmetic.
  Whether an epic claim implies its leaves are claimed, or whether leaves are
  claimed individually, and what happens when a second person wants one leaf of a
  claimed epic.
  What the view looks like for someone who has never fetched: the honest answer
  is "unknown", and the design must have a word for that state.
