## Done report

Changed:
tests/test_ticket_leases.py::repo (fixture)
tests/test_ticket_leases.py::_commit_all
tests/ticket_land_suite/test_wip.py::TestWipCommitNormalizationOnlyDirty::test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed
src/frob/tickets/_land.py::_land_lock

All three were diagnosed on real Windows via winrun (a Windows-native mirror
run of this exact worktree), not reasoned out on Linux.

1) test_ticket_leases.py::TestDispatchLandGuard::test_orphaned_squash_residue_is_reclaimed_before_a_mutating_verb_dispatches
   TEST-FIXTURE PREMISE, not a production defect. The reclaim path
   (`reclaim_orphaned_squash_residue`) creates `.frob/land.lock` while
   holding its own exclusive lock on that fd, then runs `git clean -fd`.
   On POSIX, unlinking a file this process itself still has open+locked is
   legal, so `clean -fd` silently removes it. On Windows, deleting an
   open+locked file fails outright (measured: `git clean -fd` warned
   "failed to remove .frob/land.lock: Invalid argument"), leaving it as an
   untracked residue -- but ONLY because this test's own `repo` fixture
   never gitignored `.frob/`, unlike every real frob checkout (see
   `_porcelain_dirty`'s own docstring: ".frob/ is frob-local scratch state
   a repo is expected to .gitignore anyway"). Fix: gitignore `.frob/` in
   the fixture, matching production. Verified via winrun: with the fix,
   `git clean -fd` skips the ignored file entirely (no error) and `git
   status --porcelain` stays clean on Windows, exactly as on Linux.
   PROVEN on real Windows, not just reasoned: full file (151 tests) also
   passes there except pre-existing, unrelated `echo`-not-spawnable
   failures (Windows has no `echo` executable; those tests are not in my
   scope and are already tracked elsewhere).

2) test_wip.py::TestWipCommitNormalizationOnlyDirty::test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed
   TEST-FIXTURE PREMISE, not a production defect. `Path.write_text`'s
   default `newline=None` performs Python's own universal-newlines
   translation on WRITE too: on a real Windows interpreter every `\n` in
   the string is silently turned into `\r\n`. The test's "commit an LF
   file" step used `write_text`, so on Windows the file already held CRLF
   bytes at commit time -- the later `write_bytes(CRLF)` "simulate
   corruption" step then wrote content byte-identical to what was already
   on disk, no working-tree change at all, so `git status --porcelain`
   measured clean and the test's own "must be dirty" assertion failed.
   Confirmed on real Windows with a targeted repro (printed the raw bytes
   `write_text` produced: `b'line one\r\nline two\r\n'`). Fix: use
   `write_bytes` with an explicit `\n` for the initial write. Verified via
   winrun: full file (9 tests) now passes on Windows.

3) test_land_lock.py::TestLandLockHolderMetadataAndTimeout::test_orphaned_lock_from_a_confirmed_dead_pid_is_reclaimed_and_logged
   LIVE DEFECT in `_land_lock` (src/frob/tickets/_land.py), confirmed on
   real Windows, not a test artifact. The T-1634 reclaim actually DOES
   fire -- the dead-pid liveness probe correctly returns False, and the
   lock is genuinely re-acquired and overwritten -- but the disclosure log
   line never appears. Root cause: `_land_lock` re-read the lock file's
   prior-holder metadata via `Path.read_text` AFTER this process's own
   `portable_flock_acquire` had already succeeded. `fcntl.flock` (POSIX)
   is advisory, so a second same-process handle can still read the file
   fine post-acquire -- this stayed hidden on Linux. `msvcrt.locking`
   (Windows) is MANDATORY: it blocks even a separate handle in the SAME
   process from reading a byte range this process itself just locked.
   Confirmed with a targeted repro on real Windows: the post-acquire
   `Path.read_text` raised `PermissionError` every time; `_read_land_lock_
   holder` swallows that as `OSError -> None`, so `prior_holder` came back
   `None` and the reclaim-disclosure warning was unconditionally
   suppressed -- even though the reclaim itself succeeded. This matters in
   production: an operator running frob on Windows silently lost the
   diagnostic line telling them a dead land's lock was just cleared.
   Fix: snapshot the holder metadata from PRE-acquire reads only (the
   existing wait-loop read when the lock is contended, or one read taken
   before the first acquire attempt when the lock is free immediately) and
   reuse that snapshot after acquiring, never re-reading `path` once this
   process holds the lock. Verified via winrun: the full
   TestLandLockHolderMetadataAndTimeout class (23 tests) now passes on
   Windows, including the previously-failing reclaim-and-logged case.

Evidence: bound node ids (see `frob ticket evidence T-4243`):
  tests/test_ticket_leases.py::TestDispatchLandGuard::test_orphaned_squash_residue_is_reclaimed_before_a_mutating_verb_dispatches
  tests/ticket_land_suite/test_wip.py::TestWipCommitNormalizationOnlyDirty::test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed
  tests/ticket_land_suite/test_land_lock.py::TestLandLockHolderMetadataAndTimeout::test_orphaned_lock_from_a_confirmed_dead_pid_is_reclaimed_and_logged
All three re-run and confirmed PASSING on real Windows via winrun, plus
each file's full suite (151 / 9 / 23 tests respectively) on both Linux and
Windows, plus tests/ticket_land_suite/ + tests/test_ticket_leases.py
combined (500 tests) on Linux, plus `frob test --base main` (touched-set,
exit=0).

What remains unproven until the real CI Windows leg runs: only the exact
CI runner environment/timing (concurrency level, disk/AV interaction) --
the mechanism itself (git clean -fd vs. an open+locked file; write_text's
platform-dependent newline translation; msvcrt's mandatory-locking
semantics vs. fcntl's advisory semantics) was reproduced directly on real
Windows via winrun, not inferred, for all three.

Filed: none -- all three were fixable within T-4243's own scope; no
out-of-scope discoveries.

Gates: `frob check --ticket T-4243` intermittently could not build its
graph cache (`cache: store_file_data(...) still locked after 30s` /
`database is locked`) under this session's concurrent-fleet load -- a
pre-existing shared-cache contention issue unrelated to this ticket's
files, not a finding against this change. `ruff-check`: no issues in the
changed files. `ruff-format`: applied and clean on the changed files.
`frob test --base main`: touched=8 selected, exit=0, 3 python outcomes
recorded green.

### Changed
```
 src/frob/tickets/_land.py           | 28 ++++++++++++++++++++++++----
 tests/test_ticket_leases.py         | 30 ++++++++++++++++++++++++++++++
 tests/ticket_land_suite/test_wip.py | 18 +++++++++++++++++-
 tickets/T-4243/ticket.md            |  4 ++++
 4 files changed, 75 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestDispatchLandGuard::test_orphaned_squash_residue_is_reclaimed_before_a_mutating_verb_dispatches` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_wip.py::TestWipCommitNormalizationOnlyDirty::test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_land_lock.py::TestLandLockHolderMetadataAndTimeout::test_orphaned_lock_from_a_confirmed_dead_pid_is_reclaimed_and_logged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 9 error(s), 4526 warning(s), 935 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@src/frob/vet/_bare_toolchain.py, COV003@tests/test_excludes.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/gates/_rule_id_scan.py, DRIFT002@src/frob/check/_python.py, PRE001@tickets/T-4243, SCOPE002@tickets.md, WIRE002@tests/unit/test_flag_coverage_gate.py
