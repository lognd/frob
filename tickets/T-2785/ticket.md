---
id: T-2785
title: frob ticket set-parent reports success while its auto-commit was refused, leaving
  the shared root dirty and blocking every agent land
state: queued
kind: bug
origin: agent
created: '2026-08-21'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_setters.py
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
## Measured

2026-08-21. Ran, from the shared root, while another agent's land held
`land.lock`:

    frob ticket set-parent T-2386 T-2384 --reason "..."

Output, in this order:

    WARNING: tickets: <root> refused -- a land is in progress for
      T-draft-03fd43db (land.lock held by {...}) -- retry after it completes
    ticket set-parent: resolved root <root>
    T-2386: parent now T-2384

Exit status was success and the final line reports the mutation as DONE.
But the auto-commit (T-1615's uniform ledger auto-commit) was refused by the
land lock, so the write landed in the working tree and was never committed.
Net result: `git status` showed `M tickets/T-2386/ticket.md` and the shared
root was DIRTY.

## Why this matters

A dirty shared root DirtyMain-blocks EVERY other agent's land. `fleet_status`
reports `ROOT DIRTY -- do not dispatch`. So a single setter call issued at
the wrong moment silently converts into a fleet-wide dispatch block, with a
success message telling the caller everything worked.

This is the same class as the recorded lesson that query commands dirty the
root by writing files and abandoning them uncommitted when they lose the
lock. Here it is a MUTATION command, and it is worse, because the caller is
explicitly told the mutation succeeded.

## Two distinct defects

1. PARTIAL SUCCESS REPORTED AS SUCCESS. The write happened, the commit did
   not, and the command said "parent now T-2384" and exited 0. It must
   either (a) refuse the whole operation up front when the ledger cannot be
   committed -- consistent with `frob ticket new`, which under the same
   condition refuses cleanly with `LandInProgress` and does NOT leave a
   partial write -- or (b) succeed and report explicitly that the change is
   UNCOMMITTED, naming the file and the follow-up needed. Silent partial
   success is the worst of the three.

   Note `frob ticket new` already gets this right in the same repo under the
   same lock condition. The two paths should agree; the refusal logic that
   `new` uses is the model.

2. NO-OP MUTATION WRITES AN AUDIT ENTRY. The call set parent to the value it
   ALREADY had (an earlier agent had performed the real re-parent). Instead
   of being a no-op, it appended a `triage_changes` record with
   `old_value: T-2384` / `new_value: T-2384`. An audit trail that records
   non-changes is noise that makes real changes harder to find, and here it
   is what produced the dirty file. A setter whose new value equals the
   current value should be a clean no-op.

## Positive controls, both directions

- With a land in flight, `set-parent` either refuses with a typed error and
  leaves the working tree CLEAN, or completes and says plainly that the
  change is uncommitted. In neither case may `git status` come back dirty
  after a reported success.
- With no land in flight, `set-parent` still works exactly as today,
  including its auto-commit. Without this the fix is indistinguishable from
  disabling the setter.
- Setting a parent to its CURRENT value writes no `triage_changes` entry and
  leaves the file byte-identical.
- Setting a parent to a genuinely NEW value still writes exactly one audit
  entry with the correct old/new values.

## Scope note

Check whether the sibling setters (`priority`, `kind`, `component`, `tier`,
`milestone`, `runs-last`, `label`, `body`) share this code path. If they do,
fix it once in the shared home rather than per setter -- and say in the Done
report which ones were verified, not which ones were assumed.
