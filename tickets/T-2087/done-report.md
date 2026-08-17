## Done report

Changed:
src/frob/testing/_coverage_refresh.py::_WORKER_CRASH_SIGNATURE_RE
tests/test_coverage.py::TestWorkerCrashSignatureRealSubprocess (new)

Investigation (acceptance criterion 1): reproduced two real worker crashes
against this repo's pinned pytest-xdist (3.8.0) -- a voluntary `os._exit(1)`
and a real `os.kill(os.getpid(), signal.SIGKILL)`, both inside an actual
`pytest -n <N>` subprocess, no mocking. Both produced the same two real
message shapes:

- `replacing crashed worker gwNN` (matches the OLD regex's third
  alternative already -- this is why the mechanism was not silently
  broken end to end in production, contrary to the ticket's initial "may
  never trigger automatically" concern)
- `worker 'gwNN' crashed while running '...'` (the summary line -- this
  did NOT match the old regex: `worker\s+gw\d+\s+crashed` has no room
  for the surrounding quotes the real message actually carries)

The ORIGINAL `INTERNALERROR>...KeyError: <WorkerController gwNN>` shape
(acceptance criterion 3) was NOT reproduced on this xdist version despite
both crash mechanisms above -- it may be specific to an older xdist this
repo has since upgraded past. The pattern is kept (matching it costs
nothing) but is not the primary real-world match path on this version.

Fix (acceptance criterion 2): widened the summary-line alternative to
`worker\s+'?gw\d+'?\s+crashed` (both quote styles, and none, in one
pattern). Added `TestWorkerCrashSignatureRealSubprocess` with 3 tests:
two real-subprocess repros (os._exit, SIGKILL) proving the whole detection
path works end to end, plus a fast unit-level regression lock
(`test_summary_line_alone_matches_the_quoted_node_id`) isolating the
summary-line branch specifically (no `replacing crashed worker` line
present, unlike the two real-subprocess cases) so a future edit cannot
silently reintroduce the quote mismatch.

Confirmed a genuine repro per T-1929/BUG002: committed the test file
alone first (commit 0eea3fa91a2db81514cc9e26d414c6d6d0ab994f, still
carrying the OLD unfixed regex), ran it and confirmed it genuinely fails
(AssertionError, regex does not match the quoted summary line), THEN
applied the regex fix as a second commit
(43343234e...). `--designate-repro --base-ref
0eea3fa91a2db81514cc9e26d414c6d6d0ab994f` confirms FAILED_AT_PARENT.

Evidence:
tests/test_coverage.py::TestWorkerCrashSignatureRealSubprocess::test_summary_line_alone_matches_the_quoted_node_id (designated repro, FAILED_AT_PARENT confirmed against the test-only commit)
tests/test_coverage.py::TestWorkerCrashSignatureRealSubprocess::test_os_exit_worker_crash_is_a_real_repro
tests/test_coverage.py::TestWorkerCrashSignatureRealSubprocess::test_sigkill_worker_crash_is_a_real_repro

Full-file run: `uv run pytest tests/test_coverage.py -p no:cacheprovider -q -o addopts=""` -- 51 passed (SUITE-RESULT: exitstatus=0 collected=51 failed=0)

Filed: none (no out-of-scope work found)
Gates: uv run frob check --ticket T-2087 (see session output; no new findings attributable to this change)

### Changed
```
 src/frob/testing/_coverage_refresh.py | 37 +++++++++++++++---
 tests/test_coverage.py                | 73 +++++++++++++++++++++++++++++++++++
 tickets/T-2087/ticket.md              |  8 +++-
 3 files changed, 110 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_coverage.py::TestWorkerCrashSignatureRealSubprocess::test_summary_line_alone_matches_the_quoted_node_id` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestWorkerCrashSignatureRealSubprocess::test_os_exit_worker_crash_is_a_real_repro` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestWorkerCrashSignatureRealSubprocess::test_sigkill_worker_crash_is_a_real_repro` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2087/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2087/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2087/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2087/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2087/tests/test_ticket_land.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2087, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
