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

RETRACTED MEASUREMENT, 2026-08-09, coordinator. An earlier block appended
here claimed LAND-PROOF produced a FALSE NEGATIVE on T-1895's land
(is_ancestor_of_main=False for a commit that was really on main). THAT
CLAIM WAS WRONG and has been removed so it cannot mislead whoever works
this ticket.

What actually happened: LAND-PROOF was CORRECT. `frob ticket land T-1895`
printed "landed as ... 18b82c8cab4c" and reported
is_ancestor_of_main=False / verified=False, and 18b82c8cab4c is genuinely
NOT an ancestor of main -- `git branch --contains` places it only on the
unrelated branch `t-1906-fix`. The extraction it supposedly landed is
absent from main (node_body_span missing from src/frob/strata/_sync_may.py,
the duplicate _iface_node_body_span still present in
src/frob/gates/_fix_engine_sync.py).

My original verification was the error: I ran `git merge-base --is-ancestor`
and a grep immediately after the land and read them as confirming success,
against a tree state that did not persist. The lesson is the reverse of
what I first recorded -- LAND-PROOF caught a real lost land, and the
operator (me) overrode a correct warning with a hasty check.

The genuine defect behind that land is filed separately; this ticket
remains about the anchor-state carve-out only. Do NOT widen T-1884's scope
on the strength of the retracted block.
