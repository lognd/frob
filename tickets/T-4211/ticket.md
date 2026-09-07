---
id: T-4211
title: exported check*/*Check symbol with no reference from a declared entrypoint
  list is a finding; PUBLIC_ALLOWLIST-shaped invariants are its concrete instance
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates
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
Consumer F-317/H-1 (T-4135 sub-epic, shell round-3). frob check has no notion of 'this module exports a check*/*Check gate that no entry point calls'. A rule flagging an exported check*/*Check symbol in a scripts dir with no reference from a package manifest's script list would have caught both halves of the finding; the allowlist-desync half is a concrete instance of frob:invariant PUBLIC_ALLOWLIST == git ls-files <dir>, which the code already states in prose. Fixture-testable: partially -- the entrypoint-reference check is generic and testable against frob's own scripts/CLI; the specific allowlist-invariant shape is consumer-only.