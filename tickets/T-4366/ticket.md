---
id: T-4366
title: xdist remove_node has the same mutation-during-iteration race as the hardened
  sibling
state: in-progress
kind: bug
origin: human
created: '2026-09-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/conftest.py
- tests/unit/test_conftest_stackdump.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_conftest_stackdump.py
  reason: regression test for the remove_node fix lives here, sibling of the file
    conftest.py's scope already covers
  actor: logan
  at: '2026-09-09'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE PARALLEL-SCHEDULER HARDENING FIXED ONE METHOD AND ITS SIBLING HAS THE SAME
BUG, WHICH IS NOW WHAT ABORTS THE WINDOWS SUITE.

MEASURED, with the traceback:

  File ".../xdist/scheduler/loadscope.py", line 202, in remove_node
    for node in self.assigned_work:
  RuntimeError: dictionary changed size during iteration
  SUITE-RESULT: DID-NOT-COMPLETE exitstatus=3 (INTERNAL-ERROR)
    collected=13847 (partial) failed=4 (partial, lower-bound)

A ticket already hardened this scheduler's work-assignment method against a
worker vanishing mid-operation, patching it the same way an earlier fix patched
the session layer. That fix is holding -- the error it addressed no longer
appears. This is the neighbouring method in the same class, iterating a
dictionary that a departing worker mutates underneath it.

THE TRIGGER IS THE SAME UNDERLYING EVENT, which is why this keeps resurfacing in
different guises: workers are dying mid-run. The same log shows TWO of them dying
at roughly 300 seconds, both in the self-model suite, both suspected out-of-memory
-- that memory question is being measured separately and is not this ticket's job.
What IS this ticket's job is that a dying worker should not take the whole session
down through a bookkeeping race, regardless of why it died.

FIX THE SIBLING THE SAME WAY, and then look for others rather than stopping at
two. Read the whole class: any method iterating that structure while a worker can
be removed concurrently has this shape. Fixing them one incident at a time is how
this has gone so far -- a session-layer fix, then a work-assignment fix, now a
removal fix. Enumerate the exposure instead and say what you found, even if the
answer is that these were the only two.

NOTE WHAT IMPROVED, because it changes what a future abort costs. The run now
reports 13,847 collected and a real partial failing set, where an earlier abort of
this kind reported zero collected and discarded everything that had passed. That
was fixed alongside the first scheduler patch. So an abort is no longer total data
loss -- but it is still an abort, and the goal remains a completed run.

VERIFY BY FORCING THE CONDITION rather than by absence: drive a worker removal
concurrent with the iteration and assert the session survives. The prior fix was
verified by a traceback match plus cross-platform execution, not by a green run,
and that standard held up -- one completed Windows run was NOT proof, as this
project already learned the hard way.

Windows is measurable locally: `winrun` (/home/logan/bin/winrun) syncs this repo to
a Windows mirror and runs natively. Caveats: single shared mirror checkout, venv
uses `Scripts/` not `bin/`, bare `python3` hits a Store alias stub exiting 9009.
