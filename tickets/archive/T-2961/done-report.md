## Done report

Changed:
src/frob/serve/_socketd.py::_DaemonServer (guarded, non-Windows only, Windows placeholder added)
src/frob/serve/_socketd.py::DaemonError (PlatformUnsupported value)
src/frob/serve/_socketd.py::run_socket_daemon (win32 guard)
src/frob/serve/_socketd.py::send_request (win32 guard)
src/frob/app/_daemon_proxy.py::DaemonLiveness (PlatformUnsupported value)
src/frob/app/_daemon_proxy.py::ProxyReason (PlatformUnsupported value)
src/frob/app/_daemon_proxy.py::probe_daemon (win32 guard)
src/frob/app/_daemon_proxy.py::_ask_version_over_socket (win32 guard)
src/frob/app/_daemon_proxy.py::ensure_daemon (PlatformUnsupported branch)
src/frob/app/_daemon_proxy.py::query (win32 guard)
src/frob/app/_daemon_proxy.py::try_daemon_lease (win32 guard)
src/frob/app/_daemon_proxy.py::_LeaseConnection.__init__ (win32 guard, defense in depth)
src/frob/serve/_events.py::subscribe_and_wait (win32 guard)
src/frob/verify/_worker.py::_lower_cpu_nice_priority (ty: ignore, no behavior change)

STOP-BEFORE-BUILD assessment (delivered and approved before any code was
written): the 6 ty diagnostics were not typeshed annotation noise --
`class _DaemonServer(socketserver.ThreadingUnixStreamServer):` at
_socketd.py is a MODULE-LEVEL class statement, so it raises AttributeError
the instant the module is imported on a platform lacking the base class --
structurally identical to T-2952's bare `import fcntl`, just at class-
definition time. The other 5 sites are lazy runtime calls (4 socket.AF_UNIX
sites, 1 os.nice already correctly try/except-guarded at runtime). Daemon
load-bearing-ness confirmed via code reading, not assumption:
ProxyReason's own documented contract ("every value means fall back to
in-process, silently"), all 7 CLI callers wrapping query() in the
identical try/fallback pattern, FROB_NO_DAEMON=1 as a first-class tested
bypass, and the differential-parity test suite asserting byte-identical
daemon-served/in-process answers. Recommended (and executed, on
approval) a scoped loud refusal rather than a transport rewrite.

Fix: `_DaemonServer` only defined on non-Windows; a Windows placeholder
keeps the name bound (ty-clean on every platform, never constructed) and
`run_socket_daemon` refuses (Err(DaemonError.PlatformUnsupported)) before
ever touching it. `ty check` resolves each function body independently
of its callers, so every OTHER site that references socket.AF_UNIX
needed its OWN guard, not just the outermost caller -- probe_daemon,
_ask_version_over_socket, query, try_daemon_lease, _LeaseConnection
.__init__, send_request, subscribe_and_wait each carry one. os.nice(10)
was already correct at runtime (try/except AttributeError); just needed
a ty: ignore[unresolved-attribute] suppression.

Amendment executed: guarding the module-level crash converts a
collection crash into runtime test failures for the tests that actually
construct a daemon/bind a real socket/exercise _DaemonServer -- those
assert live-daemon outcomes that cannot hold once Windows refuses
instead of crashing. Skipped at the NARROWEST granularity (26 individual
test methods across 6 files, not whole modules), each citing T-2961 and
the filed transport epic:
  tests/test_serve_socket.py: 6
  tests/test_app_daemon_proxy.py: 12
  tests/test_serve_events.py: 3
  tests/test_serve_leases.py: 3
  tests/unit/test_daemon_proxy_lease_t1276.py: 1
  tests/test_coverage_wait_shared.py: 1
Tests exercising pure in-process behavior (_EventBus, ResourceLeaseManager
direct calls, acquire_singleton_lock's already-cross-platform flock/msvcrt
lock, mocked probe_daemon liveness branches) were left unskipped -- two of
them (test_no_daemon_is_unreachable, test_falls_back_to_file_lock_when_no_daemon)
now positively validate the new Windows refusal path.

