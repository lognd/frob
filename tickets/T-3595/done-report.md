## Done report

Split tests/unit/test_rapid_sweep.py (5055 lines, 42 test classes) into
7 per-gate-family modules under tests/unit/rapid_sweep_suite/ (baseline,
sweep_run, commit, attribution, filing, dispose, worktrees), mirroring
T-3586's recipe -- the last of the six monofile splits. Deleted the now-
empty source file (matching T-3594's precedent of full deletion, not a
re-export shim). Shared test helpers (_init_git_repo, _git_commit, _git,
_seed_repo, _seed_ticket) relocated to tests/conftest.py first, ahead of
the class splits, to avoid T-3650's self-import refusal; the shared
autouse liveness-gate fixture moved to a new package-local
tests/unit/rapid_sweep_suite/conftest.py. Every frob:tests citation of
the old path repointed to the new files, across src/, tickets/, and
design/frob.strata's capability via-lists (explicit paths, 1:1).

Evidence: 7 representative node ids across all 7 new modules; full
new-package suite green (`pytest tests/unit/rapid_sweep_suite/ -p
no:xdist -q` = 179 passed). Collection count preserved exactly: 179
before, 179 after.

Filed: none -- no out-of-scope work discovered beyond the already-
ticketed tool gaps below.

Gates: `uv run ruff check src tests` clean in this worktree.
`frob check --only drift --ticket T-3595` clean for this ticket's own
DRIFT002 tests-edges (2 pre-existing repo-wide findings remain --
WAIVE011 ratchet-lock staleness and a claude-config-drift notice, both
unrelated to and pre-dating this split). gate:SCOPE reports pre-
existing SCOPE002 findings tracing to tests/conftest.py's full existing
coverage graph (pytest_configure/pytest_sessionfinish/etc., none of
them the helpers this ticket relocated); chasing them with `scope
--add` cascades into unrelated modules (src/frob/mutate/_journal.py
and others). This predates T-3595's diff -- the ticket's own base scope
already names tests/conftest.py -- and widening scope to chase it would
violate "never expand scope on your own"; left as-is, flagged for a
coordinator follow-up if `frob ticket land` refuses on it.

Tool gaps encountered (all previously known, no new ones): T-3650 hit
once on _seed_repo referencing _git, worked around with the documented
exact-cut-and-paste-to-conftest recipe. T-3646 hit on
TestDetachedSweepEnv/TestDetachedSweepEnvPublicSeam and
TestFileRegressionTicket/TestFileRegressionTicketPublicSeam -- `frob
refactor split` itself refused with an overlapping-rewrite error rather
than silently mis-attributing, fixed by splitting those symbol pairs
into separate split calls (longer name first); citation destinations
verified correct afterward. T-3645 hit across all 7 destination
modules -- consolidated scattered per-symbol imports into one top block
per file with a script, then `ruff check --fix` plus hand-added module
docstrings and `from __future__ import annotations` to match the
source module's convention.

