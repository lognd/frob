## Done report

## Done report

Changed:
- src/frob/gates/__init__.py::_ticket_marker_in_diff_hunk

Evidence:
- tests/test_gates.py::TestCoverageGate::test_cov002_grace_matches_hunk_anywhere_in_ticket_block
- (regression, unchanged) tests/test_gates.py::TestCoverageGate::test_cov002_done_ticket_covers_own_closing_diff
- (regression, unchanged) tests/test_gates.py::TestCoverageGate::test_cov002_done_ticket_without_grace_still_fires
- (regression, unchanged) tests/test_gates.py::TestCoverageGate::test_cov002_stale_done_ticket_unrelated_tickets_md_touch_still_fires
- (regression, unchanged) tests/test_gates.py::TestCoverageGate::test_cov002_marker_touch_without_state_transition_still_fires

Filed: none

Gates: uv run frob check --delta --ticket T-0564 clean (0/136 new violations); uv run pytest tests/test_gates.py -k cov002 -q: 13 passed

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestCoverageGate::test_cov002_grace_matches_hunk_anywhere_in_ticket_block` (pytest node id, verified passing when recorded)
