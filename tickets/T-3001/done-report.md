## Done report

Changed:
- src/frob/app/ticket_runner/_land_cmd.py::_unscoped_error_findings (new `full` kwarg)
- src/frob/app/ticket_runner/_land_cmd.py::_unscoped_check_spawn_args (new, ARCH001 split)
- src/frob/app/ticket_runner/_land_cmd.py::_FULL_CHECK_TIMEOUT_S (new)
- src/frob/verify/_worker.py::_default_verify_fn (now calls full=True)
- docs/modules/tickets-verify-sweep.md (new "default verify_fn runs UNBUDGETED" section)

Measured full-run cost (uncontended, this repo, 2026-08-26): 332.85s wall
(`timeout 530 uv run frob check --json` with FROB_ALLOW_FULL_CHECK=1,
no --budget). Well under the 1800s hard ceiling `full=True` now uses.

Direction chosen: run the drain's default `verify_fn` UNBUDGETED
(`full=True`), not "back off under load" or "advance the watermark
partially". Backing off is already implemented separately for the
daemon path (lease-ceiling/memory-floor backpressure, T-1695) but is
orthogonal -- it decides WHETHER to run, not whether a run that does
happen completes. Partial/incremental watermark advancement was
considered and rejected: it is exactly the "smaller answer" T-1703
forbids (a subset of gates measured is not a smaller version of "the
commit is verified", it's a different, incomplete claim), so it was
not implemented. The actual defect was that every caller of
`run_coalesced_verification` (`frob verify now`, the detached
`ionice`-idle drain child, the daemon, the backpressure debouncer) is
NOT racing any wall-clock deadline of its own, so the `--budget`
ceiling `_unscoped_error_findings` applied to them was pure downside:
it could only truncate (never speed anything up for a caller nobody
is waiting on synchronously), and a truncated run is `Unmeasurable`
(zero value, T-1703). Removing the ceiling for exactly those callers,
while leaving `_land_cmd`'s own inline pre-commit/post-land sweeps
--budget-bounded (they DO race a land's deadline), removes the
truncation without touching either T-1703 or T-2929.

Demonstrated: seeded a 3-entry stale verify queue (no watermark) via
`record_intent`, started 4 CPU-bound busy processes as simulated fleet
load, then ran `run_coalesced_verification` (the exact production
path `frob verify now`/the drain use) twice against that load. Round 1
(baseline-established, 297.7s) and round 2 (green, watermark advanced,
queue compacted to 0, 100.3s) both completed -- neither was
Unmeasurable, neither deferred a stage group (full=True passes no
--budget, so BUDGET001 cannot fire at all). Final state: queue depth
0, watermark advanced to the tip commit. Re-ran the same demonstration
against the FINAL committed code (post ARCH001 split) with a second,
independent load run -- identical outcome.

Evidence:
- tests/test_ticket_land.py::TestUnscopedErrorFindingsFullMode::test_full_mode_omits_budget_flag_and_sets_allow_full_check_env
- tests/test_ticket_land.py::TestUnscopedErrorFindingsFullMode::test_full_mode_default_is_false_preserves_prior_budgeted_behavior
- tests/unit/verify/test_worker.py (39 pre-existing tests, unmodified, all pass -- confirms no regression to run_coalesced_verification's own contract)
- tests/unit/verify/test_drain.py (pre-existing tests, unmodified, all pass)
- Manual demonstration script (not part of ticket evidence -- mutates
  .frob/verify-* state directly via record_intent, which production
  code never does): /tmp/t3001_demo.py, output pasted into this report
  above and into the session transcript.

Filed: none (T-2991 is the sibling ticket in this same series, tracked separately).

Gates: `frob check --json --ticket T-3001` clean for every touched
file (0 errors) after the ARCH001 split; `frob check --only lint`
clean for touched files (one pre-existing, unrelated `ty`
unused-ignore-comment warning at src/frob/verify/_worker.py:416,
confirmed pre-existing by inspection -- unrelated to any line this
ticket touches, not waived here since waiving requires touching that
line and this ticket's scope does not cover that function).

### Changed
```
 docs/modules/tickets-verify-sweep.md    |  25 ++++++++
 src/frob/app/ticket_runner/_land_cmd.py | 108 +++++++++++++++++++++++++-------
 src/frob/verify/_worker.py              |  26 ++++++--
 tests/test_ticket_land.py               |  78 +++++++++++++++++++++++
 tickets/T-3001/ticket.md                |  69 +++++++++++++++++++-
 5 files changed, 277 insertions(+), 29 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestUnscopedErrorFindingsFullMode::test_full_mode_omits_budget_flag_and_sets_allow_full_check_env` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUnscopedErrorFindingsFullMode::test_full_mode_default_is_false_preserves_prior_budgeted_behavior` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 44 error(s), 1079 warning(s), 857 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2989/ticket.md, DOC006@tickets/T-2990/ticket.md, DOC006@tickets/T-2993/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3001, REF002@docs/modules/ci_report.md, REF002@docs/modules/ghio.md, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ghio.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK011@tickets.md
