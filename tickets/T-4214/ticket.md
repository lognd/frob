---
id: T-4214
title: 'frob:waive premise-expiry: a waiver whose reason names a branch/tree condition
  must carry a checkable predicate and fail once it no longer holds'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: critical
parent: T-4157
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
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
THREE INDEPENDENT ARRIVALS OF ONE MECHANISM, consolidated into one leaf rather than three: (1) T-4157/H4-1 -- a frob:waive reasoning 'the file is absent on this branch' kept suppressing OPAQUE001 after a merge made that false, and nothing re-evaluated it. (2) T-4175/P8 -- a WIRE001 waiver reasoning 'not yet wired' was never re-examined once a sibling caller landed elsewhere. (3) T-4135/F-317/L-2 -- SYS101 waived wholesale for a browser node because 'the code is on a branch', which makes a stale grant and a not-yet-landed grant indistinguishable once the branch in question (T-0002) clears. All three are the same shape: a waiver's justification is contingent on tree state, and nothing re-checks the condition. Fix: a waiver whose reason names a branch condition must carry that condition as a checkable predicate (e.g. a file-existence check, a call-graph reachability check) and fail once the predicate no longer holds. Not every waiver needs a predicate -- only those contingent on tree state; working out which reasons are contingent should be answered by reading this repo's own waiver reasons (hundreds of them) rather than theorising. Fixture-testable: YES, using frob's own frob:waive DSL and its own tree-state-contingent waivers as the honest sample.