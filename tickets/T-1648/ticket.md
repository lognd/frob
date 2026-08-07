---
id: T-1648
title: A ticket can close with disclosed unfinished work and no follow-up, silently
  dropping it
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_reporting.py
- src/frob/app/ticket_runner/_close_cmd.py
- tests/**
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Twice in one wave, a ticket closed while its own Done report disclosed substantial unfinished work, and that work became untracked the moment the ticket left the queue:

- T-1420 split 1 file and disclosed 52 more still over the LARGE001 threshold. Closed. The 54 warnings had no owner until T-1646 was filed by hand.
- T-1204 fixed the PERF010 family and disclosed PERF011/014/008/005/013 as not attempted. Closed. 47 warnings, no owner until T-1647.

Both agents behaved WELL: they scoped honestly, did solid work, and disclosed the cut plainly rather than padding a completion claim. The failure is structural. A Done report is free text, so "I did not attempt X" is invisible to the queue, and closing is the act that erases it. The coordinator only caught these by re-reading two long reports and noticing the warning counts had not moved as much as expected.

This is the same family as this drive's other silent-absence incidents (a gate reporting zero because it could not look; a suite truncating without a summary line): the system reports success while the unfinished part is simply not represented anywhere.

Proposed: make a disclosed remainder a first-class, structured thing.
- A ticket may close with a REMAINDER: a short structured field (not prose) naming what was not done.
- Closing with a non-empty remainder REQUIRES a follow-up ticket id, exactly as a WIRE001 waiver requires a follow_up. Frob already knows how to demand "name the ticket that carries this forward" -- reuse that machinery rather than inventing a second one.
- `frob ticket close` refuses if the Done report contains disclosure-shaped language (not attempted, disclosed cut, honest remainder, out of scope for this pass) and no remainder field is set. A heuristic prompt is acceptable here; the goal is to make the author pause, not to parse English perfectly.

The acceptance test is the one that failed here: close a ticket whose report says "52 files remain, not attempted" and have frob demand where those 52 files went.

Note for whoever implements: do NOT make this so heavy that agents stop disclosing. Honest disclosure is the behaviour worth protecting -- the fix should capture it, never punish it. If the choice is between an agent writing "not attempted" freely and an agent hiding a cut to avoid ceremony, the current state is better than a bad fix.