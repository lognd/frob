## Done report

T-2918: `_baseline_lock` (T-2595, `_rapid_sweep.py`) degraded to a
logged-but-silent NO-OP for a process's entire lifetime whenever `fcntl`
was not importable -- unconditionally true on every Windows process, not
merely under rare lock contention. That let two concurrent sweeps race
the rolling-baseline read-decide-write with no serialization at all.

Chose the "implement a genuine cross-platform path" branch of the
directive, not the pure-refusal branch, since a real Windows lock is
achievable (`msvcrt.locking`) and strictly better than refusing to run
sweeps at all on Windows:

- Added an `msvcrt` import probe alongside the existing `fcntl` one.
- `_baseline_lock` now tries `fcntl.flock` (POSIX) first, then
  `msvcrt.locking` (Windows) -- a one-byte-range lock, since `msvcrt` has
  no whole-file advisory lock. The retry/timeout poll loop is now shared
  between both backends (identical `OSError`/`PermissionError` catch,
  since Windows raises `PermissionError`, a subclass of `OSError`, for
  "already locked").
- If NEITHER primitive is importable, `_baseline_lock` now raises a new
  public exception, `BaselineLockUnavailable`, instead of proceeding
  unlocked -- the loud-refusal half of the directive, reserved for a
  platform with no known lock primitive at all (none currently exists
  among the three this repo now runs CI on, per T-2917).
- Left the EXISTING timeout-degrade branch (a real lock exists, is
  contended past `timeout`, proceed unlocked + log WARNING) unchanged --
  that one is backed by `_write_baseline_cas`'s CAS ancestry check as a
  real, if narrower, correctness backstop for a brief contention window;
  T-2918's directive targeted the platform-absence case specifically,
  which had no such backstop and no bound on how long it could last.
- Documented the new backend and the refusal in
  docs/modules/tickets-verify-sweep.md under a new subsection, with a
  `frob:doc` edge on the new public exception (COV001).
- T-2595's own evidence cited `test_no_fcntl_degrades_to_unlocked`, which
  no longer describes real behavior (fcntl-absent now raises, it does
  not silently degrade) -- rebound it via `frob ticket evidence T-2595
  --replace` to `test_no_lock_primitive_refuses_loudly` rather than
  deleting the test out from under that ticket's evidence (memory:
  "test deletion orphans evidence").
- Fixed a TICK006 finding this series' own T-2917 land introduced: its
  Done report cited T-draft-837874a3 by its pre-renumber name; corrected
  the "Filed:" line to the real T-2930 (left the auto-generated git
  diffstat block alone, since that stat is a literal, historically
  accurate record of what the land commit actually touched under the
  pre-renumber name).

Windows backend is exercised on Linux CI via a fake `msvcrt` module
(`test_windows_backend_serializes_two_concurrent_holders`) backed by a
real `fcntl.flock` under the hood -- this proves the code path's control
flow (acquire/contend/timeout-degrade/release) without requiring an
actual Windows runner; T-2917's now-3-platform CI matrix is a separate,
complementary signal (it runs the whole test suite for real on Windows,
which will exercise this same function for real once run against this
fix).

### Changed
```
 docs/modules/tickets-verify-sweep.md       |  26 ++++++
 src/frob/app/ticket_runner/_rapid_sweep.py | 139 ++++++++++++++++++++++-------
 tests/unit/test_rapid_sweep.py             |  63 ++++++++++++-
 tickets/archive/T-2595/ticket.md           |  10 ++-
 4 files changed, 201 insertions(+), 37 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestBaselineLock::test_no_lock_primitive_refuses_loudly` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestBaselineLock::test_windows_backend_serializes_two_concurrent_holders` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestBaselineLock::test_serializes_two_concurrent_holders` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 17 error(s), 614 warning(s), 853 waived
- error-findings: COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, TICK004@tickets.md