### Changed
```
 design/frob.strata                               |    6 +-
 src/frob/app/ticket_runner/_rapid_sweep.py       |  283 +-
 src/frob/tickets/_land_git_ops.py                |   29 +-
 tests/conftest.py                                |   90 +-
 tests/unit/rapid_sweep_suite/__init__.py         |    3 +
 tests/unit/rapid_sweep_suite/conftest.py         |   37 +
 tests/unit/rapid_sweep_suite/test_attribution.py |  995 +++++
 tests/unit/rapid_sweep_suite/test_baseline.py    |  734 ++++
 tests/unit/rapid_sweep_suite/test_commit.py      |  858 ++++
 tests/unit/rapid_sweep_suite/test_dispose.py     |  667 +++
 tests/unit/rapid_sweep_suite/test_filing.py      | 1162 +++++
 tests/unit/rapid_sweep_suite/test_sweep_run.py   |  508 +++
 tests/unit/rapid_sweep_suite/test_worktrees.py   |  150 +
 tests/unit/test_rapid_sweep.py                   | 5055 ----------------------
 tickets/T-1686/done-report.md                    |    2 +-
 tickets/T-1686/ticket.md                         |    2 +-
 tickets/T-2450/done-report.md                    |    4 +-
 tickets/T-2450/ticket.md                         |    4 +-
 tickets/T-3244/ticket.md                         |    2 +-
 tickets/T-3245/done-report.md                    |    4 +-
 tickets/T-3245/ticket.md                         |    6 +-
 tickets/T-3428/done-report.md                    |    4 +-
 tickets/T-3428/ticket.md                         |    4 +-
 tickets/T-3506/done-report.md                    |    2 +-
 tickets/T-3506/ticket.md                         |    2 +-
 tickets/T-3595/ticket.md                         |   84 +
 tickets/archive/T-1684/done-report.md            |    6 +-
 tickets/archive/T-1684/ticket.md                 |    8 +-
 tickets/archive/T-1690/done-report.md            |   20 +-
 tickets/archive/T-1690/ticket.md                 |   40 +-
 tickets/archive/T-1698/done-report.md            |    8 +-
 tickets/archive/T-1698/ticket.md                 |   10 +-
 tickets/archive/T-1753/done-report.md            |    4 +-
 tickets/archive/T-1753/ticket.md                 |    8 +-
 tickets/archive/T-1754/done-report.md            |    6 +-
 tickets/archive/T-1754/ticket.md                 |   12 +-
 tickets/archive/T-1755/done-report.md            |    8 +-
 tickets/archive/T-1755/ticket.md                 |   16 +-
 tickets/archive/T-1758/done-report.md            |    2 +-
 tickets/archive/T-1758/ticket.md                 |    4 +-
 tickets/archive/T-1791/done-report.md            |    8 +-
 tickets/archive/T-1791/ticket.md                 |   14 +-
 tickets/archive/T-1795/done-report.md            |    4 +-
 tickets/archive/T-1795/ticket.md                 |    8 +-
 tickets/archive/T-1821/done-report.md            |    4 +-
 tickets/archive/T-1821/ticket.md                 |    6 +-
 tickets/archive/T-1832/done-report.md            |    4 +-
 tickets/archive/T-1832/ticket.md                 |    6 +-
 tickets/archive/T-1841/done-report.md            |   10 +-
 tickets/archive/T-1841/ticket.md                 |   14 +-
 tickets/archive/T-1847/done-report.md            |    6 +-
 tickets/archive/T-1847/ticket.md                 |    8 +-
 tickets/archive/T-1865/done-report.md            |    6 +-
 tickets/archive/T-1865/ticket.md                 |    8 +-
 tickets/archive/T-1891/done-report.md            |    2 +-
 tickets/archive/T-1891/ticket.md                 |    4 +-
 tickets/archive/T-1935/done-report.md            |    6 +-
 tickets/archive/T-1935/ticket.md                 |    8 +-
 tickets/archive/T-1983/done-report.md            |   10 +-
 tickets/archive/T-1983/ticket.md                 |   12 +-
 tickets/archive/T-2006/done-report.md            |   12 +-
 tickets/archive/T-2006/ticket.md                 |   14 +-
 tickets/archive/T-2009/done-report.md            |   18 +-
 tickets/archive/T-2009/ticket.md                 |   18 +-
 tickets/archive/T-2030/done-report.md            |    8 +-
 tickets/archive/T-2030/ticket.md                 |   12 +-
 tickets/archive/T-2034/done-report.md            |   14 +-
 tickets/archive/T-2034/ticket.md                 |   18 +-
 tickets/archive/T-2036/done-report.md            |    2 +-
 tickets/archive/T-2036/ticket.md                 |    6 +-
 tickets/archive/T-2038/done-report.md            |    6 +-
 tickets/archive/T-2077/done-report.md            |   12 +-
 tickets/archive/T-2077/ticket.md                 |   14 +-
 tickets/archive/T-2078/done-report.md            |    4 +-
 tickets/archive/T-2078/ticket.md                 |   10 +-
 tickets/archive/T-2089/done-report.md            |   40 +-
 tickets/archive/T-2089/ticket.md                 |   24 +-
 tickets/archive/T-2100/done-report.md            |    4 +-
 tickets/archive/T-2100/ticket.md                 |   12 +-
 tickets/archive/T-2106/done-report.md            |    2 +-
 tickets/archive/T-2106/ticket.md                 |    2 +-
 tickets/archive/T-2165/done-report.md            |   16 +-
 tickets/archive/T-2165/ticket.md                 |   18 +-
 tickets/archive/T-2208/done-report.md            |   12 +-
 tickets/archive/T-2208/ticket.md                 |   40 +-
 tickets/archive/T-2261/done-report.md            |    4 +-
 tickets/archive/T-2261/ticket.md                 |   20 +-
 tickets/archive/T-2312/done-report.md            |    4 +-
 tickets/archive/T-2312/ticket.md                 |   12 +-
 tickets/archive/T-2313/done-report.md            |    6 +-
 tickets/archive/T-2313/ticket.md                 |   10 +-
 tickets/archive/T-2352/done-report.md            |   16 +-
 tickets/archive/T-2352/ticket.md                 |   12 +-
 tickets/archive/T-2521/done-report.md            |    6 +-
 tickets/archive/T-2521/ticket.md                 |    8 +-
 tickets/archive/T-2571/done-report.md            |   16 +-
 tickets/archive/T-2571/ticket.md                 |   20 +-
 tickets/archive/T-2595/done-report.md            |   22 +-
 tickets/archive/T-2595/ticket.md                 |   30 +-
 tickets/archive/T-2604/done-report.md            |   20 +-
 tickets/archive/T-2604/ticket.md                 |   14 +-
 tickets/archive/T-2669/done-report.md            |    8 +-
 tickets/archive/T-2669/ticket.md                 |    8 +-
 tickets/archive/T-2671/done-report.md            |   16 +-
 tickets/archive/T-2671/ticket.md                 |   12 +-
 tickets/archive/T-2672/done-report.md            |    8 +-
 tickets/archive/T-2672/ticket.md                 |    8 +-
 tickets/archive/T-2744/done-report.md            |    4 +-
 tickets/archive/T-2744/ticket.md                 |    4 +-
 tickets/archive/T-2794/done-report.md            |    2 +-
 tickets/archive/T-2794/ticket.md                 |    2 +-
 tickets/archive/T-2833/done-report.md            |    4 +-
 tickets/archive/T-2833/ticket.md                 |    4 +-
 tickets/archive/T-2918/done-report.md            |    6 +-
 tickets/archive/T-2918/ticket.md                 |    8 +-
 tickets/archive/T-2929/done-report.md            |    8 +-
 tickets/archive/T-2929/ticket.md                 |    8 +-
 tickets/archive/T-2938/done-report.md            |   10 +-
 tickets/archive/T-2938/ticket.md                 |   10 +-
 tickets/archive/T-2997/done-report.md            |    6 +-
 tickets/archive/T-2997/ticket.md                 |    4 +-
 tickets/archive/T-3051/done-report.md            |    6 +-
 tickets/archive/T-3051/ticket.md                 |    4 +-
 tickets/archive/T-3216/ticket.md                 |   12 +-
 tickets/archive/T-3222/ticket.md                 |   12 +-
 125 files changed, 5976 insertions(+), 5753 deletions(-)
```

