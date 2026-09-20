## Done report

Changed: cache.py's two recovery loops that consult
_is_stale_or_corrupt_connection (_run_with_stale_reconnect and
_recover_fingerprint_connection) previously treated "database disk
image is malformed"/"database is corrupted" identically to a sibling's
transient atomic-replace shapes ("no such table", "disk i/o error"):
blind reopen-and-retry at the same path, then re-raise the same error
forever once the retry budget ran out. That can never fix genuine
on-disk corruption -- reopening reads the same bad bytes. New helpers
_is_genuine_corruption_shape/_cache_integrity_ok/_rebuild_because_corrupt
distinguish the two classes, verify via PRAGMA integrity_check (never
trust the message alone), and on confirmed corruption rebuild via the
existing _recreate atomic quarantine-and-replace machinery, logged at
ERROR so the run says so.

Investigation: the cache KEY already covers file content correctly
(files.content_hash, checked in frob.graph.__init__._process_source_file
before ever trusting a stat-only hit; parsed_artifacts is keyed by
(content_hash, fingerprint)) -- the consumer-reported "stale finding
survives a fix" shape (b) was NOT reproduced in this cache's own keying;
this ticket's own live measurement (a, structural corruption) was
confirmed and reproduced live in this checkout (2026-09-09,
store_file_data on tests/test_gates_ratchet.py: "database disk image is
malformed" from frob serve's long-lived connection, pid 989). The
concurrency question: this checkout runs frob serve as a long-lived
daemon holding one connection for its whole lifetime alongside many
short-lived `frob check` processes opening/closing around cache.db --
the exact shape T-3644's own history (SIGBUS, WAL->TRUNCATE) already
flags as this module's known-fragile axis; not re-litigated further
here (out of this ticket's tight scope), but the self-heal this ticket
adds means that axis can no longer wedge the cache permanently once it
does corrupt something.

Evidence: tests/unit/test_graph_cache.py::TestCorruptCacheSelfHeals
  .test_integrity_check_reports_corrupt (acceptance 3: detection)
  .test_corrupt_cache_self_heals (rebuild helper in isolation)
  .test_run_with_stale_reconnect_rebuilds_and_completes_on_corruption
    (acceptance 1 MUST-FIRE: an already-open connection that hits the
    corruption shape mid-operation completes against a rebuilt cache
    instead of raising forever)
  .test_healthy_cache_never_triggers_a_rebuild (acceptance 2
    MUST-STAY-QUIET: a healthy cache is never rebuilt)
Full tests/unit/test_graph_cache.py: 41 passed. tests/test_graph.py:
147 passed.

Filed: none

Gates: ruff-check/ruff-format clean on touched files.

### Changed
```
 src/frob/graph/cache.py        | 128 ++++++++++++++++++++++++++++++++++++-
 tests/unit/test_graph_cache.py | 140 +++++++++++++++++++++++++++++++++++++++++
 tickets/T-4159/ticket.md       |  16 +++--
 3 files changed, 279 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_graph_cache.py::TestCorruptCacheSelfHeals::test_integrity_check_reports_corrupt` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestCorruptCacheSelfHeals::test_run_with_stale_reconnect_rebuilds_and_completes_on_corruption` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestCorruptCacheSelfHeals::test_healthy_cache_never_triggers_a_rebuild` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestCorruptCacheSelfHeals::test_corrupt_cache_self_heals` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
