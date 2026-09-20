---
id: T-4344
title: Update deferred-sweep doc for T-4335's baseline-persist contract
state: done
kind: docs
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
- docs/modules/tickets-verify-sweep.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- cmd:uv run frob check --ticket T-4344 exit=0 sha256=b69f65e5a1b2
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-4335: run_deferred_post_land_sweep's baseline-write contract changed (a new identity is only rolled into the rolling baseline once it is actually filed/accounted for; a refused-to-file identity, or the first-run establishing case, are handled distinctly now). The 'Deferred post-land sweep' section of this doc still describes the OLD 'every sweep, red or green, rewrites the baseline regardless' contract and needs updating to match. Out of T-4335's own scope because this doc's frob:describes network pulls in ~170 unrelated symbols across the whole verify/land subsystem on scope closure -- a disproportionate expansion for a one-section prose fix.