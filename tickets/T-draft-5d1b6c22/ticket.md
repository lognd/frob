---
id: T-draft-5d1b6c22
title: Land queue default keyed on live-lease count, sync opt-out (--sync, ticket_land_default=sync),
  documented config key fixed
state: queued
kind: feature
origin: human
created: '2026-09-21'
priority: high
parent: T-5106
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/config.py
- src/frob/_cli_parsers/_ticket/_progress.py
- docs/modules/tickets-landing.md
- tests/unit/test_land_default_queue.py
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
Leaf A of T-5106 (~2 pts). Default and opt-out.
- `ticket_land_default` defaults to "queue" whenever more than one live lease exists in .git/frob-leases (compose the predicate from `orphaned_leases`/`lease_staleness_reason` in frob.tickets._leases, dead holders excluded); a single-lease repo keeps the synchronous land so a solo developer never pays daemon latency.
- Opt-out: `ticket_land_default = "sync"` in `[tool.frob]` and an explicit `--sync` mode flag in `_dispatch_land_mode`'s ladder (explicit flag always wins, as today). `--dry-run` stays never-promoted.
- Fix the doc/docstring key spelling: `land_default` is documented (config.py, docs/modules/tickets-landing.md) but the loader merges `[tool.frob]` by AppConfig field name, so only `ticket_land_default` works. Document the real key and add a test that the documented key round-trips.
- Tests in tests/unit/test_land_default_queue.py: lease-count promotion, sync opt-out, explicit flag precedence, documented-key round-trip.
