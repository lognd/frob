---
id: T-3543
title: Fold the record-land-commit stub into the land itself (53 of last 300 commits)
state: queued
kind: feature
origin: human
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_land_finalize.py
- src/frob/app/ticket_runner/_land_cmd.py
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
53 of the last 300 main commits are "chore(tickets): record land commit
for T-x" -- pure bookkeeping trailing every land as its own commit. Fold
it: the land-sha record is DERIVABLE (git log --grep "land T-<id>" -F)
or can be written as part of the land's own final commit (the out-of-tree
compose builds the commit; write the ledger field against the composed
tree before publish, or record the PARENT sha + "next commit" marker).
Pick the design that keeps `frob ticket show`/land-proof verification
working (they read the recorded sha today -- update their readers to
derive when absent). MUST-STAY-QUIET: land-proof (is_ancestor_of_main,
state_on_main) still verifies for old tickets with recorded shas AND new
tickets without them. ACCEPTANCE: a land produces exactly ONE trailing
ledger commit or zero, never a dedicated record-land stub.
