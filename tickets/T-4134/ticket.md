---
id: T-4134
title: frob ticket new prints its success line and then runs three unbounded analyses,
  keeping the process alive for tens of minutes after the ticket exists in git
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_new.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'records first-party evidence captured while filing this ticket: the advisory
    graph build contended on the shared cache lock for 30s and gave up AFTER the ticket
    was already created and committed, demonstrating the mechanism and showing the
    cost is superlinear under fleet load rather than merely slow'
  actor: logan
  at: '2026-09-07'
  old_length: 4661
  new_length: 6630
- mode: set
  reason: 'widens this ticket from one verb to the ledger verb family on a third report:
    accept has now blown both a 60s and a 600s budget. Adds the new fact that the
    stall prints nothing at all, so a caller cannot distinguish lock contention from
    unbounded analysis from a wedge, and flags F-329''s partial-result half as a correctness
    claim that must not be lost inside a latency ticket'
  actor: logan
  at: '2026-09-07'
  old_length: 6630
  new_length: 9222
designated_repro_test: null
acceptance:
- text: given a repository with a large open ticket queue, when a ticket is filed,
    then the command returns within a bounded time and leaves no process behind
  evidence: []
- text: given an ordinary filing, when it completes, then the scope-closure, overlap
    and body-similarity warnings are still emitted
  evidence: []
- text: given an analysis truncated by its bound, when the warnings are printed, then
    the output states that it was truncated rather than appearing clean
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`frob ticket new` ANNOUNCES THE TICKET AND THEN KEEPS WORKING FOR TENS OF
MINUTES. Reported as logand.app-v2 F-337: two filing processes were still alive
26 and 45 minutes after their tickets existed on disk AND in git. Other ticket
verbs kept working throughout, so nothing was holding a lock -- the processes
were simply still running. The reporter also notes this happened while this
repo's own agent fleet was loading the same machine, which matters (see below).

I LOCATED THE MECHANISM IN OUR CODE AND IT MATCHES THE REPORT EXACTLY.
`_emit_new_ticket_side_effects` runs three analyses in sequence:

    _emit_scope_closure_warnings(... _scope_closure_warnings(root, scope))
    _emit_scope_overlap_warnings(root, id, scope)
    _emit_body_similarity_warnings(root, id, body)

The first builds the obligation graph to compute doc/code edge closure over every
symbol in every scoped file. The second compares the new scope against every open
ticket's scope. The third compares the new body against every other ticket's
body. None is bounded, and all three scale with a queue that is now past four
hundred open tickets.

THE ORDERING IS THE PART THAT MAKES IT LOOK LIKE A HANG, and it is visible in
every filing this repo has done today. The output is always:

    created T-XXXX: <title>
    WARNING: ticket new T-XXXX: scope closure: ...
    WARNING: ticket new: T-XXXX: scope overlaps T-YYYY ...

The success line prints FIRST. So from the caller's side the ticket is created,
the id is known, the work is announced -- and then the process sits there for
minutes doing advisory analysis whose output the caller has, in practice, already
acted on. A caller with a timeout kills it; a caller without one waits; an
agent harness backgrounds it and reports the filing as still running. All three
are the same underlying problem: MANDATORY UNBOUNDED WORK AFTER THE ANNOUNCED
COMPLETION POINT.

THIS COMPOUNDS WITH A DEFECT ALREADY FILED, and the two should be read together
though fixed separately. T-4127 records that this same closure computation
EXPLODES on hub files -- 140, 345 and 71 warnings in three independent
measurements. So the analysis that makes filing slow is also the analysis whose
output is mostly noise on exactly the files where it costs the most. Neither
ticket is a reason to delete the check; together they are a strong reason to
bound it.

SECOND-ORDER EFFECT WORTH RECORDING: the reporter is on the same machine as this
repo's agent fleet, and observed this while several of our checks were running.
Our own fleet guidance already caps concurrency on measured swap pressure. A
filing verb that holds a process for 45 minutes turns every ticket a consumer
files into a long-lived resident, which pushes the shared machine further into
the pressure our own guidance is trying to avoid. The cost is not local to the
caller.

WHAT TO DO -- and the ordering here is the fix, not just an optimisation:
  1. Move the three analyses BEFORE the success line, or after it but explicitly
     detached, so the announced completion point is the real one. A caller must
     never be told the work is done while mandatory work remains.
  2. Bound each analysis. A cap on symbols examined, tickets compared, or wall
     time, with a message saying the analysis was truncated -- truncated must be
     visibly different from clean, or this becomes a silent zero.
  3. Provide a way to skip them for a caller that does not want advisory output.
     Batch filing (this repo files many tickets in a row) pays the full cost
     every time for warnings nobody reads until later.
  4. Measure the three separately before optimising. They have different shapes
     -- graph build, scope comparison, text comparison -- and the report does not
     say which dominates. Do not assume it is the graph.

