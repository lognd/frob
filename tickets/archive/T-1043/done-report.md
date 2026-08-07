## Done report

Root cause: not a land() logic bug. Mutation evidence's derived_state_lock
(acquired during land's pre-merge mutation check) legitimately creates
.frob/derived.lock as an on-disk advisory lock file in the worktree -- the
same scratch-artifact class as .frob/land.lock, which _status_ignoring_frob
(T-0577) already exists to filter out of "leaves no trace" assertions in
this test file. This one assertion (line 2109) predated that helper's
adoption at this call site and was never updated when the mutation-evidence
lock file started appearing, so it broke the moment that lock file started
being created on this code path.

Fix: use _status_ignoring_frob(wt) instead of the raw
`git status --porcelain` check, matching every other equivalent assertion
in tests/test_ticket_land.py. Test-only change; no production code touched.

### Changed
(no changed files detected)

### Evidence
- `tests/test_ticket_land.py::TestGitSubprocessFailures::test_unowned_deletions_diff_failure_after_merge` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 8 error(s), 5188 warning(s), 344 waived
- error-findings: ARCH001@src/frob/arch/_cpp_mayraise.py, COV001@src/frob/arch/_models.py, COV001@src/frob/gitlog/__init__.py, COV001@src/frob/process/parsers/common.py, COV001@src/frob/render/_color.py, COV001@src/frob/render/_elements.py, PERF003@src/frob/arch/_cpp_mayraise.py, PERF004@src/frob/arch/_cpp_mayraise.py
