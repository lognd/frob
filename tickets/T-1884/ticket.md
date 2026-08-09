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

ADDITIONAL MEASUREMENT, 2026-08-09, coordinator. Reproduced on a NON-anchor
ticket, which widens this ticket's scope beyond the anchor case in the title.

`frob ticket land T-1895 --worktree .../t1895-t1893` printed:

  land T-1895: landed as T-1895 at 18b82c8cab4c74d2f5457b738486a129321602e8 (14 file(s) changed)
  land T-1895: REL001 bumped to 0.419.0
  LAND-PROOF: ticket=T-1895 commit=18b82c8... is_ancestor_of_main=False state_on_main=done verified=False

The land had in fact FULLY SUCCEEDED. Verified independently, immediately after:
  - `git merge-base --is-ancestor 18b82c8... HEAD` -> true (it IS on main)
  - tickets/T-1895/ticket.md on main reads `state: done`
  - the actual code change is present (node_body_span defined once in
    src/frob/strata/_sync_may.py; zero occurrences of the deleted
    _iface_node_body_span in src/frob/gates/_fix_engine_sync.py)

So LAND-PROOF reported is_ancestor_of_main=False about a commit that IS an
ancestor of main -- a FALSE NEGATIVE, most likely evaluating the ancestry
before the commit/ref update it is checking has become visible to the query.

WHY THIS MATTERS MORE THAN A COSMETIC WRONG FLAG. LAND-PROOF is the one
line an operator reads to decide whether a land is trustworthy. A false
NEGATIVE trains the reader to disregard verified=False -- and the moment
that habit forms, a genuine verified=False (a land that really did not
reach main) reads as noise and gets waved through. This is the same
false-signal erosion as T-1891's spurious DirtyMain warning, and it
degrades the credibility of the repo's most load-bearing assertion.

FIX must make the ancestry check observe the post-land state (re-query
after the ref update, or order the check after whatever publishes the
commit), and add a regression test asserting verified=True for a land
that demonstrably reached main.
