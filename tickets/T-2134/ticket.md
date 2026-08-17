---
id: T-2134
title: tickets.md monofile looks stale/orphaned since the v2 sharded-ticket migration
  -- investigate and remove or document
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
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-0969/T-2131 residue. `tickets.md` (the pre-v2-migration single-file
ledger) still exists at the repo root, 545KB/11252 lines, and trips 10
DOC006 findings.

One-line check (2026-08-11): `git log -1 -- tickets.md` shows its last
real commit was 2026-08-07 (T-1763's land), while `tickets/T-*/ticket.md`
directories have moved on every single land since -- roughly 150+ lands
in the gap. Its own content is stale (e.g. its copy of T-0969 does not
reflect any state change made via the CLI since Aug 7).

`LEDGER_PATH`/`_LEDGER_NAME` ("tickets.md") is still a live constant in
`src/frob/tickets/_models.py`/`_store.py`, used throughout scope-matching
as an "always in scope" path name -- but that is a SYMBOLIC use (the
string literal), not evidence the physical file is still read or
written. `ledger_path()`/`tickets_dir()` in `_store.py` are docstringed
as "legacy"/"single mode" -- worth checking whether any live code path
still writes through them for a v2 (sharded) repo, or whether this file
is pure leftover from before the migration completed.

Investigate and either: (a) confirm nothing reads/writes it and delete
it (a `git rm`, not a content edit -- the DOC006 findings disappear with
the file), or (b) if something still depends on it, document why and
route its own 10 DOC006 findings appropriately (likely the same
archival-record argument as `tickets-archive.md`, if the file is
genuinely a frozen historical snapshot rather than actively wrong).

Do NOT delete without confirming (a) first -- an active reader silently
losing its data source is worse than 10 warnings.
