## Done report

Root cause confirmed exactly as suspected: `frob.tickets._store`'s v2
index cache (`_read_index_cache`/`_write_index_cache`) keyed staleness
on `st_mtime_ns` alone. `new_ticket` followed microseconds later by
`drop_ticket` against the same fresh ticket file can land two writes
within the SAME filesystem timestamp tick -- confirmed via captured
DEBUG logs on a live repro: a "v2 index cache hit (1 ticket(s))" read
right after drop_ticket's write served the PRE-DROP ("queued") cached
content with no preceding "stale" log line at all, because the second
write's mtime_ns matched the cache's already-recorded value from the
first write's rebuild.

Changed:
- src/frob/tickets/_store.py::_stat_key -- new helper, `[mtime_ns,
  size]` pair for one path.
- src/frob/tickets/_store.py::_read_index_cache -- staleness key now
  `(mtime_ns, size)` per path, not `mtime_ns` alone; a pre-T-2100 cache
  file (bare-int entries) is treated as a miss, not a crash.
- src/frob/tickets/_store.py::_write_index_cache -- writes `[mtime_ns,
  size]` pairs to match.

Evidence:
- tests/test_tickets.py::TestV2IndexCache::test_same_mtime_different_size_is_not_a_hit
  (designated repro; FAILED_AT_PARENT confirmed at 2cc476b1d, the
  test-only commit, via `os.utime` pinning both writes to an identical
  mtime_ns -- deterministic, not dependent on real clock granularity)
- tests/test_tickets.py::TestV2IndexCache::test_identical_mtime_and_size_still_hits_cache
  (negative control: an unchanged file must still serve from cache)
- tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_terminal_ticket_is_not_selected_and_logs_no_invalid_transition
- tests/unit/test_rapid_sweep.py::TestRevalidateDispatchableSweepTickets::test_fully_resolved_candidate_is_dropped
  (the originally-flaky pair -- measured ~1/20 failing before the fix,
  40/40 clean after, run back-to-back in the same pytest process both
  orders)

Filed: none -- no out-of-scope work found.

Gates: tests/test_tickets.py + tests/unit/test_rapid_sweep.py full
files, 296 passed, 0 failed locally. `frob check` pending at land time.
