## Done report

Investigation close: verified (not assumed) that T-1412 already
resolved this -- doc006_gate run directly against CHANGELOG.md yields 0
findings via the landed _ARCHIVAL_LEDGER_FILES exclusion, and its
regression tests pass. No code change needed; the in-worktree path to
zero exists today.

### Changed
```
 tickets.md | 69 ++++++++++++++++----------------------------------------------
 1 file changed, 18 insertions(+), 51 deletions(-)
```

### Evidence
- `tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing::test_changelog_is_an_archival_record_not_checked` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing::test_live_doc_still_flagged_after_changelog_exclusion` (pytest node id, verified passing when recorded)
- `cmd:bash -c "grep -q _ARCHIVAL_LEDGER_FILES src/frob/gates/_doclink_docanchor.py || grep -rq _ARCHIVAL_LEDGER_FILES src/frob/gates/" exit=0 sha256=e3b0c44298fc` (cmd evidence, exit=0)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 293 warning(s), 741 waived
- error-findings: none (measured, zero errors)
