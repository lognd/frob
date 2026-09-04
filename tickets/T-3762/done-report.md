## Done report

Fixed did-you-mean regex to accept Python 3.12's unquoted invalid-choice message format. Evidence: tests/unit/test_main_entry.py::TestDidYouMean::test_unknown_subcommand_suggests_closest, test_unknown_ticket_subcommand_suggests_closest. Confirmed via winrun on the Windows mirror (Python 3.12.10): all 6 TestDidYouMean tests pass. Filed: none. Gates: frob check --ticket T-3762 clean (only remaining error is gate:COV:COV003 on unrelated pre-existing ticket T-3757).

### Changed
```
 src/frob/_cli_parsers/_root.py | 14 +++++++++++++-
 tickets/T-3762/ticket.md       |  3 +++
 2 files changed, 16 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_main_entry.py::TestDidYouMean::test_unknown_subcommand_suggests_closest` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestDidYouMean::test_unknown_ticket_subcommand_suggests_closest` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 1 error(s), 4333 warning(s), 921 waived
- error-findings: COV003@tests/test_ci_workflow_matrix.py
