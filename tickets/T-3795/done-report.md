## Done report

Changed: tests/test_coverage.py::TestWorkerCrashSignatureRealSubprocess.test_sigkill_worker_crash_is_a_real_repro
Evidence: winrun-confirmed skip on win32; passes on Linux (tests/test_coverage.py::TestWorkerCrashSignatureRealSubprocess::test_sigkill_worker_crash_is_a_real_repro)
Filed: none
Gates: frob check --ticket T-3795 clean

### Changed
```
 tests/test_coverage.py        |  4 ++++
 tickets/T-3795/done-report.md | 20 ++++++++++++++++++++
 2 files changed, 24 insertions(+)
```

### Evidence
- `tests/test_coverage.py::TestWorkerCrashSignatureRealSubprocess::test_sigkill_worker_crash_is_a_real_repro` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 4351 warning(s), 922 waived
- error-findings: none (measured, zero errors)
