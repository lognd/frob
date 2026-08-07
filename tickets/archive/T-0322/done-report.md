## Done report

Implemented the interim (pre-daemon) fix the ticket asks for: a foreground,
blocking, single-flight coverage contract, so an agent gets a definitive
fresh-or-failed result inline instead of backgrounding `make coverage` and
stalling on a notification a dispatched sub-agent can never receive
(docs/guides/agent-playbook.md section 6b/3b).

New src/frob/testing/_coverage_wait.py:
- run_coverage_wait(root, command=("make","coverage-fast")): acquires a
  cross-process fcntl.flock on .frob/coverage.lock (single-flight -- a
  concurrent caller blocks here instead of independently re-running the
  full suite), checks the recorded coverage stamp against the current
  source tree using the SAME staleness contract TEST006 already enforces
  (frob.gates.load_stamp's file_hashes), and either returns immediately
  (already fresh) or runs the command and returns the definitive result.
- coverage_lock_path/CoverageWaitOutcome/CoverageWaitError: small
  supporting public API, documented at docs/modules/testing.md#public-api.

Wired as `frob test --wait-coverage` (one new argparse flag on the
EXISTING test subcommand, not a new top-level CLI surface) in
src/frob/app/test_runner.py's run().

Scope was extended five times beyond the ticket's original declaration
(each via `frob ticket scope --add --reason`, audited in scope_changes):
src/frob/__main__.py (the one new argparse flag), pyproject.toml +
CHANGELOG.md (REL001's version bump for the new public API), and
docs/modules/testing.md + uv.lock (doc anchors for the new API; the
lockfile refresh that followed the version bump). None of these were
silent -- each carries its own scope_changes reason.

Verified `frob check --ticket T-0322 --base <T-0355's close commit>`
clean except the two pre-existing LANG003 errors this session's ticket 5
(T-0566) owns (unrelated c/cpp DOC004 bucket gap, already present before
this ticket's changes). Using --base against the prior ticket's close
commit (rather than main) was necessary because this worktree does five
tickets sequentially without landing between them -- checking straight
against main re-flags every PRIOR already-closed ticket's own diff as
"no frob:ticket edge to an OPEN ticket" (COV002) and "outside scope"
(SCOPE001) once that ticket closes, which is a multi-ticket-worktree
artifact, not a real regression.

### Changed
```
 CHANGELOG.md                       |  15 ++++
 docs/modules/testing.md            |  24 +++++
 pyproject.toml                     |   2 +-
 src/frob/__main__.py               |  43 ++++++++-
 src/frob/app/config.py             |   3 +
 src/frob/app/test_runner.py        |  31 +++++++
 src/frob/app/ticket_runner.py      |  77 ++++++----------
 src/frob/gates/__init__.py         |  13 +++
 src/frob/testing/__init__.py       |  10 +++
 src/frob/testing/_coverage_wait.py | 173 ++++++++++++++++++++++++++++++++++++
 tests/test_app.py                  | 143 ++++++++++++++++++++++++++++++
 tests/test_prework_parity.py       |  19 ++++
 tests/unit/test_main_entry.py      |  45 ++++++++++
 tickets.md                         | 177 +++++++++++++++++++++++++++++++++++--
 uv.lock                            |   2 +-
 15 files changed, 712 insertions(+), 65 deletions(-)
```

### Evidence
- `tests/test_app.py::TestRunCoverageWait::test_coverage_lock_path_is_under_frob_dir` (pytest node id, verified passing when recorded)
- `tests/test_app.py::TestRunCoverageWait::test_no_stamp_runs_command_and_reports_ran` (pytest node id, verified passing when recorded)
- `tests/test_app.py::TestRunCoverageWait::test_fresh_stamp_skips_the_run` (pytest node id, verified passing when recorded)
- `tests/test_app.py::TestRunCoverageWait::test_failed_command_is_err` (pytest node id, verified passing when recorded)
- `tests/test_app.py::TestWaitCoverage::test_wait_coverage_flag_dispatches_and_exits_zero_on_success` (pytest node id, verified passing when recorded)
- `tests/test_app.py::TestWaitCoverage::test_wait_coverage_flag_exits_1_on_failure` (pytest node id, verified passing when recorded)
