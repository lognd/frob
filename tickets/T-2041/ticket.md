---
id: T-2041
title: 'docs/modules/tickets.md: document T-2023''s land-wait budget config + start-relative
  scaling'
state: in-progress
kind: docs
origin: agent
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- cmd:grep -n "Land-wait budget config and start-relative scaling" docs/modules/tickets.md
  exit=0 sha256=2b6b8f72a649
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-2023 added `_load_land_wait_timeout_s`, `_land_lock_started_at`, and
`_resolve_land_wait_budget` to `src/frob/tickets/_leases.py` (the land-wait
budget now scales to the in-flight land's own recorded start time, and is
configurable via `frob.toml`'s `[tickets] land_wait_timeout_s`), but could
not add `docs/modules/tickets.md` to scope -- T-2025 held a live write
lease on that file at the time. Add a short note to
`docs/modules/tickets.md#land-exclusivity-lease-t-1619` documenting the
new config key and the land-start-relative wait scaling once the lease
clears.
