## Done report

Changed: src/frob/gates/_docptr.py::_is_historical_ticket_doc (extended to also
match tickets/<id>/evidence/<file>.md and tickets/<id>/attachments/<file>.md,
gated on the same terminal-state (done/dropped) lookup the ticket.md/done-report.md
exemption already used).

Evidence: 7 pytest node ids in tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion
(done-ticket evidence file not flagged, done-ticket attachment not flagged, open-ticket
evidence file still flagged (must-still-fire positive control), done-ticket body not
flagged, dropped-ticket body not flagged, open-ticket body still flagged (must-still-fire
positive control), done-report not flagged even if state lookup fails). All 7 verified
passing directly with `uv run pytest -q tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion`
(SUITE-RESULT: exitstatus=0 collected=7 failed=0) after the ticket's own `frob ticket close`
evidence re-run twice reported a false EvidenceNotPassing/SpawnFailed under ~4x core
oversubscription (load average ~27-48 on a 12-core box, five agents each running gates
concurrently) -- the pytest runner subprocess itself timed out spawning at 900s, which
`ticket close` surfaced as "evidence no longer passes" rather than as unmeasured. Re-ran
`frob ticket evidence` once load dropped below 10 and it passed cleanly on the first try;
close then succeeded.

Filed: none new. Encountered-and-diagnosed (not filed by me; the coordinator is filing the
underlying defect separately): the SpawnFailed-timeout-reported-as-EvidenceNotPassing
behavior in `frob ticket close`'s evidence re-run path is the same NOT_MEASURED-rendered-
as-FAILED confusion class epic T-2391 targets. Do not "fix" tests in response to that
message without confirming the runner itself actually spawned.

Gates: frob check clean via `frob ticket land`'s own pre-land Tier-A pass (1 fix applied,
unrelated to this ticket's scope: REG010/SYS100 skips were files outside T-2534's declared
scope, left untouched). Landed under the worktree's RAPID profile (T-1681, override_ratchet
active): TEST016, the pre-commit sweep, the baseline worktree snapshot, and REL001 preflight
were OFF on this land path (REL001 preflight skip recorded as debt, T-1705/rapid-debt.jsonl).
Ledger integrity and LAND-PROOF verification were NOT relaxed. This land's T-1681
re-verification debt is not yet discharged.
