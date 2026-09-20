## Done report

src/frob/perf/_rules.py (T-4088) and tests/system/test_cli_doctor.py (T-4365) were left unformatted by their own lands because both landed under the rapid profile (T-1575/T-1681, override_ratchet=true), which skips the T-1514 pre-commit sweep entirely -- src/frob/tickets/_land.py documents this explicitly: a supplied pre_commit_sweep is wired only when the land profile does NOT set override_ratchet, i.e. every profile except rapid. That sweep is the step that would normally run a full-tree frob format pass before commit; rapid profile lands (as ours in this same series were) skip it by design and rely only on Tier-A gate fixes, which do not include general ruff-format/frob-format drift. Fixed here with a plain uv run frob format pass; filed T-4381 as a follow-up for the mechanism itself (rapid profile lands never format-check their own touched files).

### Changed
```
 src/frob/perf/_rules.py         |  4 +---
 tests/system/test_cli_doctor.py |  3 +--
 tickets/T-4380/ticket.md        | 16 +++++++++++++++-
 3 files changed, 17 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/test_perf.py::TestPerf007RedundantComputation::test_two_stages_calling_the_same_uncached_parse_is_flagged` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorCli::test_doctor_reports_healthy_when_natives_present` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 4780 warning(s), 957 waived
- error-findings: none (measured, zero errors)
