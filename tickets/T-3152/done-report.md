## Done report

TRUTH ticket: picked the correct heuristic and made both instruments read
it, without hiding which one is right by having one call the other.

Investigated both:
- frob.process._reap._process_start_age_s: derived age from the
  <proc>/<pid> DIRECTORY's own mtime.
- scripts/fleet_status.py::_forkserver_age_s: derived age from
  /proc/<pid>/stat's starttime field (clock ticks since boot, man proc's
  documented field 22) plus /proc/uptime.

Verdict: stat's starttime is correct, mtime is the one to retire.
starttime is the kernel-documented process-start timestamp every
standard tool (ps -o etimes, uptime-relative age math) already treats as
canonical, at 1/clk_tck resolution (typically 10ms). A procfs entry's
mtime is a filesystem side effect of directory creation, not a
documented interface for this purpose -- it happens to equal process
start time on a normal Linux host today, but nothing guarantees that
across every kernel/container scenario, which is exactly the ticket's
own stated concern.

Fix: rewrote _process_start_age_s (src/frob/process/_reap.py) to compute
age the same way _forkserver_age_s already does -- read stat's starttime
field via a new _stat_fields_after_comm helper (also used to de-duplicate
_read_ppid_from_stat's own inline field split), combine with /proc/uptime
and os.sysconf("SC_CLK_TCK") read once per scan (_read_uptime_and_clk_tck),
not per-pid. Removed the now-unused mtime-based implementation and the
now-unused `time` import.

Did NOT make one function call the other: scripts/fleet_status.py has a
documented "no frob import" contract (must run under any bare python3,
not just this repo's built venv) so the two implementations stay
textually independent by design -- matching the established T-3072/T-3093
precedent for this exact file pair (_is_live_check_cmdline's own
docstring). Instead: unified the ALGORITHM (both now compute the
identical stat-starttime arithmetic, field-for-field), and added
tests/unit/test_process_reap.py::TestProcessStartAgeMatchesFleetStatus,
which imports scripts/fleet_status.py's own _stat_fields_after_comm/
_forkserver_age_s (via tests/unit/conftest.py's _load_script) alongside
frob.process._reap's _process_start_age_s and asserts BOTH compute the
exact same age (and the exact same None) from identical synthetic
/proc/<pid>/stat + uptime input. Also cross-referenced both functions'
docstrings so a future reader hits the other one immediately.

Fixtures: tests/unit/test_process_reap.py's _write_proc_entry now writes
a real starttime field (against a fixed, deterministic uptime/clk_tck
baseline) instead of mutating mtime; renamed its mtime_offset_s param to
age_s and updated every call site (TestReapOrphanedForkservers's existing
6 must-fire/must-stay-quiet cases). TestProcessStartAge gained a
must-stay-quiet-in-reverse pair (unknown uptime, zero clk_tck both
degrade to None, never a fabricated age) alongside the rewritten
must-fire case.

Verified: tests/unit/test_process_reap.py -- 42/42 pass. ruff check and
ty check clean on both changed source files. git diff main
--diff-filter=D --stat is empty after re-merging main (a prior worktree
snapshot briefly showed 2 already-archived tickets' files as deleted --
stale merge base, resolved by merging main again before finishing, per
house rule).

### Changed
```
 scripts/fleet_status.py         |  18 ++++-
 src/frob/process/_reap.py       | 128 ++++++++++++++++++++++++++++-------
 tests/unit/test_process_reap.py | 143 ++++++++++++++++++++++++++++++++--------
 tickets/T-3152/ticket.md        |  11 +++-
 4 files changed, 249 insertions(+), 51 deletions(-)
```

### Evidence
- `tests/unit/test_process_reap.py::TestProcessStartAge::test_reads_age_from_starttime` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestProcessStartAge::test_missing_entry_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestProcessStartAge::test_unknown_uptime_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestProcessStartAge::test_zero_clk_tck_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestProcessStartAgeMatchesFleetStatus::test_same_stat_line_and_uptime_yield_the_same_age` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestProcessStartAgeMatchesFleetStatus::test_both_agree_none_on_unknown_uptime` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestReapOrphanedForkservers::test_terminates_old_orphaned_forkservers` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestReapOrphanedForkservers::test_leaves_young_orphaned_forkservers_alone` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
