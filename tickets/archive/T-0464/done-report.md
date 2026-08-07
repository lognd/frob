## Done report

Part 1 (the root-cause fix): the `coverage` Makefile target now sets
COVERAGE_PROCESS_START=pyproject.toml, clears stale .coverage*, and runs
`coverage combine` + `coverage xml` -- so subprocess system tests
(tests/system spawns `python -m frob`) are actually measured instead of
reading as 0% hit. pyproject.toml gains [tool.coverage.run] (branch/parallel/
relative_files/source) + [tool.coverage.paths]. This stops `make coverage`
producing the deflated 0.49 coverage.xml that exploded TEST005 to 507 false
findings (the .pth subprocess hook already exists in the venv). Verified by
inspection + a direct COVERAGE_PROCESS_START run (not a full 20-min make
coverage, per coordinator).

Part 2 (freshness/staleness hardening): CoverageData gains stale_by_mtime +
module_join_fraction; load_coverage computes them (_newest_source_mtime,
_module_join_fraction); new TEST011 advisory (Severity.WARN,
_test011_freshness, folded into _test005) fires when coverage.xml predates
tracked source OR when its lines no longer join to symbol spans (<0.5) -- so
a stale/deflated coverage.xml is FLAGGED instead of silently producing false
TEST005 findings (the blind spot: source_sha was the xml's own sha, not the
measured source).

Evidence (3 of 6 tests): test011 fires-on-stale-mtime, silent-when-fresh,
and load_coverage flags-stale-by-mtime. Coordinator resumed the stalled
agent to finish part 2 (it block-and-stalled on a make coverage run, T-0322),
inline-reviewed, landed via 3-way (all tracked). Fixes the coverage-stamp
struggles that recurred all session.
