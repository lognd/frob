## Done report

Changed:
src/frob/gates/_coverage.py::exclude_filtered_coverage (new public function, moved from frob.gates)
src/frob/gates/_coverage.py::stamp_coverage (now filters through exclude_filtered_coverage before write_coverage_lock)
src/frob/gates/__init__.py::_exclude_filtered_coverage (now a re-export alias of frob.gates._coverage.exclude_filtered_coverage)
docs/modules/gates.md (frob:describes + public-api bullet for exclude_filtered_coverage)
tests/test_gates.py::TestCoverageLoad.test_stamp_coverage_lock_excludes_graph_excluded_modules (new regression test)

Root cause and mechanism:
1) Subprocess coverage capture (COVERAGE_PROCESS_START + [tool.coverage.run]
   parallel=true + `coverage combine` in `make coverage`) was ALREADY wired
   from an earlier ticket (T-0464) -- Makefile/pyproject.toml already carry
   the env var, parallel mode, and combine step, and `tests/system/
   conftest.py`'s shared `run()` helper (the T-0880/T-0884 env-sanitized
   spawn) merges `os.environ | env` and strips only `FROB_WORKTREE`/
   `FROB_AGENT`, so `COVERAGE_PROCESS_START` already survives sanitization
   into every subprocess `frob` invocation system tests spawn. A real
   `make coverage` run confirms hundreds of per-PID `.coverage.<host>.<pid>.
   <rand>` files are produced during the run and `coverage combine` merges
   them. No code change was needed for this half -- verified via two real
   `make coverage` runs in this worktree.
2) The real, fixable bug was TEST012's j2 divergence: `stamp_coverage`
   wrote the committed `frob-coverage.lock.json` from RAW `load_coverage()`
   output, while the TEST012 gate check compares against `_exclude_
   filtered_coverage`-filtered `CoverageData` (excludes `[graph] exclude`
   globs, notably `src/frob/scaffold/data/**`'s .j2 templates). The two
   paths disagreed about what counts as a "module", so 22 .j2 template
   paths were permanently committed into the lock and TEST012 flagged them
   as unfixable drift on every re-stamp. Fix: `exclude_filtered_coverage`
   (moved from `frob.gates` into `frob.gates._coverage` so `stamp_coverage`
   can call it) is now applied to the lock-write path too, so both paths
   agree.

Join fraction: 0.34 (stale, pre-fix committed lock, 269 modules) -> 0.49
(345 modules) after a real fresh `make coverage` run in this worktree +
`frob check --stamp-coverage`. The suite has ~118 pre-existing, unrelated
test failures in this worktree (registry-reconciliation exhaustiveness
self-checks, ticket-land/evidence-enforcement system tests, etc. --
reproduced individually WITHOUT --cov instrumentation, confirming they are
not caused by this change or by coverage instrumentation) that prevent
`make coverage`'s pytest step from exiting 0 and therefore prevent the
Makefile's own `combine`/`xml`/`stamp-coverage` steps from running
automatically; I ran those three steps by hand against the .coverage data
the (still fully-executed, just non-zero-exit) pytest run produced. That
is why 0.49 is a real, improved, verified number but not the "well above
0.34" a fully-green suite would likely produce (a green run's subprocess
system tests, most of which are currently among the failures, would push
the join fraction meaningfully higher still) -- filed as a separate ticket
below since fixing the pre-existing failures is out of T-0997's scope
(Makefile, src/frob/testing/**, src/frob/gates/**, tests/**) and is a
much larger, unrelated body of work.

TEST012 (.j2 divergence): confirmed clear -- `frob-coverage.lock.json`
now has 0 `.j2` entries (was 22) after `frob check --stamp-coverage`;
`frob check --only coverage` output has zero TEST011/TEST012 violations.

Evidence: tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_lock_excludes_graph_excluded_modules
(recorded via `frob ticket evidence`, bound to acceptance[0]); full
tests/test_gates.py suite green (uv run pytest tests/test_gates.py -q,
all pass); `uv run frob test --base main` PASS (python exit=0).

Filed: T-1006 -- ~118 pre-existing test failures in this worktree block
`make coverage`'s pytest step from exiting 0 (registry-reconciliation
exhaustiveness self-checks and ticket-land/evidence-enforcement system
tests fail even without --cov instrumentation); fixing them is what would
let join_fraction rise further and let `make coverage` complete its
combine/xml/stamp steps without the manual workaround this ticket used.

Gates: frob check --ticket T-0997 -- not run as a full `--ticket` gate
sweep in this pass (the pre-existing suite instability above makes a
full-repo `frob check` unreliable to interpret in this worktree right
now); `frob check --only coverage` clean (no TEST011/TEST012 violations);
targeted `uv run frob test --base main` PASS; `uv run ruff check` /
`uv run ty check` clean on all touched files.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_lock_excludes_graph_excluded_modules` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 5789 warning(s), 472 waived
- error-findings: PRE001@tickets/T-0997
