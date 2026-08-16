---
id: T-2200
title: TICKET ROT lists a runs_last ticket under NEEDS DISPATCH, but frob ticket start
  structurally refuses it with RunsLastBlocked, so the report recommends an action
  the tool rejects
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: medium
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
- text: 'Reproduced live: T-1614''s title is literally ''RUNS LAST: audit every frob:waive
    for cop-outs, after all other work is complete''. I ran ''frob ticket runs-last
    T-1614 on'' (runs_last: true confirmed in the ledger), and scripts/fleet_status.py
    still reports it under ''NEEDS DISPATCH (2)''. Meanwhile frob ticket start refuses
    any runs_last ticket while other tickets are open -- measured earlier today on
    T-1780, which failed with RunsLastBlocked and could not be worked until the flag
    was cleared. So the report recommends dispatching a ticket the tool will reject.
    This test MUST fail against current main.'
  evidence: []
- text: 'Read runs_last from the ledger frontmatter the report ALREADY parses (_parse_ticket_ledger_file)
    and route those tickets to a third bucket naming the real action -- they are neither
    dispatchable nor decomposable, they are deliberately deferred. Do NOT drop them
    from the report: a runs_last ticket aging past threshold is still real information,
    and T-1614 at 11 days is genuinely waiting on a queue that is not draining.'
  evidence: []
- text: 'Audit the same omission in TICK004 itself: src/frob/gates/_tickets_gate.py
    contains ZERO references to runs_last, so the gate rot-alarms a ticket another
    subsystem structurally forbids anyone from starting. Two subsystems in direct
    contradiction. Do NOT fix only the report -- the gate and the report should agree
    on what a runs_last ticket''s rot means, and fixing the display while leaving
    the gate contradictory just moves the confusion.'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
