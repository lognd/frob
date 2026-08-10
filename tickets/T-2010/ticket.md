---
id: T-2010
title: Populate frob.toml min_frob_version in this repo and the 8 sibling repos so
  T-1218's stale-binary warning actually fires
state: done
kind: docs
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- frob.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: frob.toml
  reason: populate min_frob_version key in this repo's frob.toml only, per coordinator
    scoping
  actor: logan
  at: '2026-08-10'
evidence:
- cmd:grep -n "min_frob_version" frob.toml exit=0 sha256=fffd1fe2e0ed
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
