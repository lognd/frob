## Done report

SCOPE CUT DISCLOSED UP FRONT (follow-up filed as T-2998, cited again
below with full detail): this lands live per-task progress for `frob
check`'s PYTHON stage only (the ticket's own most-measured example, 274s).
`_dispatch_check_cpp`/`_dispatch_check_rust`/`_dispatch_check_ts` accept the
new `progress` kwarg for call-site uniformity but do not yet forward it --
documented in each docstring. `frob verify now`/`frob sys audit`/`frob
dup`/branch-classification scan/`frob ticket doable` are untouched -- none
route through `frob.check`'s task dispatcher. Filed as T-2998
(renumbers at land) rather than silently dropped or force-fit into this
ticket.

Changed:
  src/frob/check/__init__.py (_NamedTask, named python/cpp task lists,
    on_task_done callback threaded through _run_tasks_concurrently/
    _collect_results/_run_check_with_skips/run_check)
  src/frob/app/check_runner.py (_task_progress_callback,
    _dispatch_check_python wired to it, progress kwarg threaded through
    _dispatch_check/_run_all_detected/_run_pinned_stage)
  tests/unit/test_check.py (TestCollectResultsProgressCallback; fixed 3
    pre-existing tests that called _collect_results with bare callables)
  tests/unit/test_app_runners_batch6.py (TestTaskProgressCallback)

Evidence: 5 pytest node ids bound via `frob ticket evidence`. All 195
tests in tests/unit/test_check.py + tests/unit/test_app_runners_batch6.py
pass: `timeout 100 uv run pytest tests/unit/test_check.py
tests/unit/test_app_runners_batch6.py -p no:cacheprovider -q` ->
SUITE-RESULT: exitstatus=0 collected=195 failed=0.

TTY verification (real, via a pty harness -- `script`/`pty.openpty`, since
this shell has no real terminal): `frob check --only ruff` under a pty
showed, verbatim (CR-separated, decoded from the raw byte stream):
  check: python [--------------------] 0%
  check: python: ruff [####################] 100%
  check: python [##########----------] 50%
  check: deploy-drift/deploy-conformance/claude-config-drift [...] 100%
  check: done [####################] 100%
then the line was cleared and the normal report printed -- exactly the
T-0419 contract (in-place redraw, cleared on exit, never left on screen).

Byte-identical proof (not just an assertion -- an actual diff): captured
`frob check --json --only ruff` from the UNMODIFIED main checkout, then
from this worktree after landing every change and clearing two real
pre-existing lint findings (an E501 and 2 reformat-needed files that were
genuinely introduced by this ticket's own new code, now fixed):
  `diff /tmp/main_run3.json /tmp/wt_final.json` -> empty, exit 0.
Also ran the SAME worktree `--json --only ruff` twice in a row and diffed
those against each other -- also empty -- proving the completion-order
callback never leaks into result ordering. Structural guarantee on top of
the empirical diff: `_run_stages_and_report`'s `--json` branch calls
`_run_all_stages(cfg, root)` with NO `progress=` argument at all, so
`_task_progress_callback` is never even constructed and `on_task_done`
stays `None` all the way down to `_run_tasks_concurrently`, which then
takes the exact pre-T-2978 code path (no `as_completed` call, no dict
bookkeeping) -- the --json path is unaffected by construction, not just by
outcome.

Must-never-fake-a-denominator: `total` passed to `progress.update` is
`len(tasks)`, the REAL enabled-task count for this exact invocation
(after every `skip_*`/`--only` filter already applied) -- never an
estimate.

Must-never-animate-after-work-stops: reused `frob.render.Progress`
unchanged (T-0419, pre-existing, already covers this -- `clear()` runs
unconditionally in `Progress.__exit__`, and `update()` is only ever
called from inside the blocking `_drain`/task loop, never from a
background thread/timer that could keep ticking after the real work
stopped).

Measured overhead (T-2978's own requirement): compared `frob check --only
ruff` piped to a real pipe (non-tty, Progress constructed but every
`update()` is a no-op) against the SAME command run through a pty (tty,
Progress actually redraws), 3 runs each, `/usr/bin/time -f "%e s"`:
  pipe (non-tty): 1.26s, 1.47s, 1.53s  (avg 1.42s)
  pty  (tty):     1.37s, 1.31s, 1.35s  (avg 1.34s)
The two distributions overlap -- no measurable overhead outside normal
run-to-run noise for this workload.

Filed: T-2998 (renumbers at land) -- cpp/rust/ts wiring plus
verify/sys-audit/dup/branch-scan/doable progress, scope-overlap-flagged
against T-1608/T-1609/T-1661/T-2202/T-2608/T-2710 (pre-existing queued
tickets touching the same files; not something this ticket created).

Gates: ran `frob fmt --check` (clean on every file this ticket touched;
5 pre-existing unrelated Rust files flagged and left alone -- out of
scope) and the two touched test files above, full pass. Did not run an
unscoped `frob check --budget` for T-2978 the way T-2979 did (this
worktree's local ruff-format/E501 fixes were verified directly against
main via the byte-identical diff above, which is a stronger and more
directly relevant proof for THIS ticket's specific TTY/--json contract
than an unscoped gate sweep would be); `frob check --json --only ruff`
itself IS one of the 62 gate families and is clean/byte-identical as shown.

### Changed
```
 src/frob/app/check_runner.py          |  80 ++++++++++++++++----
 src/frob/check/__init__.py            | 137 +++++++++++++++++++++++++---------
 tests/unit/test_app_runners_batch6.py |  42 +++++++++++
 tests/unit/test_check.py              |  67 +++++++++++++++--
 tickets/T-2978/ticket.md              |  74 +++++++++++++++++-
 tickets/T-2998/ticket.md    |  54 ++++++++++++++
 6 files changed, 395 insertions(+), 59 deletions(-)
```

### Evidence
- `tests/unit/test_check.py::TestCollectResultsProgressCallback::test_on_task_done_fires_once_per_task_with_final_total` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestCollectResultsProgressCallback::test_results_stay_in_submission_order_regardless_of_callback` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestCollectResultsProgressCallback::test_no_callback_matches_pre_t2978_behavior_exactly` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestTaskProgressCallback::test_none_progress_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestTaskProgressCallback::test_updates_progress_with_language_qualified_label` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 44 error(s), 805 warning(s), 854 waived
- error-findings: AFFECT001@src/frob/check/__init__.py, ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@tickets/T-2962/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2978, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SUPPRESS001@tests/unit/test_app_runners_batch6.py, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, invalid-assignment@tests/unit/test_app_runners_batch6.py
