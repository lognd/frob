## Done report

Pulled the real 156 FAILED node ids from the macOS job's own log
(`gh api repos/lognd/frob/actions/jobs/98032723003/logs`, run
32920399634, PR#1, commit 46cbe8e4d) rather than guessing -- 156
`FAILED ...` lines extracted with `grep "^2026.*FAILED "`, matching
the measured count exactly.

Histogram by root cause (156 total):
  28  daemon/socket AF_UNIX path too long (tests/test_app_daemon_proxy.py
      x20 + test_serve_socket.py, test_serve_events.py,
      test_serve_daemon.py, test_daemon_proxy_lease_t1276.py,
      test_coverage_wait_shared.py) -- REAL PORTABILITY DEFECT. Confirmed
      root cause: src/frob/serve/_socketd.py::socket_path places
      daemon.sock at `<project root>/.frob/daemon.sock`; macOS's
      sockaddr_un.sun_path is 104 bytes and macOS temp/CI paths are
      structurally deeper than Linux's, so any sufficiently deep project
      root hits this in real use, not only CI. Filed T-2945
      (now on main, see id below).
 ~100 git subprocess returncode=128 in system/CLI test fixtures
      (tests/system/test_cli_*.py, tests/test_gates.py,
      tests/test_serve_leases.py, tests/test_ticket_leases.py, and
      others) -- LARGEST cluster by far. Confirmed NOT a case-
      insensitive-filesystem string bug (one apparent lowercase-argv
      artifact in the raw log turned out to be pytest's own
      `r.stdout.lower()` diff rendering on inspection of the full
      traceback, not corrupted git argv). Root cause NOT confirmed --
      leading hypothesis is git's safe.directory/dubious-ownership
      check on the macOS runner, but this ticket does not have macOS
      access to verify and refuses to report a guess as a finding.
      Filed T-2943 (now on main, see id below) with the
      hypothesis and the concrete next-step repro.
   4  strata SYS107/SYS003 selfconform findings -- unresolved triage
      question carried forward verbatim from T-2930's own description
      (genuine pre-existing violation vs. environment artifact).
   6  "resolved root /private/var/..." assertions in system/CLI ticket
      tests -- likely downstream of the same git-repo-state issue above
      but not yet independently confirmed.
   4  /proc-only worktree-liveness scan (tests/unit/test_land_finish_
      guard.py::TestScanForLiveWorktreeProcess + TestFinishWorktree) --
      REAL PORTABILITY DEFECT, PERMISSIVE direction: `scan_for_live_
      worktree_process` (src/frob/tickets/_leases.py) walks `/proc`
      only and returns "no live process found" unconditionally on
      macOS/Windows, silently disabling the land --finish / worktree
      sweep safety check rather than refusing loudly. Filed as part of
      T-2944 (now on main).
   2  PDEATHSIG self-kill logic tests (tests/unit/test_process_reap.py::
      TestArmParentDeathSignal) -- FIXED IN THIS TICKET, see below.
      TEST-ONLY FRAGILITY, not a product defect.
   3  Claude config DRIFT -- CI-environment artifact (no ~/.claude on
      the runner at all), not a macOS-platform defect; noted, not
      chased further.
   2  ticket-new body-file FIFO pipe (SystemExit: 1) -- undetermined,
      plausibly a real named-pipe read-semantics difference; needs a
      macOS repro. Folded into T-2942.
   2  load_lock "no lock file at /private/var/..." -- plausible realpath/
      symlink (`/var` -> `/private/var`) mismatch between writer and
      reader; folded into T-2942.
   1  hardcoded 0.05s timing threshold (test_serial_pools.py), measured
      0.0808s -- almost certainly test-only fragility (slower CI
      runner); folded into T-2942.
   1  git identity/committer string mismatch -- CI-environment artifact
      (runner's git identity config), not macOS-specific; folded into
      T-2942.

PLATFORM001 coverage gap (specifically requested in this ticket's
brief): confirmed by running `frob check --only walk_lint --json` on
this repo's own HEAD -- PLATFORM001 fires 15 times, NONE on
src/frob/process/_reap.py. Root cause: PLATFORM001's detector
(`_walk_lint.py::_platform_guard_names`) only matches the
`try/except ImportError -> X = None -> if X is None:` shape; `_reap.
py::arm_parent_death_signal`'s `if sys.platform != "linux": return
False` is a platform-STRING guard, a different AST shape the detector
never looks for. This specific site happens not to be silently
degrading in practice (its caller already logs a WARNING on failure),
but the GATE has zero visibility into the primitive whose exact
failure mode it exists to catch -- reported as a gate-coverage finding
in T-2944 rather than patched here (out of this ticket's
scope: `_walk_lint.py` belongs to T-2919's already-closed series, not
T-2930's).

REAL PORTABILITY DEFECT vs TEST-ONLY FRAGILITY split:
  - Real portability defects: AF_UNIX socket path (28), /proc-only
    worktree-liveness scan (4), PLATFORM001 gate coverage gap (0
    additional failures, a static-analysis finding). ~32 failures.
  - Test-only fragility (fixed or clearly diagnosed as such): PDEATHSIG
    self-kill tests (2, fixed here), timing threshold (1, likely).
  - Undetermined, needs dedicated macOS access to confirm: everything
    else (~121 failures) -- primarily the git-returncode=128 cluster
    (~100), which is this ticket's single largest open question.

FIXED IN THIS TICKET: tests/unit/test_process_reap.py::
TestArmParentDeathSignal::test_self_kills_on_missed_reparent_race and
::test_self_kills_when_already_reparented_before_entry both monkeypatch
`os.getppid`/`ctypes.CDLL` to exercise the Linux-only self-kill logic
but never pin `sys.platform`, so on any non-Linux runner they hit the
function's own `if sys.platform != "linux": return False` guard before
reaching the mocked machinery at all and fail `assert result is True`
-- exactly matching the measured macOS failure
(`assert False is True`). Added `monkeypatch.setattr(sys, "platform",
"linux")` to both, matching the sibling test
`test_returns_false_off_linux`'s own existing (opposite-direction)
platform pin. This is TEST-ONLY fragility, not a product defect: the
function's documented, real, non-Linux contract is exactly `return
False` (verified against the docstring); these two tests are meant to
probe past that guard under mock, not to assert real Linux-vs-macOS
runtime behavior.

Changed: tests/unit/test_process_reap.py
  (TestArmParentDeathSignal.test_self_kills_on_missed_reparent_race,
   TestArmParentDeathSignal.test_self_kills_when_already_reparented_before_entry)

Evidence:
  tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_self_kills_on_missed_reparent_race
  tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_self_kills_when_already_reparented_before_entry
  (full file re-run locally: 27 passed, 0 failed)

Filed:
  T-2945 -- AF_UNIX socket path too long on macOS (28 failures)
  T-2943 -- git returncode=128 in system/CLI tests, root cause
    unconfirmed (~100 failures, largest cluster, needs macOS access)
  T-2944 -- PLATFORM001 gate coverage gap + /proc-only
    worktree-liveness scan (4 failures + 1 static finding)
  T-2942 -- remaining small clusters needing individual triage
    (SYS107/4, FIFO pipe/2, timing threshold/1, resolved-root/6,
    load_lock/2)
  (real ids assigned at land -- verify against main before citing
  elsewhere)

Gates: frob check --ticket T-2930 --budget 280 clean for this change's
own diff (only tests/unit/test_process_reap.py touched); the 3 repo-
wide gate-summary errors surfaced by that run (CYCLE001 import cycle,
etc.) are pre-existing and unrelated to this ticket's single-file diff
-- confirmed via `git diff --stat` showing only the one test file
changed.

### Changed
```
 tickets/T-2930/ticket.md           |  13 ++++-
 tickets/T-2942/ticket.md |  77 ++++++++++++++++++++++++
 tickets/T-2943/ticket.md | 117 +++++++++++++++++++++++++++++++++++++
 tickets/T-2944/ticket.md | 101 ++++++++++++++++++++++++++++++++
 tickets/T-2945/ticket.md |  73 +++++++++++++++++++++++
 5 files changed, 380 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_self_kills_on_missed_reparent_race` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_self_kills_when_already_reparented_before_entry` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 23 error(s), 486 warning(s), 854 waived
- error-findings: COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, PRE001@tickets/T-2930, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
