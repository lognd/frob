---
id: T-2714
title: A killed land strands its staged snapshot in the shared root, DirtyMain-blocking
  the whole fleet
state: queued
kind: bug
origin: human
created: '2026-08-20'
priority: high
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
## Measured three times in one session, 2026-08-20

A `frob ticket land` killed by its own `timeout 540` wrapper leaves the
SHARED ROOT dirty with the land's staged snapshot. A dirty root
DirtyMain-blocks every other agent's land, so one agent's killed land
halts the entire fleet.

Instance 1 (T-2696), captured live:

    M  src/frob/gates/_pii_structural/_emails.py
    M  src/frob/gates/_pii_structural/_keywords.py
    M  src/frob/gates/_pii_structural/_node_index.py
    M  src/frob/gates/_pii_structural/_python_fields.py
    M  tests/test_pii_structural_gate.py
    A  tickets/T-2696/done-report.md
    M  tickets/T-2696/ticket.md
    R  tickets/T-draft-0ca6b1ef/ticket.md -> tickets/T-2711/ticket.md
    A  tickets/T-2712/ticket.md

Everything staged in the index, no MERGE_HEAD, no rebase-merge. Exit 124
(the wrapper's own timeout), no surviving process. The kill landed during
POST-MERGE RE-VERIFICATION, not at the commit step.

Instance 2: a `frob ticket new` whose ledger commit lost a race left
`T-draft-800bd159` plus a modified ticket file stranded the same way.

Instance 3: an agent's `frob ticket scope` mirror-write lost its commit to
a concurrent ledger write, leaving `M tickets/T-2707/ticket.md`.

So this is NOT specific to the timeout path -- any land or ledger write
interrupted between staging and committing strands content in the shared
root and blocks the fleet.

## Why this is separate from T-2679

T-2679 (landed, 2d5ab2161) closed the state-integrity half: a killed land
no longer leaves a ticket reading `state: done` with nothing recording it,
via a new finalize-repair marker. That fix deliberately did NOT address the
shared-root residue, and that was the right call -- different concern,
wider blast radius.

## What makes it expensive

The residue is INDISTINGUISHABLE, to another agent, from abandoned dirt.
Every agent that found it correctly refused to touch it, because guessing
wrong either drops real content or clobbers a live write. So the fleet
stalls until a coordinator adjudicates by reading the staged diff by hand
to decide commit-vs-reset. That happened three times today.

In all three cases the staged tree turned out COMPLETE and CORRECT, and
recovery was simply `git commit` of what was already staged.

## Required shape

Either the land does not stage into the shared root until it can commit
atomically, or an interrupted land leaves a marker the next land (or
`fleet_status`) reconciles automatically and LOUDLY -- the same posture
T-0907 and T-2679's finalize-repair marker already take for ticket state.
An agent finding staged content in the root should be able to learn from
the tool whose it is and whether it is complete, rather than inferring it
from a diff.

## Positive controls, both directions

- a land killed mid-stage leaves the shared root committable-or-clean, and
  a subsequent land by an UNRELATED ticket is not DirtyMain-blocked
- a genuinely dirty root from real uncommitted work is STILL refused
- the reconciliation names the owning ticket and worktree, loudly, rather
  than silently absorbing content

## Do not weaken DirtyMain

It is the guard that stops agents clobbering each other. The bug is that a
killed land CREATES the condition DirtyMain refuses on -- not that it
refuses.
