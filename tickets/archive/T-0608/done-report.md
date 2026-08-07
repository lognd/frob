## Done report

Threads cfg.check_skip_gates/check_ticket/check_base/check_delta through
_dispatch_check_cpp/_dispatch_check_rust/_dispatch_check_ts in
src/frob/app/check_runner.py to the run_check_cpp/rust/ts kwargs T-0554
added on the receiving side -- previously only _dispatch_check_python
passed them, so CLI-level --ticket/--base/--delta/--skip-gates scoping
was silently ignored for non-Python repos (gates ran unconditionally).

Six new tests in tests/unit/test_check.py
(TestDispatchCheckThreadsGateSelectors): per dispatcher, one asserting
non-default selector values arrive at the pipeline call and one pinning
the defaults when flags are omitted. Adversarially verified: all six
FAIL against the pre-fix check_runner.py (KeyError on the absent kwarg)
and pass after the fix; the reviewer independently reproduced this by
reverting the file mid-review. Reviewer verdict: APPROVE.

No scope widening needed; no public API change (dispatchers are
private); docs untouched by design (behavior now matches what
docs/modules already describe for check CLI selectors).

### Changed
```
 src/frob/app/check_runner.py |  33 ++++++++-
 tests/unit/test_check.py     | 160 +++++++++++++++++++++++++++++++++++++++++++
 tickets.md                   |  59 +++++++++++++++-
 3 files changed, 247 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_cpp_dispatch_threads_selectors` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_cpp_dispatch_default_selectors_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_rust_dispatch_threads_selectors` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_rust_dispatch_default_selectors_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_ts_dispatch_threads_selectors` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_ts_dispatch_default_selectors_unchanged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 1210 warning(s), 210 waived
