---
id: T-3608
title: worker death with pinned serial-group items deadlocks the suite until budget
  kill; extend T-3516 crash reporting
state: queued
kind: bug
origin: human
created: '2026-08-31'
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
Run 33451274911 ubuntu, aftermath of the SIGBUS worker death (companion
ticket): the suite then STALLED ~20 min at 99% until the 40m step budget
killed it with SIGABRT. Final faulthandler dump: every surviving worker
idle in xdist remote.py:214 run_one_test -> remote.py:90 get (waiting
for a next item), controller in dsession.loop_once -> queue.get. The
dead worker held pending items (plausibly the serial frob_self_scan_heavy
xdist_group items, which pin to one node); the controller never
rescheduled them and never ended the session.

Also: NO WORKER-CRASH-REPORT line was emitted -- T-3516's
pytest_handlecrashitem hooks did not cover this death path (node died
mid-item from a fatal signal; collection of crash items may only fire on
certain xdist events).

Ticket asks:
1. Make a worker death LOUD and TERMINAL: detect node-down with pending
   items that cannot be rescheduled (serial group pinned to the dead
   node) and abort the session with a clear SUITE-RESULT-FAILED line,
   instead of idling until the CI budget kills the job. A
   pytest_handlecrashitem / DSession node-down hook in tests/conftest.py
   is the likely seam (extend T-3516's machinery).
2. Extend the WORKER-CRASH-REPORT collection to this path so the
   step-summary surfacing shows WHICH item was running when the node
   died (we only know "52%, coverage_gate parse" from the faulthandler
   dump this time).
3. Positive control: a test that kills a worker mid-item and asserts the
   session ends promptly with the loud report, not a hang.

This is CI-resilience: even after the SIGBUS root cause is fixed, ANY
future worker death must cost minutes, not the whole leg's budget.
