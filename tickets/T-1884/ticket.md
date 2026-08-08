---
id: T-1884
title: LAND-PROOF verified=False for a correctly-landed anchor ticket (state_on_main
  queued/blocked)
state: queued
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
`_land_proof_checks`/`_print_land_proof` (src/frob/app/ticket_runner/_land_cmd.py)
compute the `LAND-PROOF:` line's `verified` bool as `is_ancestor_of_main AND
state_on_main in (done, dropped)` -- it predates the T-1856 `anchor` marker
and T-1874's land-time skip-close path, so landing a legitimately anchored,
requeued ticket (state stays `queued`/`blocked` on main by design) always
prints `verified=False` even though the land is completely correct and
`is_ancestor_of_main=True`.

Observed landing T-1820 (2026-08-08): `LAND-PROOF: ticket=T-1820
commit=cf87185531cb62b8c98e20fc461d79f673da72c7 is_ancestor_of_main=True
state_on_main=queued verified=False`. The land is correct; the proof check's
notion of "terminal" just does not know about anchor tickets yet.

Fix: `state_ok` should also accept `state_on_main in (queued, blocked) AND
the ticket's `anchor` field is True` (mirroring the T-1874 skip-close
condition in `_skip_close_for_anchor_no_close_requested`), not just
done/dropped. Needs the ticket's `anchor` field threaded into
`_land_proof_checks`'s already-loaded `ticket` object.
