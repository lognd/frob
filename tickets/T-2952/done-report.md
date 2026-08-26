## Done report

Changed:
src/frob/tickets/_new_renumber.py::_next_ticket_id_shared
src/frob/tickets/_new_renumber.py::_open_and_lock_counter_file
src/frob/tickets/_new_renumber.py::_unlock_and_close_counter_file
src/frob/serve/_socketd.py::DaemonError
src/frob/serve/_socketd.py::acquire_singleton_lock
src/frob/serve/_socketd.py::_release_singleton_lock
src/frob/testing/_coverage_wait.py::CoverageLockUnavailable
src/frob/testing/_coverage_wait.py::_flock_path
src/frob/testing/_coverage_wait.py::_coverage_lock
src/frob/testing/_coverage_wait.py::_shared_coverage_lock

Sweep inventory (measured, before fixing): grepped src/ for bare
imports of fcntl/pwd/grp/termios/resource/posix/tty/crypt/nis/spwd/
syslog/ossaudiodev, select.poll/epoll/kqueue usage, signal.SIG*
assigned as a default arg or at module/class scope, and os.fork/
setsid/getuid/geteuid/getgid/getpgid assigned at module scope. Found
exactly 3 bare unconditional `import fcntl` sites (the three named in
this ticket) and nothing else in any of the other shapes -- every
other fcntl call site in the repo (~10 files) already used the guarded
importlib try/except idiom from T-2918/T-2934. `signal.SIGKILL` as a
default arg (T-2936's own fix) was already guarded by a
`sys.platform != "linux"` early return.

Fix: matched the established `frob.tickets._store` pattern exactly --
`fcntl`/`msvcrt` each imported via `importlib.import_module` inside
their own `try/except ImportError`, a real `msvcrt.locking`-based
backend used when only msvcrt is available, and a loud refusal
(`TicketLockUnavailable`/`CoverageLockUnavailable`/
`Err(DaemonError.LockUnavailable)`) -- never a silent no-op -- only
when neither exists.

Evidence:
- tests/unit/test_process_lock.py::TestSharedIdCounterPlatformBackends::test_no_lock_primitive_refuses_loudly
- tests/unit/test_process_lock.py::TestSharedIdCounterPlatformBackends::test_windows_backend_round_trips
- tests/test_coverage_wait_shared.py::TestCoverageLockPlatformBackends::test_no_lock_primitive_refuses_loudly
- tests/test_coverage_wait_shared.py::TestCoverageLockPlatformBackends::test_windows_backend_round_trips
- tests/test_serve_socket.py::TestAcquireSingletonLockPlatformBackends::test_no_lock_primitive_refuses_loudly
- tests/test_serve_socket.py::TestAcquireSingletonLockPlatformBackends::test_windows_backend_round_trips

check-repro was not used: this is a platform-absence bug (the crash
only occurs when the `fcntl` module itself does not exist, i.e. on
Windows), so it cannot be reproduced as a FAILED_AT_PARENT pytest node
on this Linux CI runner. Evidence instead follows the T-2936 precedent
(same platform-only-crash shape): regression tests that exercise the
guarded code path directly (both the loud-refusal branch and the real
msvcrt backend, the latter via a fake msvcrt module backed by real
fcntl.flock on Linux CI, the same technique
frob.process._lock's own T-2934 tests use) plus a REAL windows-latest
CI run as the actual acceptance evidence (below).

Real windows-latest CI run: https://github.com/lognd/frob/pull/2, run
32938258727, job 98083729311 (commit 0d8ddb331, the fix commit before
the follow-up test/docs/refactor commits which do not change import
behavior). Confirmed: the ModuleNotFoundError: No module named 'fcntl'
crash at src/frob/tickets/_new_renumber.py:31 is GONE. The job proceeds
past `uv sync`, past `uv run frob natives build`'s own frob import,
and fails later, inside `make core`'s maturin build step, on an
UNRELATED UnicodeDecodeError (cp1252 codec decoding the cargo/maturin
subprocess's stdout) inside `frob.process._guard.guarded_subprocess_run`
-- filed as T-2953 (out of this ticket's scope) per this
ticket's own directive to file, not fix, the next crash found.

(a) Does frob IMPORT on Windows? YES, as far as this measurement goes:
the fcntl ModuleNotFoundError class (the whole reason this ticket was
filed CRITICAL) is confirmed gone by a real windows-latest CI run. This
does not prove EVERY module in the repo imports cleanly on Windows --
only that this ticket's own sweep found no further bare POSIX-only
import-time hazard, and that the real CI run got well past the point
this ticket's own crash used to stop it (all the way into a native
Rust build step).

(b) Does frob RUN USEFULLY on Windows? NO. The very next step in the
SAME CI job (`make core` / `frob natives build`) crashes on an
unrelated defect (T-2953) before the natives extension even
finishes building, which blocks `frob check`, `frob test`, and every
other command that depends on the native extension. Windows support
remains far from real; this ticket closes exactly one (now two,
counting T-2936) blocking crash in a chain that is expected to have
more.

Filed: T-2953 (Windows natives-build UnicodeDecodeError,
unrelated defect discovered via the real CI run this ticket's
acceptance criteria required)

Gates: `frob check --ticket T-2952 --only affect_drift --only scope
--only fmt` clean (0 errors, only pre-existing advisory SCOPE002/
SCOPE003 warnings from touching shared multi-symbol doc pages).
ARCH001 (function-length) triggered by the initial inline fix and
resolved by extracting `_open_and_lock_counter_file`/
`_unlock_and_close_counter_file` (private helpers, no new public
surface, does not touch the ARCH103-waived read-increment-write
critical section). T-2114 (new-public-symbol doc/test) satisfied for
`CoverageLockUnavailable` via `docs/modules/testing.md` and the bound
evidence above.

### Changed
```
 docs/modules/serve.md              |  14 +++++
 docs/modules/testing.md            |   8 +++
 src/frob/serve/_socketd.py         |  54 +++++++++++++++--
 src/frob/testing/_coverage_wait.py | 112 +++++++++++++++++++++++++++--------
 src/frob/tickets/_new_renumber.py  |  85 +++++++++++++++++++++++++--
 tests/test_coverage_wait_shared.py |  67 +++++++++++++++++++++
 tests/test_serve_socket.py         |  65 +++++++++++++++++++++
 tests/unit/test_process_lock.py    |  79 +++++++++++++++++++++++++
 tickets/T-2952/ticket.md           | 116 ++++++++++++++++++++++++++++++++++++-
 tickets/T-2953/ticket.md |  86 +++++++++++++++++++++++++++
 10 files changed, 649 insertions(+), 37 deletions(-)
```

### Evidence
- `tests/unit/test_process_lock.py::TestSharedIdCounterPlatformBackends::test_no_lock_primitive_refuses_loudly` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestSharedIdCounterPlatformBackends::test_windows_backend_round_trips` (pytest node id, verified passing when recorded)
- `tests/test_coverage_wait_shared.py::TestCoverageLockPlatformBackends::test_no_lock_primitive_refuses_loudly` (pytest node id, verified passing when recorded)
- `tests/test_coverage_wait_shared.py::TestCoverageLockPlatformBackends::test_windows_backend_round_trips` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestAcquireSingletonLockPlatformBackends::test_no_lock_primitive_refuses_loudly` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestAcquireSingletonLockPlatformBackends::test_windows_backend_round_trips` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 28 error(s), 821 warning(s), 854 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, DUP001@tests/unit/test_process_lock.py, LARGE001@src/frob/stats/_agentic.py, PRE001@tickets/T-2952, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
