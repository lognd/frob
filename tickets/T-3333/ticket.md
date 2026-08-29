---
id: T-3333
title: REF001 fires on frob's own v2 ticket files under tickets/T-####/ (diax F-009)
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_refs.py
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
Found in ../diax FROBLEMS.md (F-009), noted while working T-3277. REF001 fires on frob's own v2 ticket tree (tickets/T-0001/ticket.md and siblings) -- T-3249 already exempted the flat tickets.md file, but this is the v2 per-ticket directory tree, adjacent but distinct, and was not covered by that exemption. Not independently re-verified in this ticket; filing per T-3277's own instructions to file rather than fold in. Someone should confirm against src/frob/gates/_refs.py's _DEFAULT_ROOT_MANIFEST_EXEMPT-equivalent for the tickets/ tree and extend it to the v2 per-ticket shape if confirmed live.