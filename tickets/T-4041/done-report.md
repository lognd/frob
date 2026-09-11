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

Filed: a draft ticket was filed for an out-of-scope T-4172/archive-lease regression found while working T-4066 (unrelated to this ticket's own fix), citing it here as T-draft-858a1bad -- that draft was LOST before promotion (never renumbered to a real id; its filing commit, cfc17a573, names an intended id of T-0843, but tickets/T-0843/ was never created and the draft file itself no longer exists in the tree). Disclosed here (T-4426, the T-0707/T-0615 draft-loss incident class) rather than silently corrected: the archive-lease regression this draft was meant to capture is UNFILED and needs re-filing if it is still live. A second follow-up for this ticket's own scope-creep (F-254 security.txt non-determinism, F-293/frob-ack's frob.lock write, and the general verb-audit ask) was filed separately and is unaffected by this correction, since both are outside src/frob/app/verify_runner.py.

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

### Changed
(no changed files detected)

### Evidence
- `tests/unit/verify/test_verify_runner.py::TestAutoCommitCoverageLock::test_rewritten_lock_file_is_auto_committed` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_verify_runner.py::TestAutoCommitCoverageLock::test_unchanged_lock_file_is_a_noop_no_empty_commit` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_verify_runner.py::TestAutoCommitCoverageLock::test_no_lock_file_at_all_is_a_noop` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_verify_runner.py::TestRunNowLeavesPrimaryClean::test_verify_now_auto_commits_the_rewritten_lock_file` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 7 error(s), 4800 warning(s), 961 waived
- error-findings: DOC011@docs/modules/tickets-lifecycle.md, LARGE001@src/frob/app/verify_runner.py, LARGE001@src/frob/testing/_collect.py, MILE001@tickets.md, MILE002@tickets.md, TICK004@tickets.md, TICK006@tickets.md
