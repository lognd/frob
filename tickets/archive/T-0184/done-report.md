## Done report

Changed:
tests/system/test_cli_ticket.py::TestTicketRoundTrip.test_close_without_evidence_fails
(hardened: asserts MissingEvidence in output AND ledger stays in-progress)
tests/system/test_cli_ticket.py::TestTicketRoundTrip.test_close_with_evidence_and_done_report_succeeds
(new: success path exits 0 and ledger transitions to done)

NON-REPRODUCTION, verified three ways: every close-failure path (no
evidence, inline --evidence, evidence-without-done-report; via editable
source AND the installed uv-tool binary) logs the error AND exits 1; the
is_err -> sys.exit(1) guard in _close has existed since introducing commit
31699b3 and every historical revision of the file; audit of
ticket_runner.py, sys_runner.py, check_runner.py found no live
print-error-exit-0 pattern. Reviewer independently traced the original
T-0154 incident to a MANUAL ledger-splice commit (3dafd41), not a CLI
close -- the observed exit-0 was shell masking, not a frob defect.

Filed: none.
Gates: frob check --ticket clean except campaign-wide TEST006 stamp
staleness; frob test --base main PASS.
Review: APPROVED (non-repro + regression hardening accepted).
