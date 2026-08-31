---
id: T-3527
title: implement growth-rate grammar for frob sys capacity --at DATE
state: queued
kind: feature
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
- docs/strata/kernel.md
- docs/strata/reliability.md
- src/frob/strata/_capacity.py
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
T-2016 (done) produced only the DESIGN for a growth-rate declaration on Node.users/rate (docs/strata/kernel.md#growth-rate-declarations-t-2016) -- the grammar itself was never implemented, so frob sys capacity --at DATE (docs/strata/reliability.md's own Disclosed scope cut section) remains not yet implemented with no ticket currently tracking the implementation. Found while reviewing NEGEXIST001 for T-3519 (a doc claim needs a real frob:until binding, and none existed). Build the growth-rate grammar per T-2016's design and wire --at DATE into project_capacity.