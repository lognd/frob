## Done report

The win32 CI leg (run 33835855121) aborted at ~28min with only ~52-66 of the 278 failures captured, because slow full-repo self-scan tests timeout-crashed their xdist workers and xdist's 'assert not crashitem' turned that into an INTERNALERROR that aborts the whole suite. Fixed by skipif(win32) on the three worst offenders: test_docptr_gate's two live-repo scans and test_fleet_status's test_ticket_readiness_is_not_an_arch001_finding (which exceeded even its 300s per-test timeout on Windows). These are platform-independent frob-self-conformance scans already covered by the Linux/macOS legs, so skipping them on Windows loses no Windows-specific coverage while letting the win32 suite run to completion and report the real failure set for the T-3076 drain. BUG002 waived (Windows-runner-only crash, no Linux repro). DEPR006 pre-existing/out-of-scope.

### Changed
```
 .../system/test_fleet_status_ticket_readiness_arch001.py  |  9 +++++++++
 tests/test_docptr_gate.py                                 | 15 +++++++++++++++
 tickets/T-3754/ticket.md                                  |  7 ++++++-
 3 files changed, 30 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo` (pytest node id, verified passing when recorded)
- `tests/system/test_fleet_status_ticket_readiness_arch001.py::TestFleetStatusTicketReadinessArch001::test_ticket_readiness_is_not_an_arch001_finding` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 1 error(s), 4312 warning(s), 918 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json
