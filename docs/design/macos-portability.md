# macOS portability boundary (T-3488)

One sentence: `macos-latest` in `ci.yml` stays a real, blocking, REQUIRED
CI leg -- unlike `windows-latest` (docs/design/windows-portability.md),
its own failure set is small (~32 tests) and mechanical, so it does not
get an advisory carve-out.

## Why this doc exists

T-3488 characterized the macOS-only failure set on GitHub Actions run
33311990183 (macos-latest, HEAD `986f8671c`, 2026-08-30): with the 40m
budget (T-3482) macOS completes the suite in 26.5 min with 39 failures;
`ubuntu-latest` on the same HEAD has 6 (all owned by other tickets).
Subtracting the shared set leaves a macOS-ONLY set of ~32 tests, stable
across the last 5 completed macOS runs (51 -> 38 -> 39 -> 39). Three
buckets were cheap and mechanical enough to fix directly under T-3488;
the rest are tracked as one follow-up ticket per bucket, the same
per-bucket-ticket shape T-3076 used for Windows.

## Buckets fixed under T-3488

- **Bucket A -- GNU coreutils absent (2 tests,
  `tests/system/test_ci_hang_guard_positive_control.py`).** macOS has no
  GNU `timeout` (T-3250 already documents this for `ci.yml`'s own Test
  step). The positive control now runs the SAME bash `kill -ABRT`
  background-watcher shape `ci.yml`'s macOS Test step uses (`_WATCHER_SH`
  in the test module) instead of shelling to `timeout`, so it is
  hermetic and identical on Linux and macOS. A `win32` skip remains,
  stated as a PLATFORM001 boundary (the watcher is bash/kill/sleep,
  POSIX-only, the same boundary `ci.yml`'s Windows Test step already
  carries advisory-only under T-3425).

- **Bucket B -- runner git identity preset (1 test,
  `tests/test_ticket_leases.py::TestCommitTicketLedgerChange::
  test_identity_less_environment_falls_back_to_throwaway_git_identity`).**
  The macOS GitHub Actions runner image ships a global `user.name`/
  `user.email` (observed: `Anka <runner@...92399F.local>`). The test
  already redirected `HOME` to isolate itself, but git also consults
  `GIT_CONFIG_GLOBAL` (and, absent that, XDG config paths) ahead of
  `$HOME/.gitconfig` on some git versions/platforms, so a real global
  file outside the faked `HOME` could still be read. The test now also
  pins `GIT_CONFIG_GLOBAL=/dev/null`, making it hermetic to the runner's
  own identity on any platform.

- **Bucket G -- toolchain: cargo ANSI stderr (1 test,
  `tests/system/test_natives_build_integration.py::
  test_build_natives_compiles_and_imports_real_crate`).** `build_natives`
  inherits the calling process's environment into the `maturin develop`/
  cargo subprocess. On macOS CI, cargo emits ANSI-colored progress lines
  ("Updating crates.io index") on stderr; the test now pins
  `CARGO_TERM_COLOR=never` before calling `build_natives` (and strips any
  residual ANSI from the failure diagnostic it prints), so the captured
  output is plain text and parses/compares identically regardless of the
  ambient shell's color-forcing env vars -- the same class of fix as
  T-1586's `FORCE_COLOR`/`NO_COLOR` neutralization in `tests/conftest.py`.

## Buckets tracked as follow-ups (not fixed here)

Each below is filed as its own ticket (per-bucket, T-3076 pattern) with
the measured assertion text as its own evidence; a real root cause was
not fully pinned down for any of these from a Linux box, so each
follow-up's own first task is to measure against a macOS box or the
`-vv` CI log before attempting a fix.

- **Bucket C -- live-process / cwd detection (7 tests) -- RESOLVED
  (T-3528).** The scanner behind `tests/unit/test_land_finish_guard.py`
  (4), `tests/test_ticket_leases.py::TestRemoveWorktree::
  test_keeps_a_live_process_worktree`, `tests/test_worktree_guard.py`
  (1), and `tests/test_mutate_journal.py::
  test_recycled_pid_with_mismatched_starttime_is_treated_stale` used to
  read `/proc` directly, which does not exist on macOS. T-3500 already
  added a `sys.platform == "darwin"` dispatch for every one of these
  code paths -- `_pid_starttime_darwin` (`ps -o lstart=`,
  `src/frob/mutate/_journal.py`), `_proc_cmdline_darwin` (`ps -ww -o
  command=`) and `_proc_cwd_darwin`/`_live_pids_with_cwd`'s `lsof -a -d
  cwd -Fpn` branch (`src/frob/tickets/_leases.py`), which
  `scan_for_live_worktree_process`/`_scan_for_live_land_process`
  (the scanners `tests/unit/test_land_finish_guard.py` and
  `tests/test_worktree_guard.py` exercise) and `_is_stale`
  (`tests/test_mutate_journal.py`) already call through. T-3528
  re-measured this bucket (2026-08-31) and found the fallback fully
  wired on every scoped file except one: the bucket's own file list
  <!-- frob:waive DOC006 reason="names a module that NEVER existed, illustrating why the scope claim below is accurate -- not a live pointer" -->
  named `src/frob/tickets/_land_finish_guard.py`, which never existed
  as a separate module -- the guard logic these tests cover lives in
  `src/frob/tickets/_leases.py` and `_worktree_guard.py` instead, both
  already covered above. No PLATFORM001 boundary needed; this bucket
  is closed.

- **Bucket D -- citation/text scans return 0 (13 tests).**
  `tests/test_tickets_live_tracker.py` (11) and
  `tests/test_gates.py::TestWireGate` (2) all show a scan that finds N
  hits on Linux finding 0 on macOS -- one shared root cause (GNU vs BSD
  `grep` flags, `-P`/PCRE support, or APFS case-insensitivity breaking a
  path-keyed match) rather than 13 independent bugs.

- **Bucket E -- scope `;` validation (3 tests,
  `tests/test_tickets.py::TestScopeGlobValidation`).** A `;`-joined scope
  entry is refused on Linux but accepted on macOS -- likely a
  `shlex`/posix-mode or glob-library difference in how the CLI parses a
  `--scope` argument. This is a correctness bug (the entry should be
  refused everywhere), not a platform boundary to declare.

- **Bucket F -- subprocess/env (4 tests).** Four distinct suspects:
  a shell-metacharacter-injection guard assertion
  (`tests/test_tickets_evidence_cli.py`), an `AF_UNIX` socket path-length
  difference (macOS's 104-byte `sockaddr_un` cap vs Linux's 108, likely
  tripped by macOS's longer `/private/var/folders/...` tmp path prefix,
  `tests/test_app_daemon_proxy.py`), a worker-crash-recovery coverage
  count off by one (`tests/test_coverage.py`), and a `killpg` targeting a
  process group the macOS runner sandbox refuses to signal
  (`tests/test_coverage_sigterm.py`).

- **Bucket H -- lint-diff attribution (1 test,
  `tests/test_ticket_land_lint_diff_attribution.py::...::
  test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse`).**
  `SystemExit: 1` with no measured root cause yet -- left as "unknown,
  measure" by the parent ticket.

## Keeping the leg required

Unlike Windows, macOS's failure set here is small (~32 of ~12800+ tests)
and every bucket has either a mechanical fix or a plausible, narrow
suspect list -- none of it is the epic-sized POSIX-primitive gap T-3076
found on Windows. `macos-latest` therefore stays a normal, blocking
`ci.yml` leg with no `continue-on-error`; each follow-up ticket above
should shrink the remaining set rather than argue for making the leg
advisory.
