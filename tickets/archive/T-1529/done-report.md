## Done report

Added three TestXCacheTransparency classes to tests/test_cache_transparency.py,
extending the shared run_cold_warm_sweep harness (tests/_cache_transparency.py,
T-1519) to the three caches INV-050's inventory table had left as a
disclosed cut:

- TestCoverageLockCacheTransparency: frob-coverage.lock.json. No
  in-process cache layer exists for load_coverage_lock today (uncached
  read-through) -- swept against arbitrary write/delete/corrupt rounds as
  a regression lock against a future cache layer disagreeing with a raw
  file read.
- TestHotgraphSketchCacheTransparency: .frob/hotgraph_sketches.db. This
  one has a REAL staleness risk -- _sketch_store._connect caches a live
  sqlite connection per resolved db path for the process lifetime. The
  sweep forces a cold reconnect (_close_all()) after every put_sketch
  round and asserts get_sketch reads back exactly what the still-open
  warm connection just wrote.
- TestBudgetTimingCacheTransparency: .frob/check-budget-timing.json.
  Same uncached-read-through shape as the coverage lock, including the
  "corrupt file degrades to {}, never a crash" contract, swept the same
  way.

Updated invariants/INV-050.md's inventory table and evidence list to
reflect all three as harness-covered rather than disclosed cuts -- the
doc's own closing paragraph now states the full inventory is covered,
closing out T-1519's original deliverable (3) in full.

### Changed
```
 invariants/INV-050.md            |  38 +++--
 src/frob/tickets/_store.py       | 192 +++++++++++++++++-----
 tests/test_cache_transparency.py | 204 +++++++++++++++++++++++-
 tests/test_ticket_land.py        |  85 ++++++++++
 tests/test_tickets.py            |  57 +++++++
 tickets.md                       | 336 +++++++++++++++++++++++++++++++++++++--
 6 files changed, 848 insertions(+), 64 deletions(-)
```

### Evidence
- `tests/test_cache_transparency.py::TestCoverageLockCacheTransparency::test_cold_warm_agree_across_random_edits` (pytest node id, verified passing when recorded)
- `tests/test_cache_transparency.py::TestHotgraphSketchCacheTransparency::test_cold_warm_agree_across_random_edits` (pytest node id, verified passing when recorded)
- `tests/test_cache_transparency.py::TestBudgetTimingCacheTransparency::test_cold_warm_agree_across_random_edits` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 226 warning(s), 791 waived
- error-findings: none (measured, zero errors)
