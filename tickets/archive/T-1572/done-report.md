## Done report

Added `frob coverage --base REF` (T-1572), the touched-set incremental
refresh's diff-base override -- the old `make coverage-fast BASE=<ref>`
shell recipe's equivalent, previously hardcoded to HEAD with no CLI knob.

Real work required beyond the originally-scoped files (disclosed, not
silently expanded): the failed prior attempt's ticket text described this
as "small and mechanical once the flag exists," but tracing the default
(non `--full`) path found `run_coverage_wait` (src/frob/testing/
_coverage_wait.py) never threaded a base ref through to
`native_coverage_refresh` at all -- `native_coverage_refresh`'s own
`base` kwarg only affects touched-set SELECTION, which `--full` bypasses
entirely by running the whole suite regardless, so `--base`'s only real
effect is on the default path, and that path's plumbing did not exist
yet. Added `base: str = "HEAD"` through the full call chain:
`run_coverage_wait` -> `_run_and_settle_shared` -> `_run_native_refresh`
-> `native_coverage_refresh(..., base=base)`. Extended scope to include
this file plus its own test files (`tests/test_coverage.py`,
`tests/test_coverage_wait_shared.py`) rather than leave the flag a
silent no-op for its only real use case.

CLI wiring: `--base` on `_add_coverage_parser` (_misc.py) ->
`AppConfig.coverage_base: str | None = None` (config.py) -> wired into
`_config_external.py`'s `_STRING_FIELDS` -> `coverage_runner.run` passes
`base=cfg.coverage_base or "HEAD"` to `run_coverage_wait`.

Docs: docs/modules/cli.md's `frob coverage` section and docs/modules/
testing.md's `run_coverage_wait` public-API entry both gained the new
kwarg/flag (AFFECT001 on both `coverage_runner.run` and
`run_coverage_wait`'s own affects()-closure docs).

Pre-existing, out-of-scope findings disclosed rather than fixed or
silently left unmentioned: a full unscoped `frob check --land-parity`
shows ARCH001 x2/ARCH103 in src/frob/app/ticket_runner/_query.py and
src/frob/tickets/_doable.py (same T-1738/T-1828 findings disclosed while
landing T-1570/T-1571 earlier in this series) plus COV001/E501/TEST001 in
src/frob/registry/_staleness.py -- confirmed via `git log` to predate
this ticket (T-1264's own land, 34da12ee8). None of these three files are
in T-1572's scope or touched by its diff.

Verification: `uv run frob check --only gates-fast --ticket T-1572` and
`--only gates-native --only gates-security --ticket T-1572` both clean
except the pre-existing findings named above (0 new COV002/SCOPE/AFFECT
errors); `pytest tests/unit/test_coverage_runner.py tests/test_coverage.py
tests/test_coverage_wait_shared.py` 53 passed.

### Changed
```
 tickets/T-1572/ticket.md | 95 +++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 94 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_coverage_runner.py::TestCoverageRunner::test_default_delegates_to_run_coverage_wait` (pytest node id, verified passing when recorded)
- `tests/unit/test_coverage_runner.py::TestCoverageRunner::test_base_threads_through_to_run_coverage_wait` (pytest node id, verified passing when recorded)
- `tests/unit/test_coverage_runner.py::TestCoverageRunner::test_full_calls_native_refresh_directly` (pytest node id, verified passing when recorded)
- `tests/unit/test_coverage_runner.py::TestCoverageRunner::test_run_failure_exits_nonzero` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 7 error(s), 881 warning(s), 740 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/tickets/_doable.py, ARCH103@src/frob/app/ticket_runner/_query.py, COV001@src/frob/registry/_staleness.py, COV001@src/frob/tickets/_doable.py, E501@/home/logan/projects/frob/.claude/worktrees/cli-regroup/src/frob/registry/_staleness.py, TEST001@src/frob/registry/_staleness.py
