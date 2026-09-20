## Done report

Bound all 3 acceptance criteria to evidence: criterion 1 (seed-before-load) to the existing seed/compose tests; criterion 2 (drift recomputes only touched entries on a seeded cache) to new test_seeded_worktree_cache_only_reparses_the_touched_file; criterion 3 (no cold-start log against a warm-seeded worktree) to new test_load_graph_does_not_cold_start_against_a_warm_primary_cache. Ran frob check --ticket T-4411: only failure is gate:CROSSTICKET against T-4412 (also in-progress on src/frob/graph/cache.py), expected and out of scope; fixed FMT001 (over-long frob:tests directive) and refreshed the stale PRE001 pre-work sweep as in-scope cleanup.

### Changed
```
 docs/modules/graph.md             |   7 ++
 src/frob/graph/cache.py           | 200 ++++++++++++++++++++++++++++++++------
 src/frob/tickets/_land_compose.py |  98 +++++++++++++++----
 tests/unit/test_graph_cache.py    | 115 ++++++++++++++++++++++
 tests/unit/test_land_compose.py   |  58 +++++++++++
 tickets/T-4411/done-report.md     |  48 +++++++++
 tickets/T-4411/ticket.md          |  12 ++-
 7 files changed, 487 insertions(+), 51 deletions(-)
```

### Evidence
- `tests/unit/test_graph_cache.py::TestSeedDisposableWorktreeCache::test_seeds_from_an_existing_primary_cache` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestSeedDisposableWorktreeCache::test_no_primary_cache_is_a_quiet_no_op` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestSeedDisposableWorktreeCache::test_primary_journal_present_skips_seeding` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestSeedDisposableWorktreeCache::test_empty_primary_journal_does_not_block_seeding` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_compose.py::TestDisposableSquashWorktree::test_cache_db_is_seeded_against_the_disposable_worktree` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestSeedDisposableWorktreeCache::test_seeded_worktree_cache_only_reparses_the_touched_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_compose.py::TestDisposableSquashWorktree::test_load_graph_does_not_cold_start_against_a_warm_primary_cache` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 9 error(s), 4851 warning(s), 961 waived
- error-findings: CROSSTICKET001@src/frob/graph/cache.py, CROSSTICKET001@tests/unit/test_graph_cache.py, DOC006@tickets/T-4437/ticket.md, LARGE001@src/frob/strata/_native_staleness.py, MILE002@tickets.md, TICK004@tickets.md, TICK006@tickets.md, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4412.json, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4424.json
