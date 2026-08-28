## Done report

Changed:
  src/frob/app/ticket_runner/_verify.py::_run_pytest_directly
  src/frob/testing/_collect.py::collect_python_tests
  src/frob/testing/_coverage_refresh.py::native_coverage_refresh
  src/frob/app/mutate_runner.py::run
  src/frob/app/perf_runner.py::_profile
  docs/guides/agent-playbook.md (new section 1e)

Evidence:
  tests/unit/test_pytest_spawn_env_wiring.py (6 must-fire/must-stay-quiet cases,
  one per call site)
  Live /proc/<pid>/environ verification: a real pytest worker spawned through
  _run_pytest_directly under a live fleet lease carried
  PYTEST_XDIST_AUTO_NUM_WORKERS=3 in its own environment.
  Live warn_if_xdist_bound_missing firing verified: stripping the bound from
  os.environ under a live fleet context produced the expected ERROR log line.

Filed: none

Gates: touched-set `frob test --base main` clean (31 python tests, exit=0).
`frob check --ticket T-3099` reports gate:SCOPE SCOPE002 findings, but every
one names a symbol this ticket's diff did NOT touch (e.g.
_budget_deferred_groups_from_stdout, _validate_designate_repro_at_parent,
_missing_natives) -- a structural consequence of the ticket's declared
scope being whole files with many pre-existing frob:doc/frob:tests targets
outside that file list, not a regression introduced by this change. Not
waived (out of scope to fix the doc/scope structure of unrelated symbols in
these large files); noting explicitly rather than silently passing over it.

### Changed
```
 docs/guides/agent-playbook.md              |  30 ++++
 src/frob/app/mutate_runner.py              |  10 ++
 src/frob/app/perf_runner.py                |  10 ++
 src/frob/app/ticket_runner/_verify.py      |  10 ++
 src/frob/testing/_collect.py               |  10 ++
 src/frob/testing/_coverage_refresh.py      |  10 ++
 tests/unit/test_pytest_spawn_env_wiring.py | 266 +++++++++++++++++++++++++++++
 tickets/T-3099/ticket.md                   |   2 +-
 8 files changed, 347 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
