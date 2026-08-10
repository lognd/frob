## Done report

Delivered the three scripts recovered from the reverted ae567c5a2df5bc5cb2c21722a5d827d57fbf0b66
(check_summary.py, fleet_status.py, verify_lands.py -- smoke-tested working
implementations, unmodified in logic) under scripts/, plus the gate-satisfying
apparatus the reverted attempt was missing:

- docs/guides/coordinator-scripts.md: one frob:doc anchor per public symbol
  (including module-level constants REPO/WORKTREES/LEASES, each needing its
  own edge, not a shared one), plus a "Design and gate posture" section
  explaining the TEST001/SELFAUDIT001 choices below.
- TEST001: wrote REAL unit tests (tests/unit/test_coordinator_scripts.py,
  23 cases, all passing) rather than taking the .claude/hooks/** path-class
  exemption -- that precedent's rationale (harness-only invocation, no
  meaningful way to unit test outside it) does not transfer to this shape:
  every function here is ordinary importable Python, and subprocess/git
  calls are trivially monkeypatched. Extended the ticket's scope for the
  new test file via `frob ticket scope --add` before writing it.
- SELFAUDIT001: `scripts_ops` already existed in design/frob.strata (fs.write/
  fs.read only) but lacked the `exec` capability these scripts' subprocess.run
  calls need; added it, plus the same THREAT003 CWE-78 noflow-registry assume
  claude_hooks already carries, for the identical reason (fixed argv, no
  registry-derived bytes). Also declared `exec`/`fs.write` for the new test
  file under the `testsuite` node's existing via-lists.
- REL001: left to `frob ticket land` (T-0731 -- a worktree agent must never
  hand-bump pyproject.toml/CHANGELOG.md); it bumped to 0.414.0 automatically
  at land time.

DISCLOSURE: this ticket's own commit landed as a passenger of T-1850's land
(commit 46ce3d53d3b04ad210b407f22fd6287fb89650f1, --allow-cross-ticket used
and logged) because all six tickets in this dispatch group share one series
worktree/branch and T-1850 (a drop) happened to be the first one whose land
attempt hit the branch after T-1863's work was committed. is_ancestor_of_main
verified True for that commit. The frob:ticket T-1863 directives are real and
resolve; this ticket's own state transition (in-progress -> done) is recorded
separately in this commit.

Verification: full unscoped `uv run frob check` (two --budget 500 passes
covering gates-fast/gates-native/gates-security, plus separate --only lint
and --only static runs) against the post-merge main tip shows ZERO
severity=error diagnostics across all 43 gate families and all tool records
(ruff-check/ruff-format show warnings only, not errors -- confirmed by
reading severity off results[].diagnostics[].severity per this ticket's own
check_summary.py traversal).

### Changed
```
 tickets/T-1863/ticket.md | 26 ++++++++++++++++++++++++++
 1 file changed, 26 insertions(+)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestLoadReport::test_reads_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestLoadReport::test_reads_stdin` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestIterDiagnostics::test_yields_tool_and_diagnostic` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestIterDiagnostics::test_empty_results` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestSummarise::test_counts_by_severity` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestSummarise::test_collects_error_rows` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestCheckSummaryMain::test_exit_zero_when_clean` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestCheckSummaryMain::test_exit_one_when_errors` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestRootDirt::test_clean_repo` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestRootDirt::test_dirty_repo` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestLeases::test_reads_lease_records` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestLeases::test_no_lease_dir` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestLeases::test_unreadable_lease_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktrees::test_reports_idle_age` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktrees::test_no_worktree_dir` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestFleetStatusMain::test_exit_zero_when_clean` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestFleetStatusMain::test_exit_one_when_dirty` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestResolve::test_resolves_full_sha` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestResolve::test_unknown_sha_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestIsAncestor::test_true_when_ancestor` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestIsAncestor::test_false_when_not_ancestor` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestSubject::test_returns_commit_subject` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestVerifyLandsMain::test_distinguishes_unknown_from_missing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 23 passed (from 23 evidence id(s))
- gates: 0 error(s), 739 warning(s), 743 waived
- error-findings: none (measured, zero errors)
