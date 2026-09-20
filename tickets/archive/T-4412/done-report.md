## Done report

connect()'s _read_schema_version classified a busy/locked sqlite
connection (sqlite3.OperationalError: database is locked, T-3644's
readonly-database sibling included) identically to genuine
corruption: it logged "unreadable db, rebuilding" and fell through to
a second blocked probe (SELECT 1) that itself hit the same lock and
triggered _recreate -- destroying and rebuilding a perfectly good
cache under nothing but contention. Verbatim from today's incident:
"cache.connect: unreadable db at .frob/cache.db, rebuilding: database
is locked".

Fix: _read_schema_version now re-raises a transient lock error
instead of treating it as unreadable, and connect() wraps that read
in the same _with_lock_retry bounded busy-wait/backoff every other
cache path already gets -- resolving to a successful read once the
lock clears, or CacheLocked (naming the holding pid via the existing
_describe_lock_holders helper) once the retry budget is exhausted.
Genuine corruption (a different DatabaseError shape, T-4159's target)
is unaffected and still self-heals via rebuild.

Composition with T-4402 (landed first, same file): T-4402 touches
_rebuild_if_genuinely_corrupt/_run_with_stale_reconnect (the
already-open-connection mid-session corruption path); this ticket
touches _read_schema_version/connect() (the fresh-open schema-version
read). Disjoint call paths, no interaction; re-applied my saved patch
on top of current main and it applied cleanly with no conflicts.

Evidence (all 3 acceptance criteria bound via
`frob ticket evidence --accepts`):
[1]+[2] tests/unit/test_graph_cache.py::TestLockedDbNeverRebuilds::test_locked_db_is_never_classified_as_unreadable
  -- real second sqlite3 connection holding BEGIN EXCLUSIVE, asserts
  no _recreate call, inode unchanged, no cache.db.stale-* sidecar.
[2] tests/unit/test_graph_cache.py::TestLockedDbNeverRebuilds::test_lock_exhaustion_raises_cache_locked_naming_the_holder
  -- a lock that never clears raises CacheLocked (never a rebuild).
[3] tests/unit/test_graph_cache.py::TestLockedDbNeverRebuilds::test_genuinely_malformed_db_still_rebuilds
  -- positive control: a non-sqlite file still self-heals via
  connect()'s pre-existing T-0141 recreate path.

check-repro note: `frob ticket evidence --check-repro` reports
TEST_ABSENT_AT_PARENT (T-2025's documented structural limitation --
test and fix committed together, no ref has test-without-fix).
Verified manually instead: reverting just the
_read_schema_version re-raise (keeping everything else, including the
test file) made the TestLockedDbNeverRebuilds suite hang past a 120s
budget -- the pre-fix double-blocked-probe behavior this ticket
exists to close -- confirming the tests exercise real behavior.
Restored the fix; full suite passes again (exitstatus=0, 3/3).

Gates: `frob check --ticket T-4412` across gates-fast/lint show 0
errors attributable to this diff (fixed FMT001 directive wrapping
along the way); remaining errors are pre-existing repo-wide (DOC011
T-4313, MILE001/MILE002, TICK004/TICK006/TICK010). `frob test`
(touched set): 12/12 pass. Also ran the full TestCorruptCacheSelfHeals
+ TestLockedDbNeverRebuilds suite (8/8), tests/test_graph_lock.py +
tests/unit/test_graph_lock_holder_naming.py + tests/test_graph.py
(187/187) to confirm no regression in the surrounding lock-retry/
corruption-recovery machinery.

Filed: none.

### Changed
```
 src/frob/graph/cache.py        |  56 ++++++++++++++++++-
 tests/unit/test_graph_cache.py | 118 +++++++++++++++++++++++++++++++++++++++++
 tickets/T-4412/ticket.md       |  16 ++++--
 3 files changed, 184 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_graph_cache.py::TestLockedDbNeverRebuilds::test_locked_db_is_never_classified_as_unreadable` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestLockedDbNeverRebuilds::test_genuinely_malformed_db_still_rebuilds` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestLockedDbNeverRebuilds::test_lock_exhaustion_raises_cache_locked_naming_the_holder` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 8 error(s), 4809 warning(s), 961 waived
- error-findings: DOC011@docs/modules/tickets-lifecycle.md, LARGE001@src/frob/testing/_collect.py, MILE001@tickets.md, MILE002@tickets.md, TICK004@tickets.md, TICK006@tickets.md, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4417.json, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4424.json
