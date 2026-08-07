## Done report

Added `src/frob/testing/_coverage_cache.py` (T-1517): a persisted, per-file
content-hash keyed coverage cache at `.frob/coverage-file-cache.json`,
mirroring `frob.graph.cache`'s content-hash cache-invalidation pattern
(T-1464's `parsed_artifacts` table is the closest sibling, but this is a
single small JSON document, not a sqlite table -- coverage percentages are
a handful of small floats per file, not whole parsed-file payloads).

Three public functions: `load_file_cache` (read, `{}` on cold start),
`fill_from_cache` (backfill a freshly loaded `CoverageData.module_line`
for every file this run did NOT itself measure but whose current content
hash still matches the cache -- never overwrites data the run actually
measured), `update_file_cache` (persist every measured file's
`(content_hash, line_pct)`, merged with the existing cache so an
untouched file's entry survives a narrower run).

Wired into `frob.gates._coverage.stamp_coverage` (via
`_filtered_coverage_or_deflated`): the cache fill runs on every stamp,
BEFORE the T-1180/T-1435/T-1236 deflation/provenance/canary checks, so a
touched-set `--cov-append` run's narrower `coverage.xml` -- which
structurally cannot re-measure files it did not execute -- reads as "not
deflated" for files whose content genuinely has not changed, instead of
those files silently vanishing from `module_line` or forcing a full-suite
run just to keep the join fraction up. `update_file_cache` runs after a
successful `write_coverage_lock` so the cache always reflects the
freshest per-file numbers for the next stamp, incremental or full. Both
calls are deferred (function-local) imports from `frob.gates._coverage`
into `frob.testing._coverage_cache` -- `frob.testing`'s package `__init__`
already imports `_coverage_wait`, which imports `frob.gates._coverage`
(`load_stamp`) at module level, so a module-level import the other
direction would close a real import cycle during `frob.gates` package
init; verified by re-running the fresh-collection pytest suite after
adding the deferred-import fix (no ImportError).

This directly implements T-1205 acceptance[2] ("GIVEN an unchanged file
THEN its coverage is never recomputed: per-file coverage keyed by content
hash, full-suite runs reserved for cold start or explicit --full") for the
CACHING half; T-1516 (sequenced after this ticket) is the native
orchestration command that decides WHEN to run full vs. touched-set and
is what "full-suite runs reserved for cold start" ultimately depends on
end-to-end -- this ticket supplies the persistence layer that makes an
incremental run's coverage.xml honest once that orchestration exists.

design/frob.strata: added `frob:ticket T-1517` to both the `core` and
`testsuite` nodes (COV002), three new `interface=` attrs on `core`
(`fill_from_cache`, `load_file_cache`, `update_file_cache`), one on
`testsuite` (`TestCoverageFileCache`), and
`src/frob/testing/_coverage_cache.py` to both the `fs.read`/`fs.write`
`may ... via` lists (SELFAUDIT SYS100/SYS104) -- `frob check --only sys`
went from 6 errors to 0 after these.

No code outside `src/frob/testing/**`, `src/frob/gates/_coverage.py`,
`tests/test_coverage.py`, and `design/frob.strata` (the implicit
sweep-obligation surface every ticket touching public symbols/capability
effects must update) was touched.

### Changed

### Changed
```
 design/frob.strata                    | 859 +++++++++++++++++-----------------
 docs/modules/gates.md                 |  66 +++
 docs/modules/testing.md               |  69 +++
 src/frob/gates/_coverage.py           |  29 ++
 src/frob/testing/__init__.py          |  14 +
 src/frob/testing/_coverage_cache.py   | 191 ++++++++
 src/frob/testing/_coverage_refresh.py | 292 ++++++++++++
 src/frob/testing/_coverage_wait.py    | 163 ++++---
 tests/test_coverage.py                | 248 +++++++++-
 tickets.md                            | 403 +++++++++++++++-
 10 files changed, 1840 insertions(+), 494 deletions(-)
```

### Evidence
- `tests/test_coverage.py::TestCoverageFileCache::test_load_missing_returns_empty` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_backfills_unchanged_file` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_ignores_stale_hash` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_never_overwrites_fresh_data` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageFileCache::test_update_file_cache_persists_measured_files` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageFileCache::test_update_file_cache_roundtrips_through_fill_from_cache` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
