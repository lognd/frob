## Done report

Batches and rate-limits the post-land sweep. See body for full detail.

### Changed
```
 src/frob/app/ticket_runner/_rapid_sweep.py  | 562 ++++++++++++++++++++++++++--
 tests/unit/rapid_sweep_suite/test_window.py | 457 ++++++++++++++++++++++
 tickets/T-4414/ticket.md                    |  33 +-
 3 files changed, 1013 insertions(+), 39 deletions(-)
```

### Evidence
- `tests/unit/rapid_sweep_suite/test_window.py::TestSpawnDeferredPostLandSweepBatches::test_two_lands_in_one_window_spawn_exactly_one_worker` (pytest node id, verified passing when recorded)
- `tests/unit/rapid_sweep_suite/test_window.py::TestRunOneSweepBatch::test_anchors_on_the_batchs_own_last_land` (pytest node id, verified passing when recorded)
- `tests/unit/rapid_sweep_suite/test_window.py::TestSpawnDeferredPostLandSweepBatches::test_land_while_sweep_running_never_spawns_a_second_worker` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 4916 warning(s), 968 waived
- error-findings: SELFAUDIT001@tests/unit/rapid_sweep_suite/test_window.py, TICK010@/home/logan/projects/frob/.git/frob-leases/T-draft-926571db.json
