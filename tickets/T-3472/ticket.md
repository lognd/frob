---
id: T-3472
title: Re-verify migrate_missing_v2's AFFECT001 waiver against docs/design/ledger-v2.md
state: queued
kind: docs
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_store_migrate.py
- docs/design/ledger-v2.md
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
follow-up split off T-2730: T-2730's scope named only migrate_to_ledger/migrate_v1_to_v2/_migrate_one_v2/_split_done_report's 4 tickets-data-storage.md anchors and their AFFECT001 waivers. migrate_missing_v2's own AFFECT001 waiver (src/frob/tickets/_store_migrate.py, cites the same T-2718 lease-conflict reason) targets docs/design/ledger-v2.md instead, a different doc not named in T-2730's scope -- verify that doc's content is still accurate post-extraction and remove the waiver if so.