---
id: T-1780
title: 'Split docs/modules/tickets.md: 35 open tickets name it, so any one blocks
  the other 34'
state: queued
kind: feature
origin: agent
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/tickets.md
- docs/index.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
`docs/modules/tickets.md` is the single largest throughput limiter on
this repo's queue. Measured: **35 open tickets name it in their scope.**

Because scope is also the lease, any one of those 35 blocks the other 34.
Observed continuously this session -- at every check, that file had a live
lease, and tickets waited behind it that shared no code at all:

- T-1720 (land should auto-rebase the worktree) and T-1771 (uv.lock
  coherence) sat blocked through multiple dispatch cycles, held first by
  T-1613/T-1743, then by T-1750/T-1779, never by anything they overlapped
  with in code.
- A five-agent wave could only ever run one agent on ledger/land work,
  because every such ticket needs this doc.
- Groups had to be assembled around "who gets tickets.md" rather than
  around the work, which is the opposite of how dispatch should be
  planned.

The file has grown to hold: the ticket lifecycle, the land pipeline, the
post-land sweep, the rapid profile, deferred verification, worktree
leases, the ledger v2 layout, the release quartet, worktree liveness, and
more. Those are separate subsystems that happen to share a doc.

SPLIT IT, one file per concern the tickets actually cluster around.
Suggested seams, but measure before committing to them -- group the 35
tickets by which SECTION they cite and let that drive the split:

- `docs/modules/ticket-lifecycle.md` (states, transitions, evidence,
  done reports)
- `docs/modules/land.md` (the land pipeline, squash/splice, release
  quartet, land-owned files)
- `docs/modules/verification.md` (post-land sweep, deferred verification,
  the watermark epic, rapid profile)
- `docs/modules/worktrees.md` (leases, liveness, isolation, sweep)
- `docs/modules/ledger.md` (v1/v2 layout, merge driver, archive)

REQUIREMENTS:

1. Every `frob:doc` anchor pointing into the old file must resolve after
   the split. There are many. This is exactly what DOC006/COV005 exist to
   catch, so a clean `frob check` is the completeness proof -- do not
   hand-audit and hope.
2. Update the SCOPE of the affected open tickets to name their new doc
   home. That is the entire point: if the 35 tickets keep naming one
   file, splitting the file changes nothing.
3. Do NOT leave `docs/modules/tickets.md` as a stub that re-includes the
   others. A stub everything still points at reproduces the lease
   exactly.
4. `docs/index.md` and any cross-references get updated in the same
   change.

MARK THIS `runs-last`. T-1613 landed that marker today for precisely this
shape: an operation that touches something everything else depends on,
and is safe only when nothing else is in flight. Splitting a file 35 open
tickets reference while any of them is being worked would produce exactly
the merge carnage the marker exists to prevent. Set it with
`frob ticket runs-last <id> on` and let the queue enforce the quiet
window rather than a coordinator remembering to.

This is a documentation change with no behavioural effect, and it will
unblock more parallel work than any code fix currently in the queue.
