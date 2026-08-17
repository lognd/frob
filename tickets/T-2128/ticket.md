---
id: T-2128
title: SCOPE002 for docs/modules/tickets.md#coalescing-verify-worker-t-1688 is ERROR-severity
  while every other SCOPE002 against this doc is a warning
state: queued
kind: bug
origin: human
created: '2026-08-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`frob check --ticket <id> --only scope` reports 8 SCOPE002 ERRORS (not
warnings) for docs/modules/tickets.md#coalescing-verify-worker-t-1688's
frob:describes targets in src/frob/verify/_worker.py, for ANY ticket
whose scope declares docs/modules/tickets.md alone -- confirmed against
T-1973, which made ZERO content edits this session (a pure Done-report
closure), and still shows the identical 8 errors as T-1899/T-1952/
T-1996, which DID edit the doc. Every other SCOPE002 finding for the
same broad doc file reports as a WARNING (386 of them, same run) --
these 8 are the only ones promoted to ERROR, and the promotion is
unrelated to anything touched this session.

Pre-existing, not caused by any of T-1899/T-1952/T-1996/T-1973's own
work -- filed rather than silently worked around. Worth investigating
why this one anchor's SCOPE002 findings are ERROR-severity while every
sibling SCOPE002 finding against the same doc file is WARNING-severity.
