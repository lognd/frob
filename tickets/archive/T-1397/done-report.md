## Done report

Confirmed the reported defect by reading the live Makefile: coverage-fast's
incremental (xargs) branch pointed COVERAGE_PROCESS_START directly at
pyproject.toml (relative source/data_file), the same Loss-A shape T-1235
fixed for coverage: by generating a dedicated .frob/coverage-subprocess.rc
with absolute paths.

Fix: factored .frob/coverage-subprocess.rc generation into its own plain
Make file target (content is deterministic -- only $(CURDIR)-dependent,
constant for the checkout's lifetime -- so a file target that only
regenerates once, rather than a recipe re-run on every invocation, is
correct and also directly implements the ticket's own suggested fix
wording: "reuse .frob/coverage-subprocess.rc if coverage: has already run
once"). coverage: still unconditionally rm's and regenerates it at the top
of every real run (rm -f .coverage .coverage.* .frob/coverage-subprocess.rc)
to preserve its existing always-fresh behavior; coverage-fast now depends
on the same file target and points COVERAGE_PROCESS_START at it instead of
pyproject.toml, so a coverage-fast-only run (no prior coverage: run) still
generates the correct absolute-path rc rather than needing one to already
exist.

Verified: make .frob/coverage-subprocess.rc run directly produces the
expected absolute-path rc content (manually inspected: source and
data_file both resolve to this checkout's absolute path). make -n coverage
and make -n coverage-fast dry-run cleanly with correctly expanded
COVERAGE_PROCESS_START values, no shell-quoting/expansion regressions.

Three new regression tests in tests/unit/test_makefile_coverage.py
(TestCoverageFastUsesAbsoluteSubprocessRc) lock: (1) the literal
pyproject.toml Loss-A shape can never reappear, (2) coverage-fast's own
recipe text depends on and uses the shared rc, (3) the rc-generating printf
block exists in exactly one place (not duplicated across the two targets).
Full tests/unit/test_makefile_coverage.py suite (22 tests) passes:
`uv run pytest tests/unit/test_makefile_coverage.py -p no:cacheprovider -q`
-> all green.

Not independently reproduced end-to-end via a live pytest-cov subprocess
run against the OLD (buggy) rc path, matching the ticket's own disclosed
verification method (read the Makefile directly, confirmed by dry-run
expansion) -- a live subprocess-coverage-loss reproduction would need a
real make coverage run first (coordinator-only step per playbook 6b) to
get past coverage-fast's cold-.coverage fallback branch.

### Changed
```
 Makefile                             |  58 ++++++-
 docs/guides/agent-playbook.md        |  55 ++++++
 src/frob/gates/_coverage.py          |  76 +++++++++
 src/frob/tickets/_land_git_ops.py    | 112 ++++++++++++
 tests/test_gates.py                  |  90 ++++++++++
 tests/test_ticket_land.py            |  71 ++++++++
 tests/unit/test_makefile_coverage.py | 105 ++++++++++++
 tickets.md                           | 322 ++++++++++++++++++++++++++++++++++-
 8 files changed, 876 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_never_points_at_pyproject_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_uses_the_shared_absolute_rc` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_rc_file_target_is_shared_not_duplicated` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 3 error(s), 349 warning(s), 694 waived
- error-findings: ARCH001@src/frob/tickets/_land_git_ops.py, PRE001@tickets/T-1397, SELFAUDIT001@design
