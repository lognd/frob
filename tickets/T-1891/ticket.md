---
id: T-1891
title: frob ticket new prints a DirtyMain --no-commit warning even when it DID commit
  the ledger
state: queued
kind: bug
origin: agent
created: '2026-08-09'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED 2026-08-09, coordinator, on main. Ran 'frob ticket new ...' with no --no-commit flag. It printed:

  WARNING: tickets: T-1890 ledger change left DIRTY by --no-commit -- this WILL DirtyMain-block every concurrent 'frob ticket land' ... Fix: git add tickets/T-1890 tickets.md && git commit ...

but it had ALREADY committed the change itself (commit 9ca6bba96, tree clean immediately after). The recommended remediation then failed with 'nothing to commit, working tree clean'.

WHY IT MATTERS. DirtyMain deadlock is one of this repo's most expensive known footguns, so this warning is one an operator is trained to act on instantly. Crying wolf on the clean path is worse than silence: it teaches coordinators to ignore the one message that actually matters, and it burns a redundant commit round-trip during a live multi-agent wave.

FIX. Gate the warning on the ACTUAL post-write worktree state (or on the --no-commit flag genuinely being set), not on an unconditional code path. Add a regression test asserting the warning is absent when 'ticket new' commits, and present when --no-commit is passed.