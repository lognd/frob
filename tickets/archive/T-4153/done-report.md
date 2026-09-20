## Done report

Added _is_ticket_ledger_v2_artifact to src/frob/gates/_refs.py, exempting frob's own tickets/T-*/ticket.md and tickets/T-*/done-report.md (plus tickets/archive/T-*/ counterparts) from REF001/REF002, matching frob.tickets._store's _V2_TICKET_GLOB shape and following T-3249/T-3444/T-4145 precedent. Deliberately narrow: only the two fixed filenames frob itself writes are exempt, not the whole tickets/ directory -- proven by a fixture (test_unrelated_file_in_ticket_dir_still_fires_ref001) where an unrelated file in a ticket dir still fires REF001. 4 new tests added to tests/test_refs_gate.py, all passing.

### Changed
```
 src/frob/gates/_refs.py  | 50 ++++++++++++++++++++++++++
 tests/test_refs_gate.py  | 91 ++++++++++++++++++++++++++++++++++++++++++++++++
 tickets/T-4153/ticket.md | 32 ++++++++++++++++-
 3 files changed, 172 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_refs_gate.py::TestTicketLedgerV2Exempt::test_ticket_md_is_exempt_with_no_declaration` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestTicketLedgerV2Exempt::test_done_report_md_is_exempt_with_no_declaration` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestTicketLedgerV2Exempt::test_archived_ticket_md_is_exempt_with_no_declaration` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestTicketLedgerV2Exempt::test_unrelated_file_in_ticket_dir_still_fires_ref001` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 7 error(s), 4514 warning(s), 934 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@src/frob/process/_project_tool.py, COV001@src/frob/vet/_bare_toolchain.py, DOC006@tickets/T-4144/ticket.md, DOC006@tickets/T-4155/ticket.md, DRIFT002@src/frob/check/_python.py, SCOPE002@tickets.md
