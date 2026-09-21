## Done report

-- T-3986

### Changed
```
 src/frob/policy/__init__.py        |   84 +-
 tests/test_policy.py               |  194 +++
 tickets/T-3986/done-report.md      | 2279 ++++++++++++++++++++++++++++++++++++
 tickets/T-3986/ticket.md           |   32 +-
 tickets/T-4030/done-report.md      | 2265 +++++++++++++++++++++++++++++++++++
 tickets/T-4030/ticket.md           |   24 +-
 tickets/T-draft-58a07e89/ticket.md |   42 +
 7 files changed, 4875 insertions(+), 45 deletions(-)
```

### Evidence
- `tests/test_policy.py::TestPol000::test_pol000_stays_quiet_on_real_match` (pytest node id, verified passing when recorded)
- `tests/test_policy.py::TestPol000::test_pol000_stays_quiet_when_underscore_capture_only_matches` (pytest node id, verified passing when recorded)
- `tests/test_policy.py::TestPol000::test_pol000_stays_quiet_for_warn_severity` (pytest node id, verified passing when recorded)
- `tests/test_policy.py::TestPol000::test_pol000_fires_on_zero_match_pattern` (pytest node id, verified passing when recorded)
