---
id: T-0272
title: 'std.host: OS-group and sudoers-grant vocabulary'
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- strata-core/src/parse.rs
- src/frob/strata/**
- docs/strata/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_host_isolation.py::TestLateralIsolation::test_disjoint_groups_do_not_fire_shared_group
- tests/unit/strata/test_host_isolation.py::TestVerticalIsolation::test_sudoers_does_not_fire_when_undeclared
- tests/unit/strata/test_litmus_host_isolation.py::TestHostIsolationHardenedLitmus::test_isolated_model_discharges
designated_repro_test: null
threat: null
component: null
---
T-0256's HOST001 (shared-group sub-target) and HOST002 (sudoers sub-target) cannot structurally prove these two sub-targets because std.host (T-0255) carries no OS-group or sudoers-grant grammar -- both ALWAYS fire (deny-by-default, honest gap) until an explicit waive is written or this ticket adds the grammar. Add: a repeatable 'group "NAME"' owns-adjacent clause (desugars to a group=NAME attr, mirroring runs_as) and a 'sudoers "RULE"' clause (desugars to sudoers=RULE, repeatable) to strata-core/src/parse.rs's parse_node/parse_store, HostManifest gains group: tuple[str,...] and sudoers: tuple[str,...] fields (_host.py), then HOST001's shared-group and HOST002's sudoers sub-targets in _host_isolation.py derive real findings instead of the always-fire placeholder.