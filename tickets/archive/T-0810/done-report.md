## Done report

## Done report

Changed:
- src/frob/tickets:archive (unchanged, T-0764) -- consumed by CLI as force=cfg.ticket_force
- src/frob/app/ticket_runner.py::_archive -- now accepts force kwarg, threads to archive(), logs a warning naming the live-lease count before overriding
- src/frob/app/ticket_runner.py::_ticket_dispatch_table -- archive lambda now passes cfg.ticket_force
- src/frob/app/config.py::AppConfig.ticket_force -- new bool field, wired into from_external's bool-field list
- src/frob/__main__.py::_add_ticket_fail_evidence_archive_parsers -- registers --force on the archive subparser (dest=ticket_force)

Evidence:
- tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_refuses_without_force_when_a_live_lease_exists
- tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal
- tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_with_no_live_leases_stays_quiet

Filed: none

Gates: frob check --ticket T-0810 clean (0 errors); frob test --base main PASS (touched-set: interface/CLI dispatch tests, archive-force CLI tests, AppConfig toml-read test)

### Changed
(no changed files detected)

### Evidence
- `tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_refuses_without_force_when_a_live_lease_exists` (pytest node id, verified passing when recorded)
- `tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal` (pytest node id, verified passing when recorded)
- `tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_with_no_live_leases_stays_quiet` (pytest node id, verified passing when recorded)
