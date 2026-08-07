## Done report

REL200 waiver burn-down for elaborator-synthesized cache flows: the cache grammar has no attr clause, and by this grammar's design a cache is an in-process derived view inheriting its node's trust, so the elaborator now stamps the local attr on every synthesized cache fill/invalidation flow unconditionally (_CACHE_LOCAL_ATTR in src/frob/strata/_infra.py). The two REL200 waivers on the graphlang node are removed; a new reliability test proves REL200 stays silent on cache flows with no waiver declared.

### Changed
```
 design/frob.strata                    |  16 ++---
 src/frob/strata/_infra.py             |  36 +++++++++--
 tests/unit/strata/test_infra.py       |   5 ++
 tests/unit/strata/test_reliability.py |  30 +++++++++
 tickets.md                            | 117 +++++++++++++++++++++++++++++++++-
 5 files changed, 191 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/unit/strata/test_infra.py::TestCacheDesugar::test_cache_node_and_fill_flow` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestMissingTimeout::test_cache_fill_and_invalidation_flows_are_local_exempt` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
