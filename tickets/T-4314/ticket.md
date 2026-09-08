---
id: T-4314
title: Land lock file names a dead holder after completion, read as a live land
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_leases.py
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_leases.py
  reason: 'SCOPE002: T-4314''s scope symbols already carry frob:tests directives into
    this file (88 pre-existing) plus this ticket''s own new forcing tests; add it
    so evidence coverage resolves in-scope'
  actor: logan
  at: '2026-09-08'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE LAND LOCK FILE KEEPS NAMING A DEAD PROCESS AFTER THE LAND FINISHES, AND
READERS TREAT THAT LEFTOVER CONTENT AS THE CURRENT STATE.

MEASURED TODAY. After a land completed successfully, the lock file still contained
a JSON record naming a process id, a session id, a start timestamp, and the ticket
that had been landing. That process no longer existed, no land process was running
at all, and taking the advisory lock succeeded immediately -- the lock was free.
The file's contents were pure residue.

THE ACTUAL STATE IS THE ADVISORY LOCK, NOT THE FILE. The kernel releases the lock
when the holder dies, which is exactly the property that makes it trustworthy and
that a previous investigation in this repository already established. The JSON
body is metadata about who holds it, and nothing clears that body on the normal
completion path.

WHY THE RESIDUE IS NOT HARMLESS. A refusal message built from this file names a
live-looking holder with a plausible recent timestamp, so a reader concludes a
land is in progress and waits. One agent did exactly that today: it ended its turn
to wait for a land that had already finished, on the strength of file contents
that were never going to change. A record that cannot become stale-looking is the
whole point of a status file; this one is indistinguishable from a real one.

DECIDE BETWEEN THE TWO HONEST FIXES rather than splitting the difference. Either
the file's contents are cleared when the lock is released, so its presence means
something; or every reader of the file first tests whether the lock is actually
held and treats the body as descriptive only, so a stale body cannot produce a
"land in progress" claim. The second is more robust because it survives a crash
that skips any cleanup, and this file's whole purpose is describing a situation
where processes die unexpectedly -- but check how many readers exist before
choosing, and make whichever you choose the single path.

MAKE THE MESSAGE SAY WHAT WAS CHECKED. Any refusal that claims a land is in
progress should be able to state that the lock is genuinely held, not merely that
a file exists containing a pid. If the holder is dead, say so and proceed.

FORCE THE CONDITION IN A TEST -- write the file naming a pid that does not exist,
leave the lock unheld, and assert no reader reports a land in progress. A
diagnostic verified only in the healthy case is not verified; this repository has
paid for that lesson repeatedly.
