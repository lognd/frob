## Done report

`_documented_srcs` in src/frob/gates/__init__.py was genuinely orphaned:
grep across src/ and tests/ showed zero call sites, only docstring/comment
mentions referring to its superseding replacement `_resolved_documented_srcs`
(T-0233). Deleted it outright.

`_run_jobs` (and its helper `_timed_job`) were NOT dead -- they are imported
and exercised directly by
tests/test_gates.py::TestRunJobsTimingAttribution::test_cpu_bound_neighbor_does_not_inflate_a_cheap_jobs_timing.
The DEAD001 false positive was exactly the misplacement pattern the ticket
called out: the `frob:tests` directives sat above the TEST function in the
test file instead of above the SOURCE symbols in gates/__init__.py, so the
comment DSL never bound the edge. Moved both `frob:tests` directives to sit
directly above `_timed_job` and `_run_jobs` in gates/__init__.py and removed
the ineffective copies from the test file.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestRunJobsTimingAttribution::test_cpu_bound_neighbor_does_not_inflate_a_cheap_jobs_timing` (pytest node id, verified passing when recorded)
