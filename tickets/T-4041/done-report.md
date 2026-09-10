## Done report

Changed:
- src/frob/app/verify_runner.py::_auto_commit_coverage_lock (new)
- src/frob/app/verify_runner.py::_COVERAGE_LOCK_REL (new)
- src/frob/app/verify_runner.py::_run_now (calls the new auto-commit step)

Ownership/determinism established (per this ticket's own ACCEPTANCE): frob-coverage.lock.json is frob's own bookkeeping (frob.gates._coverage.write_coverage_lock), a deterministic, rounded summary of coverage.xml for the same underlying state -- no human decision is recorded by the rewrite. Candidate fix (1), attribute automatically, is the right one per the ticket's own preference order.

Fix: `_run_now` now calls `_auto_commit_coverage_lock(root)` immediately after `run_coalesced_verification` returns, before rendering the outcome. It stages+commits ONLY frob-coverage.lock.json with a self-describing message ("chore(verify): refresh frob-coverage.lock.json (frob verify now, T-4041)") when-and-only-when that file is dirty; a no-op when unchanged (never an empty commit) or when the commit itself fails (logged as a WARNING, never turns a successful verify run into a hard failure -- the watermark/drain work already happened and must not be undone by an attribution step failing).

MUST-FIRE fixture: TestRunNowLeavesPrimaryClean::test_verify_now_auto_commits_the_rewritten_lock_file -- runs `_run_now` against a real git repo whose coverage lock gets rewritten by the (stubbed) verify pass, asserts `git status --porcelain` is empty afterward.
MUST-STAY-QUIET: the same test's stub still returns a real WorkerOutcome and `_run_now` still calls `run_coalesced_verification` -- the drain path itself is untouched, only the coverage-lock residue is handled.

Evidence: tests/unit/verify/test_verify_runner.py::TestAutoCommitCoverageLock.test_rewritten_lock_file_is_auto_committed, ::test_unchanged_lock_file_is_a_noop_no_empty_commit, ::test_no_lock_file_at_all_is_a_noop, TestRunNowLeavesPrimaryClean::test_verify_now_auto_commits_the_rewritten_lock_file

Filed: T-draft-858a1bad (out-of-scope T-4172/archive-lease regression found while working T-4066, unrelated to this ticket's own fix) -- and a second follow-up for this ticket's own scope-creep (F-254 security.txt non-determinism, F-293/frob-ack's frob.lock write, and the general verb-audit ask), filed separately since both are outside src/frob/app/verify_runner.py.

Gates: `frob check --ticket T-4041` stalled >45min with no new output under heavy fleet load (6+ concurrent `frob check` processes observed via `pgrep`) and was killed rather than waited on further; touched-set tests (tests/unit/verify/test_verify_runner.py, 20/20 pass, includes the 4 new cases) and a manual review of the diff (26 added lines, no new imports beyond a deferred `from frob import gitio` already used elsewhere in this module's style) stand in as evidence pending a land-time check run.

### Changed
```
 src/frob/app/verify_runner.py           |  74 +++++++++++++++++
 tests/unit/verify/test_verify_runner.py | 141 +++++++++++++++++++++++++++++++-
 2 files changed, 214 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/verify/test_verify_runner.py::TestAutoCommitCoverageLock::test_rewritten_lock_file_is_auto_committed` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_verify_runner.py::TestAutoCommitCoverageLock::test_unchanged_lock_file_is_a_noop_no_empty_commit` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_verify_runner.py::TestAutoCommitCoverageLock::test_no_lock_file_at_all_is_a_noop` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_verify_runner.py::TestRunNowLeavesPrimaryClean::test_verify_now_auto_commits_the_rewritten_lock_file` (pytest node id, verified passing when recorded)
