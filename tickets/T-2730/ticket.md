---
id: T-2730
title: Update tickets-data-storage.md anchors after T-2695's _store_migrate.py extraction
state: queued
kind: docs
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/tickets-data-storage.md
- src/frob/tickets/_store_migrate.py
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
## Description

T-2695 (LARGE001 remainder batch 2) extracted `_store.py`'s migration
functions (`migrate_to_ledger`, `migrate_v1_to_v2`, `migrate_missing_v2`,
`_migrate_one_v2`, `_split_done_report`) into a new
`src/frob/tickets/_store_migrate.py` module. `docs/modules/tickets-
data-storage.md` still carries `frob:describes src/frob/tickets/_store.
py::migrate_to_ledger` (and 3 sibling anchors) pointing at the OLD
location -- these need updating to `src/frob/tickets/_store_migrate.py`.

NOT fixed in T-2695 itself: `docs/modules/tickets-data-storage.md` was
under another ticket's (T-2718) live cross-worktree lease at the time of
the extraction, so it could not be edited from that worktree. T-2695
waived the resulting AFFECT001 findings citing this lease conflict, with
this ticket as the follow_up.

Once T-2718's lease clears: update the 4 `frob:describes` anchors in
`docs/modules/tickets-data-storage.md` to name
`src/frob/tickets/_store_migrate.py` instead of `src/frob/tickets/
_store.py` for `migrate_to_ledger`/`migrate_v1_to_v2`/`_migrate_one_v2`/
`_split_done_report`, then remove the now-unneeded AFFECT001 waivers in
`_store_migrate.py`.
