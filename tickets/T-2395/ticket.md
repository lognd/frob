---
id: T-2395
title: 'scope contention is undiscoverable: no way to ask which files are declared
  by many open tickets'
state: queued
kind: feature
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: Given a ledger where several open tickets declare the same file, when frob
    ticket contention runs, then it reports each contended file ranked by ticket count
    with the owning ticket ids and a suggested single-agent batching.
  evidence: []
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED TODAY: `src/frob/__main__.py` is declared by NINE queued
tickets simultaneously (T-2385, T-1135, T-1608, T-1609, T-1614, T-1656,
T-1661, T-1945, plus the never-close anchor T-1831), and
`src/frob/app/_config_external.py` by six (T-1656, T-1661, T-1666,
T-1945, T-2202, T-2387).

I discovered this ONLY as a side effect of `frob ticket new` printing
overlap warnings while filing an unrelated ticket. There is no way to
ASK the question. Consequences paid today: two tickets were
double-assigned to different agents earlier in this drive, and a series
had to be re-routed mid-flight when the contention was noticed by luck.

Because scope is a write lease, contention directly caps parallelism --
it determines how many agents can work at once, which is the single
most important number for a drain drive. It should not be discoverable
only by accident.

FIX: `frob ticket contention` -- report files declared by 2+ open
tickets, ranked by ticket count, with the ticket ids per file and a
suggested batching (the set of tickets that should go to ONE agent
because they share a lease). Complements `frob ticket wave --agents N`,
which already computes scope-disjoint groups: wave answers "how do I
split work", contention answers "where is work already colliding".
Per the automatic-over-commands directive, also surface a warning in
`frob ticket doable` when a returned ticket sits on a hot file, so an
operator who never runs the new verb still sees it.
