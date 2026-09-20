## Done report

Root cause: `_measure_fresh_and_write_baseline` CAS-wrote `fresh` as the
new rolling baseline UNCONDITIONALLY, before `run_deferred_post_land_
sweep` even computed `new_findings` or decided whether they got filed.
When T-2929's stale-verification-queue guard refused to file a genuinely
new `(rule, file)` identity, the baseline had already absorbed it as
though it were pre-existing debt -- every later sweep compared against
a baseline that had already been taught the error was normal, and
printed the self-contradictory "CLEAN (N error(s))".

Fix: split the write out of the measurement step (now `_measure_fresh_
sweep_state`, measure-only) into a new `_persist_baseline` helper that
`run_deferred_post_land_sweep` calls explicitly, per branch, only once
it knows what is actually accounted for:
- no prior baseline (first sweep) -> persist everything found
  (establishing, not growing, the baseline) -- unchanged from before.
- no new identities vs. the prior baseline -> persist `fresh`; log the
  nonzero-fresh case as "N pre-existing error(s) ... TOLERATED DEBT, not
  clean" instead of the old self-contradictory "CLEAN (N error(s))".
- new identities found and filed (or disposed to an existing duplicate)
  -> persist `fresh` (unchanged from before -- now safe, since a ticket
  tracks them).
  new identities found but REFUSED (stale verification queue) -> persist
  only `fresh - new_findings` (the previously-known set); the refused
  identities are deliberately excluded so the next sweep still sees them
  as new and gets a real chance to file once the queue is current.

Verified both directions, forced (not just on a clean tree):
- `test_stale_baseline_refusal_is_still_new_on_the_next_sweep`: a first
  sweep that refuses to file (stale queue) does NOT rebaseline the
  refused identity; a second sweep with the same fresh set and a
  now-current queue DOES file it. This reproduces the exact T-4324 ->
  T-4329 shape the ticket measured from the real sweep logs.
- `test_stale_baseline_refuses_to_file_and_records_debt` (existing test,
  updated): asserts the persisted baseline stays at the prior known set,
  not the old (buggy) `fresh`.
- `test_inherited_debt_is_reported_as_debt_not_clean`: zero new findings
  but nonzero fresh count no longer logs "CLEAN (N error(s))".
- `test_genuinely_zero_errors_still_says_clean`: the truly-zero case
  still logs CLEAN plainly.
- `test_writes_and_logs_survival_warning_on_loss`: `_persist_baseline`
  unit coverage for the extracted write helper.
- Pre-existing suite (`tests/unit/rapid_sweep_suite/`, 184 tests) still
  green, including the first-run/unmeasurable/normal-filing paths this
  change deliberately left unchanged.

Changed:
- src/frob/app/ticket_runner/_rapid_sweep.py::_measure_fresh_and_write_baseline
  (renamed `_measure_fresh_sweep_state`, write removed)
- src/frob/app/ticket_runner/_rapid_sweep.py::_persist_baseline (new)
- src/frob/app/ticket_runner/_rapid_sweep.py::run_deferred_post_land_sweep
  (per-branch persist decision + fixed CLEAN/debt reporting)
- tests/unit/rapid_sweep_suite/test_sweep_run.py (new/updated tests above)

Filed: T-4344 ("Update deferred-sweep doc for T-4335's
baseline-persist contract") -- docs/modules/tickets-verify-sweep.md's
"Deferred post-land sweep" section still describes the OLD "every
sweep, red or green, rewrites the baseline regardless" contract. Left
out of this ticket's own scope because the doc's `frob:describes`
network pulls in ~170 unrelated symbols across the whole verify/land
subsystem the moment the file enters scope closure -- filed separately
rather than expanding scope unilaterally.

Gates: `frob check --json` reports 4 errors: 2 are docs/modules/
verify-rapid-debt-visibility.md (INV003, REF002), owned by T-4334 and
pre-existing, not touched by this change. The remaining 2 (PRE001,
SCOPE001, "no active ticket is derivable") are `frob check`'s branch-
name-derivation gate not recognizing this worktree's lowercase `t-4335`
branch name -- an artifact of how `frob ticket work` names branches, not
a code correctness issue; `frob check --ticket T-4335` resolves those
two and passes cleanly for everything this ticket's own scope owns
(a DRIFT001 finding on `run_deferred_post_land_sweep`, whose external
contract genuinely did change, is waived in-line with a reason pointing
at the T-4344 follow-up, matching this same file's existing
T-2521/AFFECT001 waiver precedent for the identical doc-closure-
explosion shape). `frob test --base main` (touched-set): 11 python
test(s), exit=0.

### Changed
```
 tickets/T-4335/ticket.md           | 38 ++++++++++++++++++++++++++++++++++++++
 tickets/T-4344/ticket.md | 29 +++++++++++++++++++++++++++++
 2 files changed, 67 insertions(+)
```

### Evidence
- `tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun::test_stale_baseline_refusal_is_still_new_on_the_next_sweep` (pytest node id, verified passing when recorded)
- `tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun::test_inherited_debt_is_reported_as_debt_not_clean` (pytest node id, verified passing when recorded)
- `tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun::test_genuinely_zero_errors_still_says_clean` (pytest node id, verified passing when recorded)
- `tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun::test_stale_baseline_refuses_to_file_and_records_debt` (pytest node id, verified passing when recorded)
- `tests/unit/rapid_sweep_suite/test_sweep_run.py::TestPersistBaseline::test_writes_and_logs_survival_warning_on_loss` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 3 error(s), 4697 warning(s), 963 waived
- error-findings: INV003@docs/modules/verify-rapid-debt-visibility.md, REF002@docs/modules/verify-rapid-debt-visibility.md, SCOPE002@tickets.md
