## Done report

Root cause (verified against source): frob.graph.cache._recreate unlinked
the cache db and its -wal/-shm sidecars IN PLACE, then reopened at the
SAME path. A sibling ProcessPoolExecutor worker's process-lifetime
_artifact_cache_connection (frob.lang._artifact_cache_connection) has
the OLD -shm memory-mapped for WAL coordination; unlink-then-recreate-
at-the-same-path invalidated that mapping out from under it, crashing
the sibling with SIGBUS mid-SELECT in load_parsed_artifact -- exactly
the ubuntu CI run 33451274911 trace.

Fix: _recreate now RENAMES (never unlinks) the db/-wal/-shm aside to a
quarantined sibling name before opening a fresh db at the original path.
A rename never invalidates another process's already-open fd/mmap
(those stay bound to the renamed file's inode); only in-place unlink+
recreate-at-the-same-path does. The whole quarantine-and-reopen sequence
is serialized by an advisory exclusive flock on a dedicated
<path>.rebuild.lock file (frob.process._lock's shared portable_flock_*
primitives), falling back to running unlocked if no lock backend exists.
Quarantined sidecars are swept (best-effort, age-gated) on the next
rebuild rather than unlinked immediately, since a sibling might still
have them mapped.

Positive control: TestRecreateConcurrentReaderSurvives spawns a real
sibling subprocess holding a long-lived WAL reader connection while the
main process repeatedly calls _recreate against the same path; asserts
the sibling's exit code is 0 (never a negative/signal-killed
returncode). I verified this test suite (all 3 new tests) passes
against the FIXED code; I could not reliably force the OLD code to
crash in this sandbox within the test's bounded race window (the
production incident is an intermittent, filesystem/timing-dependent
race -- that is why it surfaced only occasionally in CI, not on every
run). The rename-vs-unlink mechanism itself is directly and
deterministically verified by
test_quarantined_sidecars_are_renamed_not_unlinked (asserts a
quarantined sidecar survives after _recreate, proving rename not
unlink) and test_sweep_removes_only_old_quarantined_sidecars (age-gated
cleanup).

Also fixed along the way (same scope): the two frob:tests directives'
target-form (DOC007/DRIFT002 -- dotted Class.method, not pytest's
Class::method), and design/frob.strata's testsuite node capability
grants (SELFAUDIT001/SYS100: the new subprocess.Popen (exec) and
write_bytes/os.utime (fs.write) call sites), plus the SYS111 via-list
ratchet ceiling bump in
docs/design/registry/capability-via-ratchet.lock.json for both.

Evidence: tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives.test_sibling_reader_survives_concurrent_recreate,
tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives.test_quarantined_sidecars_are_renamed_not_unlinked,
tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives.test_sweep_removes_only_old_quarantined_sidecars

Gates: `uv run frob check --ticket T-3607` scoped run shows 0
errors touching src/frob/graph/cache.py, tests/unit/test_graph_cache.py,
design/frob.strata, or the ratchet lock (SELFAUDIT001/DOC007/DRIFT002/
COV002/SCOPE001 all cleared after the fix-up pass). Remaining repo-wide
FAIL rows (ARCH102/103, DEPR006, WAIVE011, LARGE001, REL001) are
pre-existing/unrelated -- ARCH102/103 and LARGE001 are this agent's OWN
next series items (T-3607 does not touch those files), DEPR006/WAIVE011
are pre-existing lock-producer staleness, REL001/T-3411 is explicitly
out of this series' scope per the coordinator brief.

Filed: none (companion ticket T-3608 filed separately for the xdist
worker-death deadlock, per the coordinator's priority-insert brief).

### Changed
```
 tickets/T-3607/ticket.md | 26 ++++++++++++++++++++++++++
 1 file changed, 26 insertions(+)
```

### Evidence
- `tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_sibling_reader_survives_concurrent_recreate` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_quarantined_sidecars_are_renamed_not_unlinked` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_sweep_removes_only_old_quarantined_sidecars` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 8 error(s), 4146 warning(s), 899 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, DEPR006@frob-deprecated-baseline.lock.json, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, REL001@src/frob/__init__.py, WAIVE011@frob-ratchet.lock.json
