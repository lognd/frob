---
id: T-1517
title: 'coverage: per-file content-hash incremental caching layer'
state: done
kind: feature
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/**
- src/frob/gates/_coverage.py
- tests/test_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_coverage.py::TestCoverageFileCache::test_load_missing_returns_empty
- tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_backfills_unchanged_file
- tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_ignores_stale_hash
- tests/test_coverage.py::TestCoverageFileCache::test_fill_from_cache_never_overwrites_fresh_data
- tests/test_coverage.py::TestCoverageFileCache::test_update_file_cache_persists_measured_files
- tests/test_coverage.py::TestCoverageFileCache::test_update_file_cache_roundtrips_through_fill_from_cache
designated_repro_test: null
threat: null
component: null
---
T-1205 acceptance[2] (per-file content-hash keyed incremental caching, so
an unchanged file's coverage is never recomputed even across separate
touched-set runs). T-0484's python_coverage_targets already selects
WHICH tests the touched set obligates; coverage-fast (Makefile, T-1397)
already restricts the pytest run to that selection with --cov-append.
Neither keys per-file coverage data by content hash or persists a
cache the way frob.graph's own cache does -- this ticket is that
missing layer: a per-file (or per-module) coverage cache keyed by
source content hash, so a file whose hash has not changed since its
last real measurement is never re-instrumented even indirectly, and a
combine/merge step reconciles cached entries with freshly measured
ones into the single coverage.xml / frob-coverage.lock.json TEST005/
TEST006 read. Filed as a real ticket after the original T-1205 session's
Done report cited draft ids T-1487/T-1488 for this and the native-
command follow-up; both ids were later reused by unrelated tickets
during a ledger renumber, so the follow-up work they described was
never actually tracked. This ticket re-files the caching half.
</content>