## Done report

Ticket.model_copy now normalizes scope back to a tuple, closing the pydantic serializer warning path model_copy's validator-bypass left open; the 3 macOS-failing node ids pass clean under -W error::UserWarning; docs/modules/tickets-data-storage.md documents the normalization; scope extended to include that doc file per T-4453's own acceptance criterion 3

### Changed
```
 docs/modules/tickets-data-storage.md |  9 +++++++++
 src/frob/tickets/_models.py          | 32 ++++++++++++++++++++++++++++++++
 tickets/T-4453/ticket.md             | 24 ++++++++++++++++++++++++
 3 files changed, 65 insertions(+)
```

### Evidence
- `tests/unit/test_new_ticket_scope_overlap_warning.py::TestNonRelativeScopeDoesNotCrash::test_corrupt_row_is_named_loudly_not_silently_coerced` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_scope_overlap_warning.py::TestNonRelativeScopeDoesNotCrash::test_unrelated_ticket_still_files_despite_one_corrupt_row` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_scope_overlap_warning.py::TestNonRelativeScopeDoesNotCrash::test_multiple_corrupt_entries_use_plural_wording` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 1 error(s), 4847 warning(s), 965 waived
- error-findings: TICK004@tickets.md
