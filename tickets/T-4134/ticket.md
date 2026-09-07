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