Filed the Windows-native-daemon-transport epic (T-2963,
renumbers at land) with the options/trade-offs from the assessment
written into its body: AF_UNIX-on-Windows (client half only, Win10
1803+/Python 3.9+ floor -- ThreadingUnixStreamServer has no cross-
platform server-half equivalent regardless), named pipes (real Windows
IPC, needs a wholly separate client+server implementation), loopback
TCP+token (simplest, but a new local-process-reachable auth surface this
repo's own SEC/PII gates would need to evaluate). Decomposition into
child tickets is left to whoever picks up the epic, per its own body.

Evidence:
- local `uv run ty check src` (FROB_SUGGEST_ACK=1, ran directly since
  this IS the tool being verified): exit 0, zero blocking diagnostics.
  The one non-blocking diagnostic (warning[unused-ignore-comment] on
  _worker.py's os.nice suppression, since os.nice DOES resolve on this
  Linux runner) is EXPECTED cross-platform asymmetry, confirmed to not
  fail ty's own exit code (warning severity, not error).
- targeted pytest: 72/72 pass across
  tests/test_serve_socket.py, tests/test_serve_events.py,
  tests/test_serve_leases.py, tests/unit/test_daemon_proxy_lease_t1276.py,
  tests/unit/verify/test_worker.py. 40/41 pass in
  tests/test_app_daemon_proxy.py + tests/test_coverage_wait_shared.py --
  the 1 failure (TestDifferentialParity::test_check_delta_gates_only_json_daemon_matches_in_process)
  is a PRE-EXISTING flake unrelated to this change (a "[REPLAY age=...]"
  cache-timing label mismatch between a daemon-served and in-process run,
  reproduced identically and independently confirmed during T-2953's own
  verification pass before this ticket existed).

check-repro not used: same platform-absence reasoning as T-2952/T-2953 --
the crash this fixes only occurs on a platform this Linux CI runner is
not, so it cannot be reproduced as a FAILED_AT_PARENT pytest node here.

REAL windows-latest CI: attempted (PR #4,
https://github.com/lognd/frob/pull/4, run 32944685482) but could NOT
reach `ty check` this session -- all three platforms (windows-latest,
ubuntu-latest, macos-latest) failed identically at an EARLIER step
(`ruff check src tests`) on a pre-existing, already-independently-filed
defect on main (T-2960, `I001` in src/frob/vet/_ecosystem.py, filed by
this repo's own rapid-sweep machinery from an unattributed source
between T-2953's land and this session, NOT touched by any of the three
Windows tickets in this chain). This is disclosed honestly rather than
claimed as a pass: this ticket's OWN acceptance criterion ("a real
windows-latest CI run gets past ty check with zero diagnostics") is
NOT independently CI-confirmed this session. Confidence instead rests
on: (a) the identical local ty invocation exiting 0, (b) the
`sys.platform == "win32"` narrowing pattern being a standard, widely-
supported idiom across mypy/pyright/ty (not a novel or fragile
technique), and (c) T-2960 being a one-line `ruff --fix`-fixable,
already-tracked, unrelated finding that will unblock re-verification
the moment it (or a rebase past it) lands -- not something this ticket
should absorb into its own scope.

Filed: T-2963 (Windows-native-daemon-transport epic)

Gates: `frob check --ticket T-2961 --only affect_drift --only scope
--only fmt` clean (0 errors; only pre-existing advisory SCOPE002/
SCOPE003 warnings from touching central multi-caller seams).

(a) Does frob IMPORT on Windows? Still YES (unchanged from T-2952/
T-2953 -- this ticket's fix does not touch import-time behavior beyond
what T-2952 already covers; the NEW fix here is a class-definition-time
crash, and it is now guarded).

(b) Does frob RUN USEFULLY on Windows? Not independently re-confirmed
by real CI this session (see above) -- locally, `ty check` is clean and
26 tests are correctly, narrowly skipped rather than silently passing
or crashing. The pipeline's real next failure past `ty check`, if any,
is UNKNOWN until T-2960 (unrelated) is fixed and CI can actually reach
that step again. Per the coordinator's STOP instruction, this session
ends here rather than chasing that verification further.

### Changed
```
 docs/modules/serve.md                       |  46 ++++++-
 docs/modules/testing.md                     |   8 +-
 frob.lock                                   |  20 ++-
 src/frob/app/_daemon_proxy.py               |  58 ++++++++-
 src/frob/serve/_events.py                   |  10 +-
 src/frob/serve/_socketd.py                  | 131 ++++++++++++++-----
 src/frob/verify/_worker.py                  |   9 +-
 tests/test_app_daemon_proxy.py              | 133 ++++++++++++++++++++
 tests/test_coverage_wait_shared.py          |  12 ++
 tests/test_serve_events.py                  |  36 ++++++
 tests/test_serve_leases.py                  |  34 +++++
 tests/test_serve_socket.py                  |  67 ++++++++++
 tests/unit/test_daemon_proxy_lease_t1276.py |  12 ++
 tickets/T-2961/ticket.md                    | 188 +++++++++++++++++++++++++++-
 tickets/T-2963/ticket.md          | 121 ++++++++++++++++++
 15 files changed, 837 insertions(+), 48 deletions(-)
```

### Evidence
- `tests/test_serve_events.py::TestSubscribeAndWait::test_no_daemon_is_unreachable` (pytest node id, verified passing when recorded)
- `tests/test_coverage_wait_shared.py::TestWorktreeLock::test_falls_back_to_file_lock_when_no_daemon` (pytest node id, verified passing when recorded)
- `tests/test_serve_socket.py::TestAcquireSingletonLock::test_first_caller_wins` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestEnsureReducedPriority::test_applies_nice_and_ionice_exactly_once` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestEnsureReducedPriority::test_failed_nice_call_never_raises` (pytest node id, verified passing when recorded)
- `tests/unit/test_daemon_proxy_lease_t1276.py::TestEnsureDaemonLivenessBranches::test_wedged_does_not_spawn_a_rival` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 28 error(s), 1188 warning(s), 853 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC008@docs/commands/check.md, I001@/home/logan/projects/frob/.claude/worktrees/t-2961/src/frob/vet/_ecosystem.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/serve/_socketd.py, PRE001@tickets/T-2961, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
