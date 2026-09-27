---
id: T-draft-c3104c44
title: 'ticket start under a live land loses its root-ledger mirror write silently:
  the root row keeps state queued or an empty worktree while the worktree is in-progress,
  so reconcile and the passenger guard misjudge the ticket as root-pinned'
state: queued
kind: bug
origin: agent
created: '2026-09-27'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
due: null
rank: null
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/app/ticket_runner/_lifecycle.py
- src/frob/tickets/_store.py
- src/frob/tickets/_leases.py
- docs/modules/tickets-lifecycle.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: DOC006 inline waivers (T-draft-7ee140de)
  actor: logan
  at: '2026-09-27'
  old_length: 2052
  new_length: 2052
- mode: append
  reason: 'T-6538 report: start from the root pins the row; refuse start without a
    worktree'
  actor: logan
  at: '2026-09-27'
  old_length: 2052
  new_length: 3111
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured on 2026-09-26/27 on four tickets while a land drain held the
root lock: T-6524 (root row worktree=/home/logan/projects/frob,
branch=dev, no lease), T-6538 (root row in-progress with worktree=/home/logan/projects/frob
while its own worktree ledger copy has an EMPTY worktree field, 0
commits ahead: the start ran against the root before the worktree
existed and the mirror never caught up),
T-5285 (root row still `queued` while its worktree ledger says
in-progress and a lease exists), plus T-6589's own start that printed
"body mirrored onto the primary checkout" and later showed the T-4313
lost-write shape. Consequences measured: `frob ticket reconcile` reports
the ticket as a live root-pinned in-progress hold, the passenger /
sibling-scope guard blocks other tickets on its files (T-6537 and
T-6549 could not start), and a later root `requeue` then trips the
T-1914 sibling-state guard on the queued worktree.

Cause: `frob ticket start` writes the transition in the worktree ledger
and mirrors it to the root; under LandInProgress the mirror is refused
or rolled back after the verb printed success, leaving the root row
half-updated (state or worktree/branch fields stale).

Deliver: (1) `start` performs the root mirror as one atomic write of
state + worktree + branch + lease, and if the root refuses (land in
progress) it retries with `--wait` semantics by default and otherwise
prints REFUSED loudly with the exact fields left stale, never a silent
success; (2) `frob ticket reconcile` detects a root row whose worktree
is the repo root, empty, or absent while a `.claude/worktrees/<id>`
exists with commits ahead, and offers `--apply` to copy the worktree's
row to the root; (3) the passenger and sibling-scope guards read the
lease file (authoritative scope, [[leases-and-scope]]) before the root
row and ignore a root-pinned row that has no lease; (4) positive
control: a fixture with a held root lock; `start` either waits and
mirrors or exits non-zero naming the stale fields, and reconcile repairs
the planted degraded row.


Correction from the T-6538 implementer's report (2026-09-27): the root
row was NOT a lost mirror write. `frob ticket start T-6538` was run from
the shared primary checkout and frob printed "T-6538 lease NOT recorded
-- /home/logan/projects/frob is the shared primary checkout ... work this
ticket from a dedicated worktree instead (T-2007)" but still transitioned
the row to in-progress with worktree=/home/logan/projects/frob,
branch=dev and no lease file; later `frob ticket work` / `sweep` runs
could not repair the fields ("already in-progress"). So the primary
deliverable is: `start` on the shared primary checkout REFUSES (tiered
safety: a real decision) unless `--worktree <path>` (or `frob ticket
work`, which creates one) is given; a root-pinned in-progress row is
repairable by `frob ticket work <id> --worktree <path>` re-mirroring the
fields; and the passenger/sibling guards ignore a root-pinned row with no
lease. The lost-mirror-under-land case in the body stays as the second
shape (T-5285: root queued, worktree in-progress with a lease).
