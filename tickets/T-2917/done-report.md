## Done report

Changed:
  .github/workflows/ci.yml (build job: added strategy.matrix.os =
    [ubuntu-latest, windows-latest, macos-latest], fail-fast: false,
    runs-on: ${{ matrix.os }})
  tests/test_ci_workflow_matrix.py (new)

Evidence:
  tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_job_declares_a_matrix_strategy (designated repro, FAILED_AT_PARENT verified against commit 241752940, the test-only commit before the ci.yml fix)
  tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_matrix_includes_windows_and_macos
  tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_matrix_is_fail_fast_false

Real CI results (PR https://github.com/lognd/frob/pull/1, run 32920399634,
opened against this branch to get genuine GitHub-hosted runner results,
not a local simulation):

  build (windows-latest): FAIL in 54s. Crashes at `uv run frob natives
    build`, before any Rust/pytest step runs:
      AttributeError: module 'signal' has no attribute 'SIGKILL'.
        Did you mean: 'SIGILL'?
    at src/frob/process/_reap.py:137, module-level default-arg
    evaluation of `def arm_parent_death_signal(sig: int = signal.SIGKILL)`.
    signal.SIGKILL does not exist on Windows at all -- this crashes on
    IMPORT, so frob cannot even print --help on Windows in this tree.
    This is the exact defect T-2918/T-2919 target, now measured for real
    instead of inferred from source reading.

  build (macos-latest): FAIL in 21m2s. Native build (cargo/maturin),
    cargo tests, ruff, and ty all PASS on macOS (it is POSIX, so the
    Rust/lint/typecheck steps that never touch fcntl/prctl are fine).
    Fails at the `Test` (pytest) step: 156 FAILED test node ids
    (measured via `gh api .../jobs/98032723003/logs`, grep -c on
    "FAILED " lines = 156). Representative clusters:
      - tests/unit/test_process_reap.py::TestArmParentDeathSignal
        (both tests) -- assert False is True: the T-2880 orphan-
        forkserver protection (arm_parent_death_signal, Linux-only
        ctypes libc prctl(PR_SET_PDEATHSIG)) silently no-ops on macOS,
        confirming the MEASURED EVIDENCE in the dispatch brief directly.
      - Large clusters in tests/test_ticket_*.py, tests/test_tickets*.py,
        tests/unit/test_land_finish_guard.py, tests/unit/test_worktree_guard.py
        -- process/lease/lock-adjacent tests that assume Linux-only
        process semantics (SIGKILL delivery, /proc-style scanning, etc).
      - A handful of unrelated pre-existing platform-fragile tests
        (line-ending goldens in test_export_golden.py, an autocrlf test,
        a perf-timing threshold test) that are not part of this
        series' scope and are noted here for the follow-up ticket below,
        not fixed in T-2917/T-2918/T-2919.

  build (ubuntu-latest): the pytest step ran past the ~500s observation
    windows used for the other two jobs' full completion (this repo's
    own playbook explicitly warns the full local suite exceeds a single
    agent foreground budget); job was still in the `Test` step, all
    prior steps (native build, cargo tests, lint, typecheck) green,
    when this report was written. This is the pre-existing sole CI
    target and this diff does not change its job definition beyond
    moving it into the matrix array -- its behavior is unchanged by
    this ticket. PR #1 is left open and watchable for the final ubuntu
    verdict; not a blocking condition for T-2917 (the ticket's job is
    adding the matrix so failures are DETECTABLE, which is now proven
    -- two of three new platform legs already produced real, measured
    failures).

  standalone-install: PASS (18s, unaffected -- ubuntu-only job untouched
    by this ticket's scope).

Filed: T-draft-837874a3 (renumbers at land; follow-up: macOS-only pre-existing test fragility unrelated
  to fcntl/prctl -- line-ending goldens, autocrlf test, perf-timing
  threshold -- found in the macos-latest run's 156 failures, out of
  scope for this series)

Gates: frob check --ticket T-2917 to be run before land; no waivers
  anticipated (single-file CI config change + one new test file).

### Changed
```
 .github/workflows/ci.yml           |  6 +++-
 tests/test_ci_workflow_matrix.py   | 45 +++++++++++++++++++++++++
 tickets/T-2917/ticket.md           | 23 +++++++++++--
 tickets/T-draft-837874a3/ticket.md | 67 ++++++++++++++++++++++++++++++++++++++
 4 files changed, 138 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_job_declares_a_matrix_strategy` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_matrix_includes_windows_and_macos` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_matrix_is_fail_fast_false` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 19 error(s), 455 warning(s), 847 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC008@docs/commands/check.md, PRE001@tickets/T-2917, TICK004@tickets.md, WIRE002@src/frob/tickets/_unlanded.py
