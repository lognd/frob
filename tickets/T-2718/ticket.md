---
id: T-2718
title: 'TICK011 refuses to close a Done report that frob''s own Tier-A generator produced,
  forcing a hand-appended Filed: line'
state: queued
kind: bug
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
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
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Observed independently by three agents in one session

`frob ticket close` refuses with TICK011 against a Done-report section
that FROB'S OWN Tier-A generator produced, unless a literal `Filed: T-####`
line is present. The generated `### Changed` section does not include one.

Each agent hit it, could not proceed, and independently worked around it
the same way -- appending a `Filed:` line by hand via
`frob ticket body --append`. Three separate rediscoveries of the same
workaround, none of them recorded anywhere the next agent would look.

Instances: T-2141 and T-2303 (same agent, twice), T-2679, T-2128.

## Why this is worth fixing rather than tolerating

A gate that demands a format the tool's own generator does not emit will
obstruct every future agent identically. The workaround is harmless in
isolation, which is exactly why it will keep being rediscovered rather
than reported -- each agent reasonably treats it as a local papercut and
moves on.

Note also that hand-appending a `Filed:` line to satisfy a gate is
DISCLOSURE THEATRE when there is no real follow-up to name: the agent
writes a line whose only purpose is to clear the check. One agent
observed the sharp end of this directly -- a ticket with a genuine
`### Changed` section and NO real follow-up has no clean escape today,
so the honest options are to invent a citation or to not close.

## What to decide

Either:
(a) the generator emits whatever TICK011 requires, so generated reports
    pass by construction; or
(b) TICK011 stops requiring a `Filed:` line for a section the generator
    produced, and requires it only where a follow-up genuinely exists.

Prefer whichever keeps TICK011's real signal intact. Its job is to catch
work that was cut and never recorded -- do NOT weaken that. The bug is
that it fires on a section frob itself wrote, not that it asks for
disclosure.

## Positive controls, both directions

- a Tier-A-generated Done report with no real follow-up CLOSES without a
  hand-appended line
- a ticket that genuinely cut scope and named no follow-up STILL fires
  TICK011 -- without this the fix has removed the gate's purpose
- an explicitly recorded follow-up is still accepted and still surfaces

## Note

This is adjacent to but distinct from T-2372 (burn TICK004/TICK007/TICK011
WARN gates to zero, then promote to error). That ticket is about clearing
the existing backlog; this one is about the gate firing on frob's own
generated output, which would keep regenerating that backlog.
