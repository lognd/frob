---
id: T-2534
title: T-2505's historical-ticket-doc exemption should cover evidence/attachments
  dirs too
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_docptr.py
- tests/test_docptr_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_docptr_gate.py
  reason: regression tests for the T-2534 evidence/attachments historical-doc exemption
    fix
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion::test_done_ticket_evidence_file_not_flagged
- tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion::test_done_ticket_attachment_not_flagged
- tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion::test_open_ticket_evidence_file_still_flagged
- tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion::test_done_ticket_body_not_flagged
- tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion::test_dropped_ticket_body_not_flagged
- tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion::test_open_ticket_body_still_flagged
- tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion::test_done_report_not_flagged_even_if_state_lookup_fails
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-2374 (DOC004/DOC006 burn-down to zero + promote to ERROR).

T-2505 exempted DOC006 from checking historical ticket records, keyed on TERMINAL ticket
state (done/dropped): tickets/<id>/ticket.md when the ticket's state is done/dropped, and
tickets/<id>/done-report.md unconditionally (src/frob/gates/_docptr.py::_is_historical_
ticket_doc).

That exemption does NOT cover tickets/<id>/evidence/*.md or tickets/<id>/attachments/*.md --
files written under a DONE/DROPPED ticket that are the SAME historical-record class (written
once, describing what was true at the time, never edited again) but live one directory level
deeper. T-2374 measured 3 live DOC006 findings of exactly this shape (T-1881/evidence/
fix-measurement.md, T-2195/attachments/*.md, T-2328/attachments/*.md, all under DONE
tickets) and waived them individually with a disclosed reason rather than widen this ticket's
scope into _docptr.py.

FIX: extend _is_historical_ticket_doc's TICKET_DOC_RE (or add a sibling check) to also match
tickets/<id>/evidence/<file>.md and tickets/<id>/attachments/<file>.md, gated on the SAME
terminal-state lookup _terminal_ticket_ids already computes -- no new positive control is
needed beyond re-running T-2505's existing open-ticket-still-fires test against an
evidence/attachments path to confirm the boundary holds there too.

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
