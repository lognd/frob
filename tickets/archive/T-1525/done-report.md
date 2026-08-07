## Done report

Added `frob coverage` (`src/frob/app/coverage_runner.py`): the missing CLI
entrypoint over `frob.testing._coverage_refresh.native_coverage_refresh`
(T-1516) and `frob.testing._coverage_wait.run_coverage_wait`. Default (no
flag) delegates to `run_coverage_wait(root)`, reusing its existing
single-flight lock and freshness check. `--full` bypasses both and calls
`native_coverage_refresh(root, snapshot, full=True)` directly (an
explicit whole-suite request should not be short-circuited by another
worktree's already-fresh cached result). Wired through the same path
every other verb here uses: `Subcommand.coverage` (src/frob/app/config.py),
`coverage_full`/`coverage_path` fields whitelisted in
src/frob/app/_config_external.py, `_add_coverage_parser`
(src/frob/_cli_parsers/_misc.py, re-exported via
src/frob/_cli_parsers/__init__.py), dispatch-table entry plus the closed
if/elif import chain in src/frob/app/app.py, and the parser registered in
src/frob/__main__.py.

Decision (this ticket's other half): `frob check` does NOT auto-trigger a
coverage refresh, for any caller -- agent or non-agent/human/CI. T-1516's
Done report already ruled this out for a dispatched worktree agent
(FROB_AGENT=1, agent-playbook.md section 3b's foreground-timeout
contract); this ticket had to decide the non-agent half and the answer is
still no, on different grounds: running the test suite is a categorically
slower, more failure-prone operation than every other gate `frob check`
runs, and hiding it as an implicit side effect of a "tell me what's
wrong, fast" command would surprise every caller. Documented in
docs/modules/cli.md's new "frob coverage (T-1525)" section. `frob check`
keeps reporting staleness via TEST011/TEST017 rather than fixing it;
`frob coverage` (this verb) and `frob test --wait-coverage`
(test_runner.py's existing wired call into run_coverage_wait, T-1516)
are the two explicit places a refresh is expected to run from.

Scope was widened beyond the ticket's original single-file declaration
(src/frob/__main__.py) to cover the actual CLI-verb convention this repo
follows (Subcommand enum + config fields + parser + runner + dispatch
wiring, the natives_runner/T-0864 precedent) -- added via
`frob ticket scope --add --reason`, each add logged: src/frob/_cli_parsers/
_misc.py, src/frob/_cli_parsers/__init__.py, src/frob/app/app.py,
src/frob/app/config.py, src/frob/app/_config_external.py, src/frob/app/
coverage_runner.py, docs/modules/cli.md, README.md, tests/unit/
test_main_entry.py, tests/test_app_config.py, tests/unit/
test_coverage_runner.py.

Gate findings addressed as part of this ticket's own diff: DOC005 (README
command-table row + count, fixed), INV006 (coverage_runner.py's docstring
used "exclusively"/"only" as unenforced normative claims, reworded),
PRE001 (stale pre-work sweep, re-ran `frob ticket sweep T-1525`), WIRE001
(tests/unit/test_coverage_runner.py's module-level `_cfg` helper read as
an unwired new symbol; converted to a bound `TestCoverageRunner._cfg`
method, matching the existing `TestNativesRunner._cfg` precedent in
tests/unit/test_natives_build.py).

One finding disclosed, not fixed: SELFAUDIT001 (self-audit family SYS104)
flags `_add_coverage_parser` (cli node) and `TestCoverageRunner`
(testsuite node) as public symbols missing an `interface=` declaration in
design/frob.strata. That file is leased by in-progress T-1220
(`ScopeLeaseConflict` on `frob ticket scope T-1525 --add
design/frob.strata`) -- per this dispatch's hard rule, the scope add was
skipped rather than forced, and this edge is left for whichever ticket
next holds design/frob.strata's lease (T-1220 itself, or a follow-up
after it lands).

gate:DUP001 (src/frob/app/app.py::_import_runner_module vs
src/frob/app/__init__.py::_import_runner_run_module, 95% similar) is
PRE-EXISTING on main (verified via `git show main:src/frob/app/app.py` --
the duplicate pair already existed before this ticket's 2-line addition
to the same if/elif chain) -- not this ticket's to fix, out of scope.

Targeted tests: `tests/unit/test_coverage_runner.py`,
`tests/unit/test_main_entry.py`, `tests/test_app_config.py` -- 29 passed.
`frob check --ticket T-1525` (foreground, 540s wrapper): no ERROR-level
finding traces to a file this ticket touched except the disclosed
SELFAUDIT001 pair above.

### Changed
```
 tickets.md | 94 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 92 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_coverage_runner.py::TestCoverageRunner::test_default_delegates_to_run_coverage_wait` (pytest node id, verified passing when recorded)
- `tests/unit/test_coverage_runner.py::TestCoverageRunner::test_full_calls_native_refresh_directly` (pytest node id, verified passing when recorded)
- `tests/unit/test_coverage_runner.py::TestCoverageRunner::test_run_failure_exits_nonzero` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 341 warning(s), 782 waived
- error-findings: none (measured, zero errors)
