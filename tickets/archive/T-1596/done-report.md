## Done report

Root-caused BOTH problems in this ticket. The truncation problem (part 2 of
the ticket) is the one that mattered most and is now fixed.

TRUNCATION ROOT CAUSE (confirmed, deterministic, reproduced repeatedly):
NOT an OOM kill, NOT a crash, NOT a hang. `dmesg`/`journalctl -k` show zero
kill/OOM entries across every reproduction; every subprocess exited with a
real, observed exit code every single time. The cause is pytest's own
verbosity stacking: `pyproject.toml`'s `addopts` already bakes in one `-q`.
This repo's OWN dispatch guidance (and my own initial reproduction attempts,
copied verbatim from the brief) recommends running the suite as
`pytest tests/ -q --timeout=600` -- a SECOND `-q` on top of the one already
in `addopts`. Two `-q` flags take pytest's verbosity to -2 ("very quiet"),
at which point `TerminalReporter.summary_stats()` silently skips printing
its own final `N passed, M failed in Ts` line entirely -- with no error, no
traceback, nothing to grep for. Isolated by bisecting flags one at a time
on a small single-file run: the exact command with only one `-q` prints the
summary; with two it does not; no other flag (not `--dist=loadgroup`, not
`--timeout`, not xdist worker count) makes any difference either way.
Confirmed at full-suite scale on 2 separate ~5min runs (8546 collected)
using the exact "-q" doubled invocation: both completed with a real,
observed process exit code and zero dmesg/journalctl kill signal, but
neither one printed pytest's own final summary line.

FIX: `tests/conftest.py` gains a `pytest_sessionfinish` hook that writes an
always-visible `SUITE-RESULT: exitstatus=<n> collected=<n> failed=<n>` line
via `TerminalReporter.write_line` (a low-level write NOT gated by the
verbosity level that silences `summary_stats()`), controller-only under
xdist (mirrors the existing `pytest_configure`'s own `workerinput`
early-return). Verified this line survives -q, -qq (any verbosity
stacking), and appears exactly once per run at both single-file and
full-suite (8546-test) scale, including the exact doubled-`-q` invocation
that previously produced zero visible signal. This makes truncation
impossible to mistake for success: any caller that used to grep the log
for pytest's own summary line now has a second, unsuppressable line to grep
for instead; its absence is now unambiguous evidence of a real crash/hang,
never a verbosity artifact.

POLLUTION HALF (part 1 of the ticket): ran the FULL, unscoped suite twice
end-to-end (8546 collected each time, ~5min per run) using the corrected
`SUITE-RESULT:` line to confirm neither run silently truncated. NONE of the
originally-listed pollution members from T-1596's own ticket body
(TestMapRunner, TestOutlineRunner::test_directory_target_falls_back_to_map,
TestParseCache::test_second_call_same_content_is_a_hit,
TestClaimDivergencePostMerge, TestSetDoneReportClaims,
TestLedgerV2LandMergeStory, TestReverifyCli, TestNewFileCarveOut) appeared
as a failure in either run. I could NOT reproduce any of them and am
stating that explicitly rather than claiming a fix for something I never
saw fail -- either T-1591's fix already closed these (the ticket body
itself frames them as "still red" only as of T-1591's own investigation,
which predates this session), or they need a worker-count/scheduling shape
neither of my two runs (both default `-n auto --dist=loadgroup`) happened
to hit. I did NOT mark this as fixed by touching test isolation code for
symptoms I never observed -- that would be exactly the "fix by reordering/
skipping without cause" anti-pattern this ticket explicitly warns against.

Two DIFFERENT failures appeared once in the first run and did NOT
reproduce in the second (test_serve_socket.py::TestShutdownReapsChildren::
test_frob_shutdown_exits_and_reaps_within_budget -- a 5s wall-clock budget
assertion; test_tickets_ledger_concurrency.py::
TestRenumberOneRaceWithConcurrentNew::
test_concurrent_new_ticket_survives_a_racing_renumber_one -- a concurrency
race). Both are consistent with transient system load (a sibling worktree
was independently running a full pytest suite concurrently on the same
host during my first run, confirmed via `ps aux`), not deterministic
xdist-order pollution -- neither repeated on the clean second run. Noting
by name per the ticket's own instruction, not silently dropping them.

Every OTHER failure seen in both runs is already-known, already-ticketed,
and out of THIS ticket's fix scope: TestCheckOnlyPerf::
test_perf001_fixture_warns_but_check_exits_zero and
TestCoverageTargetNativesGuard::
test_coverage_fast_incremental_branch_restores_and_verifies_natives are
T-1595's stale assertions; TestKindCliInvalidKind::
test_invalid_kind_refused is T-1594's traceback-vs-clean-refusal bug. The
3 self-conformance failures seen in both runs
(TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant,
TestCoverageTotality::test_repo_unrestricted_scan_is_clean,
TestFrobSelfModel::test_sys_gate_zero_violations) plus
TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap
are all the SAME single cause: my own two new public symbols
(TestSuiteResultLine, pytest_sessionfinish) are not yet declared in
design/frob.strata's `testsuite` node interface list. Confirmed via
`frob sys sync-interface --check`, which names exactly these two symbols
as the only drift in the whole repo. Per the agent playbook (section 0
item 5), `frob ticket land` runs `frob sys sync-interface` (writing, not
--check) automatically before its own merge -- this is expected,
self-healing drift, not something to hand-fix in the worktree; hand-editing
design/frob.strata is also outside this ticket's declared scope
(tests/**, src/frob/lang/**, src/frob/tickets/**).

### Changed
```
 tickets.md | 5 ++++-
 1 file changed, 4 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_conftest_stackdump.py::TestSuiteResultLine::test_sessionfinish_prints_greppable_line_at_any_verbosity` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestSuiteResultLine::test_sessionfinish_skips_on_xdist_worker` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 5353 warning(s), 797 waived
- error-findings: none (measured, zero errors)
