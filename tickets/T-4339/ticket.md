---
id: T-4339
title: frob ticket new reported creating a ticket that was never written
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_create.py
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
THE TICKET COMMAND REPORTED CREATING A TICKET THAT WAS NEVER WRITTEN ANYWHERE, AND
NOTHING NOTICED FOR HOURS.

MEASURED. Of thirty-four tickets filed in one working day, thirty-three exist on
disk and in git history. One does not exist ANYWHERE: no ticket directory, no
commit that created it, no commit that so much as mentions its id, in the working
tree, the archive, or any of roughly thirty live worktrees. The only trace is a
zero-byte lock file bearing its id, timestamped at the moment of filing.

THE COMMAND PRINTED SUCCESS. Its output was the ordinary `created <id>: <title>`
line, indistinguishable from the thirty-three that worked. That line was taken at
face value, the id was handed to an implementer hours later, and the failure only
surfaced when that implementer searched exhaustively for a ticket that had never
existed and reported the id as unresolvable.

THIS IS A SILENT-SUCCESS DEFECT, WHICH IS THE INVERSE OF THE FAILURE MODE THIS
PROJECT NORMALLY CHASES AND STRICTLY WORSE. A command that fails loudly costs a
retry. A command that reports success while persisting nothing destroys the record
it was invoked to create, and the loss is undetectable at the call site. The
ticket IS the durable record; if it does not survive, the content is gone. The
only reason nothing was lost here is an accident: the full brief happened to be
duplicated in the dispatch message that referenced the id.

FIND OUT WHERE THE WRITE WENT. The id was clearly allocated -- the lock file
proves the allocator ran and reserved it. Something between allocation and the
committed ticket file did not happen, and did not raise. Candidate seams worth
examining: whether the directory write and the commit are separate steps with a
window between them; whether a concurrent land's ledger splice can drop a
freshly-created ticket that is not yet committed; whether an error on the commit
path is swallowed; and whether the success line is printed before the write is
durable rather than after. Establish which actually occurred rather than hardening
all four on suspicion. Note that several lands and other ticket creations were
running concurrently at that moment, so a concurrency window is a strong
candidate -- but confirm it.

THE SUCCESS LINE MUST FOLLOW THE WRITE, NOT PRECEDE IT. Whatever the root cause,
the command should confirm the ticket is readable back before claiming it exists.
A read-back check after creation is cheap relative to filing a ticket at all, and
it converts a silent loss into a loud failure.

CONSIDER THE ORPHANED LOCK AS A DETECTION SIGNAL. A lock file whose id has no
corresponding ticket is, by construction, evidence of exactly this failure. Say
whether that is worth surfacing routinely -- it would have caught this within
minutes instead of hours.

VERIFY BY FORCING THE CONDITION, not by filing tickets until one fails. Whatever
seam you identify, drive it deliberately (interrupt or fail the write, or induce
the concurrent operation) and assert the command reports failure and does not
print a success line. Then confirm the normal path still works and still commits.
