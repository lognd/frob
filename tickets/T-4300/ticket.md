---
id: T-4300
title: SCOPE002 fans out unfixably on giant shared docs (tickets-landing.md)
state: queued
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_scope*.py
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
Discovered while working T-4184: any ticket touching a symbol whose frob:doc target lives in docs/modules/tickets-landing.md (a ~2500-line doc describing effectively the entire land subsystem) gets a real SCOPE002 finding ('add docs/modules/tickets-landing.md to scope'), but actually adding that file (or even a single #anchor fragment inside it) to the ticket's scope fans SCOPE002 out across ~500 UNRELATED symbols the same doc happens to describe elsewhere -- an under-capture false-positive storm far worse than the original finding. Measured directly on T-4184 touching _land_release.py::_apply_release_bump/_maybe_rebuild_natives: 0 extra SCOPE002 findings before touching the doc, ~500 after adding it to scope. Ended up waiving AFFECT001 on the touched functions instead of fixing SCOPE002 properly. SCOPE002 (or the scope-closure add flow) needs a way to scope a single doc ANCHOR without pulling in every OTHER anchor's own describes-edges in the same file, or the doc itself needs splitting into per-ticket-sized files.