### Evidence
- `tests/unit/rapid_sweep_suite/test_baseline.py::TestRollingBaseline::test_write_then_read_round_trips` (pytest node id, verified passing when recorded)
- `tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun::test_unmeasurable_check_leaves_the_baseline_untouched` (pytest node id, verified passing when recorded)
- `tests/unit/rapid_sweep_suite/test_commit.py::TestCommitRapidDebt::test_leaves_the_repo_clean` (pytest node id, verified passing when recorded)
- `tests/unit/rapid_sweep_suite/test_attribution.py::TestAttributeNewFindings::test_empty_queue_returns_empty_mapping` (pytest node id, verified passing when recorded)
- `tests/unit/rapid_sweep_suite/test_filing.py::TestRelativizeRegressionScopeFile::test_absolute_under_root_is_relativized` (pytest node id, verified passing when recorded)
- `tests/unit/rapid_sweep_suite/test_dispose.py::TestAutoDisposeFiledFindings::test_disposes_findings_the_ticket_covers` (pytest node id, verified passing when recorded)
- `tests/unit/rapid_sweep_suite/test_worktrees.py::TestSweepStaleWorktreesAfterLand::test_never_uses_force` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 14 error(s), 4409 warning(s), 1051 waived
- error-findings: ARCH102@src/frob/process/_lock.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, LARGE001@src/frob/refactor/_scan.py, LARGE001@src/frob/refactor/_verify.py, OPAQUE001@src/frob/app/_config_external.py, PRE001@tickets/T-3595, REL001@src/frob/__init__.py, SEC110@tests/ticket_land_suite/test_wip.py, SELFAUDIT001@docs/design/registry/capability-via-ratchet.lock.json, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
