## Done report

Changed:
tests/system/test_cli_doctor.py::_write_fake_posix_tool
tests/system/test_cli_doctor.py::_fake_required_toolchain_path
tests/system/test_cli_doctor.py::_env_with_fake_required_toolchain
tests/system/test_cli_doctor.py::_stable_external_tools
tests/test_doctor.py::_stable_external_tools

Evidence:
tests/test_doctor.py::test_run_diagnosis_natives_present
tests/test_doctor.py::test_run_diagnosis_natives_absent
tests/test_doctor.py::test_run_diagnosis_partial_availability
(tests/system/test_cli_doctor.py's 44 tests bound via existing frob:tests directives from the prior commit on this branch)

Filed: T-4371 (WIRE001 false positive on two-hop test-helper call chains, found while working T-4365; scoped to src/frob/gates/_wire.py)

Gates: frob check --ticket T-4365 clean (0 errors); TICK010 stale lease for
unrelated ticket T-4346 and PRE001/pre-work-sweep both cleared by
frob ticket sweep T-4365. --designate-repro-force used on
tests/test_doctor.py::test_run_diagnosis_natives_present: the bug is
environment-dependent (ambient ruff/ty on PATH), so --check-repro's
automatic run in this dev sandbox (which has ruff/ty installed) reads
PASSED_AT_PARENT; manually verified FAILED_AT_PARENT by running the
touched test files with a PATH excluding .local/bin (so ruff/ty absent),
reproducing the macOS CI condition -- 14/14 (test_doctor.py) and
44/44 (test_cli_doctor.py) pass post-fix under that same PATH.

### Changed
```
 tests/system/test_cli_doctor.py    | 116 +++++++++++++++++++++++++++++++++++--
 tests/test_doctor.py               |  43 ++++++++++++++
 tickets/T-4365/ticket.md           |  22 ++++++-
 tickets/T-4371/ticket.md |  41 +++++++++++++
 4 files changed, 217 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_doctor.py::test_run_diagnosis_natives_present` (pytest node id, verified passing when recorded)
- `tests/test_doctor.py::test_run_diagnosis_natives_absent` (pytest node id, verified passing when recorded)
- `tests/test_doctor.py::test_run_diagnosis_partial_availability` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 4767 warning(s), 960 waived
- error-findings: none (measured, zero errors)
