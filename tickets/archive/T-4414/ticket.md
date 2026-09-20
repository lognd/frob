---
id: T-4414
title: 'Post-land sweep: detached, batched, rate-limited'
state: done
kind: feature
origin: human
created: '2026-09-11'
priority: high
parent: T-4410
tier: story
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/verify
- tests/unit/rapid_sweep_suite
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/rapid_sweep_suite
  reason: ticket's own declared scope; test files for the new window-batching logic
    in _rapid_sweep.py
  actor: logan
  at: '2026-09-15'
evidence:
- tests/unit/rapid_sweep_suite/test_window.py::TestSpawnDeferredPostLandSweepBatches::test_two_lands_in_one_window_spawn_exactly_one_worker
- tests/unit/rapid_sweep_suite/test_window.py::TestRunOneSweepBatch::test_anchors_on_the_batchs_own_last_land
- tests/unit/rapid_sweep_suite/test_window.py::TestSpawnDeferredPostLandSweepBatches::test_land_while_sweep_running_never_spawns_a_second_worker
designated_repro_test: null
acceptance:
- text: GIVEN two lands complete within one rate-limit window WHEN the post-land sweep
    is triggered THEN exactly one detached sweep process is spawned covering both
    lands, not one per land
  evidence:
  - tests/unit/rapid_sweep_suite/test_window.py::TestSpawnDeferredPostLandSweepBatches::test_two_lands_in_one_window_spawn_exactly_one_worker
- text: GIVEN a repo-wide finding surfaces in a batched sweep WHEN it fires THEN a
    ticket is still filed for it, attributed to the batch rather than a single land
  evidence:
  - tests/unit/rapid_sweep_suite/test_window.py::TestRunOneSweepBatch::test_anchors_on_the_batchs_own_last_land
- text: GIVEN the sweep is running WHEN a new land completes THEN it does not spawn
    a second concurrent sweep; it either joins the pending batch window or is deferred
    to the next window
  evidence:
  - tests/unit/rapid_sweep_suite/test_window.py::TestSpawnDeferredPostLandSweepBatches::test_land_while_sweep_running_never_spawns_a_second_worker
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Owner design decision (2026-09-11): land proves the diff; the unscoped repo-wide sweep must not run synchronously per land. Move the existing post-land sweep off the per-land synchronous path onto a detached, batched schedule (one sweep per N lands or per time window), rate-limited so concurrent lands do not each spawn their own full sweep. Repo-wide findings are still filed as tickets.