---
id: T-2739
title: verify T-2481/T-1943 COV005 waivers against T-2720's narrowed detector, remove
  any that no longer reproduce
state: queued
kind: docs
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/root-write-guard.py
- src/frob/gates/_coverage_sites.py
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
T-2720 narrowed COV005's rebind detection: a new private edge under an old public binding's (kind,target) key is only flagged when the old public qualname's OWN edge for that key is gone (genuine displacement), not merely because SOME other symbol reuses the same shared anchor. The 18 frob:waive COV005 sites in .claude/hooks/root-write-guard.py (T-2481) and 4 in src/frob/gates/_coverage_sites.py (T-1943) all cite exactly this anchor-reuse false-positive shape in their reasons. COV005 is diff-hunk-scoped, so it cannot be re-evaluated against already-landed, already-squashed history directly -- verify each site by constructing a synthetic diff/hunk covering it (or reverting-then-reapplying the relevant hunk in a scratch branch) against the narrowed detector, and remove any waiver whose finding no longer reproduces, per this repo's own waiver-removal discipline (a removal must be backed by a measurement, not an assumption).