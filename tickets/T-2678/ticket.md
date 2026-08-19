---
id: T-2678
title: frob ticket body writes an archived ticket's update to a fresh non-archive
  copy, causing DuplicateId
state: queued
kind: bug
origin: human
created: '2026-08-19'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_body.py
- src/frob/app/ticket_runner
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: priority
  old_value: medium
  new_value: critical
  reason: corrupts main directly for the whole fleet via the body-mutation mirror
    step; coordinator-elevated
  actor: logan
  at: '2026-08-19'
body_changes:
- mode: append
  reason: 'coordinator review: elevate to critical, confirm correct repair direction
    (archive is canonical, not active), note the mirror-to-primary-checkout blast
    radius and the possible T-2666 ClaimDivergence connection'
  actor: logan
  at: '2026-08-19'
  old_length: 2169
  new_length: 4280
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`frob ticket body <id> --set-file/--append-file` against an ARCHIVED
ticket (living in `tickets/archive/<id>/`) writes its updated
ticket.md to a FRESH `tickets/<id>/` location instead of updating the
existing `tickets/archive/<id>/ticket.md` in place -- leaving both
present with the same id. `frob ticket show <id>` then fails outright
with `DuplicateId: Ticket id already exists`, blocking every operation
against that id until someone manually deletes the stale archive copy.

Reproduced directly (2026-08-19, T-2669 dispatch): `frob ticket body
T-1688 --append-file ... --reason ...` against T-1688, which lived
only in `tickets/archive/T-1688/` beforehand. After the command, BOTH
`tickets/T-1688/` (new, carries the append + a `body_changes` audit
entry) and `tickets/archive/T-1688/` (stale, pre-edit, done-report.md
byte-identical to the new copy's) existed. `frob ticket show T-1688`
failed with DuplicateId immediately afterward. Recovered by deleting
the stale archive copy (confirmed safe: done-report.md identical,
archive copy missing the just-recorded body_changes entry) and keeping
the fresh active-location copy as canonical.

T-2344/T-2348 (touched the same session via `frob ticket evidence
--replace`, not `frob ticket body`) did NOT hit this -- neither was
archived, so this may be specific to `frob ticket body`'s write path
not consulting the archive location the way `evidence --replace`'s
does, or specific to the append/set code path in general. Worth
checking whether `frob ticket evidence`/`drop`/other mutating verbs
share the same archive-unaware write path before assuming this is
`body`-only.

## Positive controls this needs

- Running `frob ticket body <archived-id> --append-file ...` must
  update `tickets/archive/<id>/ticket.md` in place, never create a
  parallel `tickets/<id>/`.
- The must-NOT-fire control: the same command against a non-archived
  ticket must continue writing to `tickets/<id>/` exactly as today.

## Do NOT

- Do NOT make `frob ticket show` silently pick one of two duplicate
  ids -- the current hard DuplicateId refusal is correct and caught
  this defect; fix the write path, not the read-time symptom.


CRITICAL (elevated 2026-08-19, coordinator review): this bug corrupted
main directly, not just a worktree. `frob ticket body`'s write mirrors
straight to the primary checkout (the same "mirrored onto the primary
checkout ... visible to the fleet now" step every scope/body/evidence
mutation performs) -- so a single `frob ticket body <archived-id>
--append-file` on a done ticket takes down `frob ticket show` for
EVERY ticket, fleet-wide, the moment it runs, not just locally.
Reproduced directly today (T-1688, T-2669 dispatch): the corruption
sat on main for roughly 20 minutes before repair and is suspected
(not yet confirmed) of contributing to an unrelated land's own
ClaimDivergence failure (an identity-less finding against the retired
`tickets.md` v1 monofile, which is plausible if the ledger failed to
load cleanly mid-check).

CORRECT REPAIR DIRECTION (get this right the first time -- the
initial repair attempt in this session got it backwards): the ARCHIVE
copy is the ticket's real home; the ACTIVE-path copy the bug creates
is the corrupt artifact, not the good one. A naive "keep whichever
copy has my newest edit" repair risks silently un-archiving a done
ticket (moving it back into the active set, changing every open/done
count that reads `tickets/T-*/`) -- a worse, quieter corruption than
the DuplicateId itself. If the active copy carries content the
archive copy is missing (e.g. an append made after the bug already
routed the write to the wrong path), preserve that CONTENT by copying
it onto the archive-path file, then delete the active directory --
never keep the active directory wholesale.

## Positive controls, both directions (required before landing the fix)

- `frob ticket body <archived-id> --append-file/--set-file ...` must
  write to `tickets/archive/<id>/ticket.md` in place and must NOT
  create a `tickets/<id>/` directory at all.
- The must-NOT-regress control: the identical command against a
  NON-archived (active) ticket must continue writing to
  `tickets/<id>/` exactly as today -- do not overcorrect into routing
  every ticket through the archive path.