MUST-FIRE FIXTURE:   filing a ticket in a repo with a large open queue returns
                     within a bounded time, and no process outlives the command.
MUST-STAY-QUIET:     the closure, overlap and similarity warnings are still
                     emitted for an ordinary filing -- this bounds them, it does
                     not remove them.
THIRD FIXTURE:       when an analysis is truncated by its bound, the output says
                     so explicitly rather than printing a clean-looking result.

ACCEPTANCE
- The success line is not printed while mandatory work remains outstanding.
- Each of the three analyses is bounded, with truncation visible in the output.
- A documented way to skip the advisory analyses exists.
- The three costs measured separately and the numbers recorded on this ticket.
- All three fixtures committed.

FIRST-PARTY EVIDENCE, OBSERVED WHILE FILING THIS VERY TICKET. The filing command
that created this ticket emitted, in this order:

    WARNING: cache: store_file_data(...) hit a stale/corrupt connection,
             reopening ... and retrying (attempt 1/3): database disk image is
             malformed
    ERROR:   cache: store_file_data(...) still locked after 30s, giving up
    ERROR:   build_graph: cache lock never released: database is locked

The ticket WAS created and committed. What failed was the post-announcement
advisory analysis -- the graph build behind the scope-closure warnings -- because
three agents were running checks against the same cache at the same time.

THAT IS THIS TICKET'S OWN MECHANISM, DEMONSTRATED. The filing verb's mandatory
path succeeded; the unbounded advisory path then contended for thirty seconds on
a shared resource and gave up. A caller watching only the tail of that output
would conclude the filing failed. It did not.

AND IT SHARPENS THE FIX. The advisory analyses do not merely take a long time --
they take a SHARED LOCK on the graph cache, so N concurrent filings or checks
serialise against each other. That makes the cost superlinear in fleet size
rather than merely additive, which is consistent with the reporter seeing 26 and
45 minutes specifically while several of our own checks were running. Whatever
bound is chosen must account for contention, not just single-process runtime:
measure the analyses under concurrent load, not on an idle machine.

DO NOT CONCLUDE THE CACHE IS CORRUPT FROM THE FIRST LINE. The "malformed" message
came with an automatic reopen-and-retry and the run continued to the lock
timeout; a follow-up integrity check could not run because the database was still
locked by a live agent. Treat corruption as UNCONFIRMED and re-check on an idle
machine before acting on it -- an unverified corruption claim would send someone
rebuilding a cache when the real finding is contention.

THIRD REPORT, AND IT IS NOT THE SAME VERB -- WHICH WIDENS THIS TICKET. This one
filed as `ticket new`; the reporter has now hit the same shape on `ticket accept`
twice, at two different durations:

    F-329  accept exceeded even a 600 second foreground budget under load, and
           when re-run, recorded a partial result
    F-375  two chained accepts did not finish within a 60 second budget and were
           auto-backgrounded with empty output; a `show` in the meantime proved
           only the first had landed; re-issuing the third directly succeeded
           immediately

So the unbounded post-announcement work this ticket describes for filing is not
specific to filing. At least two ledger verbs can run long enough to blow a
caller's timeout, and the ticket should be scoped to the verb family rather than
to one verb. Determine which verbs run analyses after their mutation and report
the list -- the fix is per-family, not per-verb.

THE PART THAT MAKES F-375 WORSE THAN A SLOW COMMAND, and it is a new fact this
ticket did not have: THE STALL PRINTS NOTHING. The reporter observed no lease
message, no lock message, no progress line -- from either the backgrounded run or
the retry. So a caller cannot distinguish "contending on a lock", "doing unbounded
analysis", and "wedged" from the outside. They had to infer the cause and marked
their own guess as uncertain.

That is the operational half of the defect and it deserves its own acceptance
criterion: a ledger verb that is going to run longer than a second or two must SAY
WHAT IT IS WAITING ON. This repo already has the shape to copy -- the concurrency
advisory prints when another check is running, and land status markers record a
phase. A verb that blocks silently forces every caller to choose between an
arbitrary long timeout and an auto-backgrounded job with no output, which is
exactly the bind the reporter describes.

NOTE THE SECOND-ORDER COST THEY NAME: their own dispatch guidance says never let a
frob command auto-background, and they cannot honour it when a single accept can
exceed 60 seconds with no diagnostic. A tool whose latency is unpredictable and
undocumented forces its callers to write rules they cannot keep.

AND NOTE F-329's HALF THAT IS STILL UNADDRESSED HERE: a re-run recorded a PARTIAL
result. That is more serious than slowness -- it suggests an interrupted verb can
leave the ledger half-written, which is a correctness claim rather than a
performance one. Chase it separately if this ticket's scope will not hold it, but
do not let it be forgotten inside a latency ticket.
