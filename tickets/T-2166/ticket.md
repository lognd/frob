---
id: T-2166
title: docs/modules/tickets.md needs a --finish-pure-cleanup section for T-2108
state: queued
kind: docs
origin: human
created: '2026-08-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-2108 fixed `frob ticket land --finish` re-running the full land
pipeline (including a BUG002 repro re-check that now genuinely PASSES,
since the fix is already on main) on a ticket already terminal
(done/dropped) on main -- `_finish_only_if_already_landed`/
`_ticket_terminal_state_on_main` in
src/frob/app/ticket_runner/_land_cmd.py.

docs/modules/tickets.md needs a new section describing this
(originally drafted, then reverted when T-2132 took a live lease on
the file mid-ticket): add "## --finish is pure cleanup when already
landed (T-2108)" right after the existing "## Auto-rebase after a
successful land (T-1720)" section, frob:describes both new symbols,
and explain the distinction from _check_already_landed/
AlreadyLandedOnMain (that one refuses loudly on an empty scope-diff
for ANY land call; this one only fires for --finish/--retire-on-proof,
keys on terminal STATE not diff emptiness, and succeeds quietly since
--finish's whole point is cleanup).

Could not be done in T-2108 itself: docs/modules/tickets.md was held
by T-2132's live cross-worktree lease at land time.
