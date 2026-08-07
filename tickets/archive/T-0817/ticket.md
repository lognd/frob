---
id: T-0817
title: 'vet: wire net_enabled kill-switch into vet''s network call sites (LINT004
  net gap)'
state: dropped
kind: security
origin: agent
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN FROB_DISABLE_NET=1 (or the guard's net flag) WHEN any vet code path
    attempts a network operation THEN it is refused and logged without connecting;
    the vet strata node declares the net kill-switch flag and its LINT004 waiver is
    deleted
  evidence: []
threat: denial-of-service
component: null
---
The net kill-switch mechanism exists (T-0200 frob.process._guard.net_enabled) but no call site invokes it; vet's strata node holds may-net with a LINT004 waiver that previously cited T-0803 (exec-only sweep, now closed). Wire net_enabled into vet's network paths, declare attr flag on the node, delete the waiver.

## Drop reason
- 2026-07-23: absorbed: the vet net kill-switch wiring landed as T-0822 (worked from a worktree draft filed when a ledger restore predated T-0817's filing); design flag declared, waiver deleted, sys audit PROVED (absorbed by T-0822)