## Done report

Added three file-input flags mirroring the done-report --why-file precedent
(T-0458), so long/backticked ticket prose never rides the shell:
`frob ticket new --body-file PATH` (mutually exclusive with --body),
`frob ticket new --acceptance-file PATH` (mutually exclusive with
--acceptance; blank-line-separated blocks, or one criterion per line if
the file has no blank line), and `frob ticket scope --reason-file PATH`
(mutually exclusive with --reason; one of --reason/--reason-file is
required). Implemented via `_resolve_new_body`/`_resolve_new_acceptance`/
`_parse_acceptance_file`/`_resolve_scope_reason` in ticket_runner.py, new
AppConfig fields (ticket_body_file, ticket_acceptance_file,
ticket_scope_reason_file), and matching argparse flags in __main__.py.
Verified byte-exact round trip for a body/reason containing backticks,
quotes, and dollar signs, plus clean mutual-exclusion errors, in
tests/unit/test_ticket_file_flags.py (9 tests, all passing). Documented
both flags in docs/modules/tickets.md and added a new agent-playbook
section (1d) routing multi-sentence ticket prose through these flags.

### Changed
```
 docs/guides/agent-playbook.md        |  26 +++++
 docs/modules/tickets.md              |  41 ++++++-
 src/frob/__main__.py                 |  27 ++++-
 src/frob/app/config.py               |  20 ++++
 src/frob/app/ticket_runner.py        | 109 +++++++++++++++--
 tests/unit/test_ticket_file_flags.py | 220 +++++++++++++++++++++++++++++++++++
 tickets.md                           |  11 +-
 7 files changed, 441 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_file_flags.py::TestNewBodyFile::test_body_file_round_trips_byte_exact` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_file_flags.py::TestNewBodyFile::test_body_and_body_file_together_errors_cleanly` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_file_flags.py::TestNewBodyFile::test_unreadable_body_file_errors_cleanly` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_file_flags.py::TestNewAcceptanceFile::test_blank_line_separated_blocks_become_criteria` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_file_flags.py::TestNewAcceptanceFile::test_one_per_line_when_no_blank_lines` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_file_flags.py::TestNewAcceptanceFile::test_acceptance_and_acceptance_file_together_errors_cleanly` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_file_flags.py::TestScopeReasonFile::test_reason_file_round_trips_byte_exact` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_file_flags.py::TestScopeReasonFile::test_reason_and_reason_file_together_errors_cleanly` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_file_flags.py::TestScopeReasonFile::test_neither_reason_nor_reason_file_errors_cleanly` (pytest node id, verified passing when recorded)
