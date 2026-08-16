---
id: T-2180
title: fleet_status.py cannot answer 'which lands are in flight', so every coordinator
  hand-rolls a ps grep that overcounts 4x -- the misread behind two agents reporting
  15-16 concurrent lands when there were 4
state: queued
kind: feature
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: Report DISTINCT land invocations keyed on ticket id, derived from the process
    table's structured fields (pid, etimes, cpu time, argv), never from a line count.
    'ps aux | grep -c frob ticket land' returns roughly 4 per land (the bash wrapper,
    timeout, uv run, and the real python process); two agents independently reported
    '15-16 concurrent lands' when there were 4, and the coordinator nearly repeated
    it. This test MUST fail against current main.
  evidence: []
- text: Report each land's CPU time alongside elapsed time. Content alone cannot distinguish
    a live land from a dead attempt's residue -- a killed land's staged diff is byte-identical
    across retries because it is the same work -- but CPU time discriminates immediately.
    This is what falsely read as a 'wedged land' today.
  evidence: []
- text: Report land.lock holder liveness from /proc fd ownership (does any live process
    hold the file open), NOT from the recorded pid and NOT from lock age. Pids are
    reused; a legitimate land genuinely exceeds 1500s under load. The absence of this
    check is why a stale-lock theory survived long enough to be filed critical and
    later retracted -- the lock is flock-based and the kernel frees it on holder death.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
