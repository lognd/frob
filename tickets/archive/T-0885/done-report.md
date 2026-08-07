## Done report

Leftover mutant journals from an xdist worker crash or external SIGTERM were never restored on the next run start; T-0857 only covered frob mutate's own-crash path. A pytest_configure hook in tests/conftest.py now calls frob.mutate.restore_stale_journals at session start (controller only, skipped on xdist workers), so a corrupted on-disk target left by a killed mutation run is healed before any test executes. Two regression tests reproduce the dead-PID journal incident and the xdist-worker skip.

### Changed
```
 tests/conftest.py            | 35 ++++++++++++++++++
 tests/test_mutate_journal.py | 70 ++++++++++++++++++++++++++++++++++--
 tickets.md                   | 86 +++++++++++++++++++++++++++++++++++++++++++-
 3 files changed, 188 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_mutate_journal.py::test_pytest_session_start_restores_leftover_journal` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_pytest_session_start_skips_restore_on_xdist_worker` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
