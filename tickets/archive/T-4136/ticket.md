---
id: T-4136
title: test_land_cmd_drain_wiring double missing target_branch kwarg (T-4105 producer/consumer
  desync)
state: done
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_land_cmd_drain_wiring.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_land_cmd_drain_wiring.py::TestRapidLandDrainWiring::test_real_rapid_land_spawns_both_sweep_and_drain
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-4130 (full tests/unit run). T-4105 added a required target_branch kwarg to spawn_deferred_post_land_sweep (src/frob/app/ticket_runner/_rapid_sweep.py) and the call site in src/frob/app/ticket_runner/_land_cmd.py::_land_core_finish_post_land now passes it. tests/unit/test_land_cmd_drain_wiring.py::TestRapidLandDrainWiring::test_real_rapid_land_spawns_both_sweep_and_drain monkeypatches spawn_deferred_post_land_sweep with a lambda of the old arity (root, ticket_id, final_id, commit_sha) and fails with TypeError: got an unexpected keyword argument 'target_branch'. Same producer/consumer desync class as T-4130's clusters 1-3 (a landed change updated a producer/call site and left a test double behind), out of T-4130's declared scope (different file, different ticket). Fix: update the lambda/double to accept target_branch (or **kwargs), matching what the real call site now passes.