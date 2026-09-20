## Done report

Root cause: _recreate/_rebuild_schema_atomically called _quarantine_sidecars(path)
which renamed path.name ITSELF aside (not just -wal/-shm) before the following
_replace_with_retry(tmp_path, path, ...) published the rebuilt db there -- a window
with NO file at path at all. Wide enough on a loaded macOS CI runner for a
concurrent connect_readonly sibling's mode=ro sqlite3.connect to land inside it
and raise "unable to open database file" (T-3607's own concurrent-reader test's
own regression).

Culprit commit: NEITHER named commit actually introduced this. Diffed cache.py
byte-for-byte at 59c43cb12 (passing) vs current head: _recreate,
_quarantine_sidecars, and _replace_with_retry are IDENTICAL across both commits.
T-4411 added seed_disposable_worktree_cache (a separate function, uses
_replace_with_retry but never touches _recreate's own call sequence). T-4412
changed _read_schema_version to re-raise transient lock errors instead of
misclassifying them as corrupt -- also does not touch _recreate's absence
window, and the test calls graph_cache._recreate directly, bypassing
_read_schema_version entirely. The absence window has existed unchanged since
T-3623/T-3632; today's CI failure is this pre-existing race finally landing
under macOS's slower/differently-scheduled I/O, not a functional regression
from either named ticket.

Reproduction: local Linux loop (reader duration raised 2.0s -> 10.0s, 20
iterations) at UNFIXED code: 0/20 fails (confirms the ticket's own note that
this window is too narrow to hit reliably on Linux). A new deterministic test
(test_path_never_absent_during_recreate, patches os.replace/os.link/Path.rename
to record path.exists() before/after each call) DOES fail reliably against
unfixed code -- used as the --check-repro proof instead of the flaky
integration test.

Fix (two parts): (1) _quarantine_sidecars now only renames -wal/-shm aside;
the main db is preserved under a quarantined name via a hard LINK
(_quarantine_main_db) instead of a rename, so path is never removed -- only
atomically retargeted by the immediately-following os.replace. (2)
connect_readonly's _with_lock_retry call now also treats "unable to open
database file" as transient (via a new extra_transient parameter, checked
through the extracted _should_retry_lock_error helper) as a second,
independent layer of defense.

Measured after fix: local Linux loop (10.0s duration, 20 iterations): 0/20
fails (unchanged from baseline, as expected -- the race was never Linux-
reproducible). New test_path_never_absent_during_recreate: FAILS at
unfixed code (56229ef63), PASSES with the fix (5b9867ee3) --
frob ticket evidence --check-repro confirms FAILED_AT_PARENT (a genuine
repro). Full tests/unit/test_graph_cache.py: 51/51 passing. frob test
(touched set): PASS (10 tests). frob check --ticket T-4454: clean except
pre-existing repo-wide TICK004 rot warnings for unrelated tickets
(T-4111..T-4118), out of scope.

### Changed
```
 src/frob/graph/cache.py        | 127 +++++++++++++++++++++++++++++++++++++++--
 tests/unit/test_graph_cache.py |  62 ++++++++++++++++++++
 tickets/T-4454/ticket.md       |  12 ++++
 3 files changed, 195 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_path_never_absent_during_recreate` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_quarantined_sidecars_are_renamed_not_unlinked` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 1 error(s), 4800 warning(s), 962 waived
- error-findings: TICK004@tickets.md
