## Done report

Moved frob ticket accept --amend/--remove to 1-based indexing, matching frob ticket show's display and --accepts (T-3837). Enumerated every acceptance-index surface (CLI --amend/--remove/--accepts, show's display, amend_acceptance/remove_acceptance's library API, one doc section) -- no other verb was still 0-based; --accepts and the display were already fixed by T-3837, --amend/--remove were the only laggards. Added must-fire fixtures for index 0 and out-of-range on both amend and remove (CLI and library level), a must-stay-quiet fixture proving --amend 1 edits the criterion show prints as [1], and verified F-074 (reason validated before any ticket read) already holds at the CLI layer with a regression fixture that fails if the ticket load is ever reached before the missing-reason refusal.

### Changed
```
 docs/modules/tickets-data-storage.md       |  19 ++-
 src/frob/_cli_parsers/_ticket/_metadata.py |  16 ++-
 src/frob/app/ticket_runner/_mutate.py      |  14 +-
 src/frob/tickets/_accept.py                | 109 +++++++++++-----
 tests/test_tickets_acceptance.py           | 198 ++++++++++++++++++++++++++---
 tickets/T-3908/ticket.md                   |  68 +++++++++-
 6 files changed, 362 insertions(+), 62 deletions(-)
```

### Evidence
- `tests/test_tickets_acceptance.py::TestAmendAcceptance::test_amend_refuses_zero_index_not_the_first_criterion` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAmendAcceptance::test_remove_refuses_zero_index_does_not_drop_the_first_criterion` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove::test_cli_amend_zero_index_is_rejected_not_the_first_criterion` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove::test_cli_remove_zero_index_is_rejected_not_the_first_criterion` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove::test_cli_amend_one_edits_the_criterion_show_prints_as_one` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove::test_cli_amend_missing_reason_refused_before_ticket_is_read` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove::test_cli_remove_missing_reason_refused_before_ticket_is_read` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAmendAcceptance::test_amend_replaces_text_and_records_reason` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAmendAcceptance::test_remove_drops_criterion_and_records_reason` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 7 error(s), 4515 warning(s), 947 waived
- error-findings: AFFECT001@src/frob/tickets/_accept.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@src/frob/process/_project_tool.py, COV001@src/frob/vet/_bare_toolchain.py, DRIFT002@src/frob/check/_python.py, FMT001@tests/test_tickets_acceptance.py, SCOPE002@tickets.md
