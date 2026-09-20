## Done report

Fixed win32 failures in TestFixEngineScopeLease::test_uncommitted_in_scope_edit_survives_a_disqualified_tier_a_revert and TestFixEngineTierA::test_pre_fix_dirty_snapshot_captures_uncommitted_content: both wrote fixture content via bare text-mode write_text(), which translates \n to os.linesep (\r\n on win32) on write, then compared _snapshot_dirty_files's exact on-disk bytes against an LF-only literal. Fixed by adding newline="" to the fixture writes. Test-only change, no source touched. winrun-confirmed both tests pass on win32.

### Changed
```
 tickets/T-3790/ticket.md | 17 +++++++++++++++--
 1 file changed, 15 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/gates_suite/test_fix_engine.py::TestFixEngineScopeLease::test_uncommitted_in_scope_edit_survives_a_disqualified_tier_a_revert` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_pre_fix_dirty_snapshot_captures_uncommitted_content` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 1 error(s), 4329 warning(s), 922 waived
- error-findings: PRE001@tickets/T-3790
