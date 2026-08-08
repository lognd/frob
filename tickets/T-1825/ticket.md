---
id: T-1825
title: Document frob ticket wave in docs/modules/tickets.md once the lease frees
state: queued
kind: docs
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/tickets.md
- src/frob/tickets/_doable.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
## Description

T-1738 (`frob ticket wave --agents N`) landed the code (src/frob/tickets/_doable.py's `wave`/`WaveGroup`/`WaveResult`/`WaveRemainderReason`, CLI wiring in `_cli_parsers/_ticket/_query.py` and `app/ticket_runner/{_query.py,__init__.py}`) without a docs/modules/tickets.md#public-api section, because that page was under a T-1686/T-1736 lease for the whole span T-1738 was worked.

## Plan

Once docs/modules/tickets.md frees: add a `wave` subsection next to `doable`/`doable_blocked` describing the partition algorithm (union-scope disjointness across groups, intra-group collision is fine, remainder semantics), then add the `frob:doc docs/modules/tickets.md#public-api` directive back onto `wave()` in src/frob/tickets/_doable.py.

## Acceptance

- [ ] docs/modules/tickets.md has a `wave` section under public-api
- [ ] `wave()` carries a `frob:doc` edge to it
- [ ] `frob check` reports no doc-coverage finding for `wave`/`WaveGroup`/`WaveResult`/`WaveRemainderReason`
