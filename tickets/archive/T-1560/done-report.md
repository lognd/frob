## Done report

Post-T-1555 full re-measure found 26 gate errors on main; this ticket
closes every one of them. Two (PRE001/SCOPE001 on tickets-archive.md)
were an uncommitted archive artifact, fixed by committing it on main
before this worktree branched. Two COV003s (archived T-1269/T-1495
evidence pointing at tests renamed by wave-4 unwind-semantics work) were
fixed on main directly via an exact-string swap in tickets-archive.md,
because evidence --replace cannot reach archived tickets -- that tooling
gap is filed as T-1561.

In this worktree:

- 16 WIRE002 errors: frob:waive WIRE001 directives across 8 test files
  named T-1490 (15) and T-1488 (1), both closed by wave-4 lands; WIRE002
  requires waivers to bind an OPEN ticket. All 16 rebind to T-1558, the
  filed successor/waiver-home for the module-local-test-helper WIRE001
  class. No waiver was deleted -- follow_up attribution only. The
  systemic prevention (close/land must refuse or auto-migrate waivers
  bound to the closing ticket) is filed as T-1559.
- ARCH001 on src/frob/tickets/_land.py::_land_plan_locked (67 lines):
  the dry-run/report success tail extracts into _land_plan_finish, a
  genuine unit (report construction + dry-run always-reset semantics)
  with its own docstring; T-1522 unwind semantics unchanged, covered by
  the bound TestLandPlan evidence.
- ARCH001 on src/frob/tickets/_store.py::v2_state_transitions (77
  lines): the per-lineage-segment git-log mining extracts into
  _mine_v2_path_transitions with a local flush() closing over the
  commit/state scan state; oldest-first ordering and cross-segment sha
  dedup preserved, covered by the three bound TestV2StateTransitions
  evidence ids.
- PERF001 at _store.py:790: _v2_path_lineage kept an ordered list but
  did membership tests against it inside the walk loop; a parallel seen
  set now answers membership, the list keeps ordering.
- 3 PII012 suggestions in tests/unit/test_dup_legacy_cpp.py: 'token'
  there is the dup-fingerprint lexer's positional _vN token, not a
  credential surface; reasoned frob:waive PII012 directives added above
  the two owning tests.

frob check --land-parity in this worktree: clean, 0 unscoped errors --
matches what the land sweep will evaluate. Targeted suites green:
tests/test_tickets.py + tests/test_ticket_land.py -k "V2StateTransitions
or LandPlan" (11 passed); ruff check/format clean; ty clean on both
touched source files.

Changed:
  src/frob/tickets/_land.py::_land_plan_locked (shrunk)
  src/frob/tickets/_land.py::_land_plan_finish (new private helper)
  src/frob/tickets/_store.py::v2_state_transitions (shrunk)
  src/frob/tickets/_store.py::_mine_v2_path_transitions (new private helper)
  src/frob/tickets/_store.py::_v2_path_lineage (seen set)
  tests/_cache_transparency.py, tests/test_cache_gate.py,
  tests/test_cache_transparency.py, tests/test_ticket_land.py,
  tests/test_tickets_migration.py, tests/unit/perf/test_hotpath_smells.py,
  tests/unit/perf/test_serial_pools_import_failure.py,
  tests/unit/test_coverage_attribution_lock_t1395.py (follow_up rebinds)
  tests/unit/test_dup_legacy_cpp.py (2 reasoned PII012 waivers)

### Changed
```
 src/frob/tickets/_land.py                          |  25 +++++
 src/frob/tickets/_store.py                         |  98 ++++++++++--------
 tests/_cache_transparency.py                       |   6 +-
 tests/test_cache_gate.py                           |   2 +-
 tests/test_cache_transparency.py                   |   2 +-
 tests/test_ticket_land.py                          |   2 +-
 tests/test_tickets_migration.py                    |  12 +--
 tests/unit/perf/test_hotpath_smells.py             |   2 +-
 .../unit/perf/test_serial_pools_import_failure.py  |   4 +-
 tests/unit/test_coverage_attribution_lock_t1395.py |   2 +-
 tests/unit/test_dup_legacy_cpp.py                  |   6 ++
 tickets.md                                         | 112 +++------------------
 12 files changed, 114 insertions(+), 159 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestV2StateTransitions::test_transitions_mined_oldest_first` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestV2StateTransitions::test_no_history_returns_empty_tuple` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestV2StateTransitions::test_byte_similar_sibling_ticket_does_not_drop_transitions` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandPlan::test_tick_gate_dirty_unwinds_finalize_but_keeps_the_durable_merge` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 258 warning(s), 784 waived
- error-findings: none (measured, zero errors)
