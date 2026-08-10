---
id: T-1999
title: Land-path guards decide ticket liveness from main's IN_PROGRESS state, not
  the live lease, so a started-but-unsynced worktree's files land unguarded
state: queued
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED, 2026-08-10, during `frob ticket land T-1977` (landed commit
f3257572a).

T-1977's land wrote `docs/modules/gates.md` -- a file it does NOT declare
in its own scope -- via the pre-land Tier-A pass
(`fix_docenum001_enumerates_sync` regenerating the `frob:enumerates
members=` list after SYS111 was registered). At that exact moment
`docs/modules/gates.md` was in T-1665's declared scope and
`.git/frob-leases/T-1665.json` was LIVE (verified present immediately
before and after the land; `pgrep -fa T-1665` showed 5 running
processes both times). The land did not refuse. Confirm with
`git show f3257572a -- docs/modules/gates.md` (1-line diff).

ROOT CAUSE -- it is NOT the auto-fix ordering. T-1932's
`_reverify_cross_ticket_leakage_post_mutation`
(`src/frob/tickets/_land.py:3345`, called at `:1549`) is correctly
placed AFTER the wip-commit and DID run. It did not fire because
`_check_cross_ticket_leakage` only counts a file as leaked when the
OTHER ticket is `IN_PROGRESS` (T-1639, deliberate), and it reads that
state from MAIN's ledger. At land time
`git show f3257572a^:tickets/T-1665/ticket.md` reports `state: planned`
-- T-1665's worktree had started it locally and taken the lease, but
main's copy had not yet been updated.

So two authorities disagree about whether a ticket is live: the
cross-worktree LEASE FILE (which the concurrent worktree actually
created, and which `frob ticket start` writes first) and MAIN'S TICKET
STATE (which the guard trusts). Every land-path guard gated on
`IN_PROGRESS` is blind for the whole window between a worktree taking a
lease and main observing the state transition. This is the same
authority-divergence class T-1993 just fixed for scope CONTENT, one
level up: T-1993 made the lease's scope authoritative, but the guards
still decide LIVENESS from main's state field.

## Do not fix it this way
- Do NOT make the Tier-A auto-fix skip files outside the landing
  ticket's scope. The auto-fix regenerating a derived claim is correct
  and is what makes `frob:enumerates` self-healing (see T-1974); the
  bug is that the guard did not evaluate the write, not that the write
  happened.
- Do NOT re-order or duplicate the post-mutation re-check. It ran, at
  the right point, and returned a correct answer given its inputs.
  Adding a third call site changes nothing.
- Do NOT widen the guard to all non-done states without measuring: the
  `IN_PROGRESS`-only narrowing is T-1639's deliberate choice and
  reverting it blindly re-opens whatever T-1639 closed. Read T-1639
  first.
- Do NOT fix this by having agents update main's state sooner. That is
  a process rule, and a process rule is not an enforcement.

## Acceptance criteria
1. A test that reproduces the miss and FAILS FIRST: ticket A lands a
   change touching a file that is (a) in ticket B's declared scope and
   (b) covered by a live `.git/frob-leases/B.json`, while main's copy
   of B reads `state: planned`. The land must refuse. Assert the
   current code lands it clean before the fix.
2. Liveness for every land-path guard is decided from the lease file
   when one exists, falling back to main's ticket state when it does
   not -- fixed in ONE place both guards call, not per-guard.
3. Re-measure: the same scenario with B's lease absent and B `planned`
   must still land clean (no over-refusal on genuinely dormant work).
