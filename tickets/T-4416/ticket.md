---
id: T-4416
title: 'Profile semantics: rapid=scoped-synchronous, standard=unscoped-synchronous'
state: queued
kind: feature
origin: human
created: '2026-09-11'
priority: high
blocked_by:
- T-4413
parent: T-4410
tier: story
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/cli_doctor*
- src/frob/app/cli_init*
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN the rapid and standard land profiles WHEN documented THEN rapid is described
    as scoped-synchronous (diff-plus-dependents) and standard as unscoped-synchronous
    (full check), matching their actual post-T-4413 behavior
  evidence: []
- text: GIVEN frob doctor or frob init runs on a repo above a measured size threshold
    (ticket count or file count) WHEN it evaluates land profile THEN it recommends
    rapid, citing the measured cost numbers (25-45 min unscoped check at ~4200 tickets/~1400
    files, T-4408's 50+ min)
  evidence: []
- text: GIVEN a repo below the threshold WHEN doctor/init evaluates profile THEN it
    does not force rapid, leaving standard as a reasonable default for small projects
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Owner design decision (2026-09-11) plus T-4413's scoped rapid sweep changes what 'rapid' means. Rename or document rapid as scoped-synchronous and make standard the unscoped-synchronous profile for small projects. frob doctor / frob init should recommend rapid above a measured repo size threshold, citing this repo's measured unscoped-check costs (25-45 min at ~4200 tickets/~1400 files; T-4408 land: 50+ min single-thread).