---
id: T-2505
title: DOC006/COV003/REF001 should not police historical records (117 of 140 findings)
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: T-2501
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_docptr.py
- tests/test_docptr_gate.py
evidence_scope:
- tests/test_docptr_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_docptr_gate.py
  reason: T-2505 fix's own tests live here (SCOPE002)
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion::test_done_ticket_body_not_flagged
- tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion::test_dropped_ticket_body_not_flagged
- tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion::test_open_ticket_body_still_flagged
- tests/test_docptr_gate.py::TestDoc006TicketHistoricalExclusion::test_done_report_not_flagged_even_if_state_lookup_fails
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 273f421a9c2c868a5da2ceddf52c9df9922d146c
---
MEASURED 2026-08-18 against a full unbudgeted `frob check`:

    140 DOC006 findings total
    117 of them (84%) live in tickets/ -- done reports and closed
        ticket bodies
     23 live in docs/

Same lens, same run: 13 COV003 and 11 REF001 also fire inside tickets/.
141 findings total are aimed at historical records.

WHY THIS IS WRONG, not merely noisy. A done report is an immutable
record of what was true when it was written. Requiring its pointers to
resolve forever means every rename retroactively invalidates history,
and "fixing" it means EDITING THE HISTORICAL RECORD TO SAY SOMETHING IT
DID NOT SAY -- falsifying the archive to satisfy a linter. That is the
opposite of drift prevention.

DOC006 ITSELF IS A GOOD RULE AND MUST BE KEPT. Its 140 findings break
down as: 67 cli invocation (docs naming subcommands that do not exist,
e.g. `frob ticket check-repro`, `frob design ...`), 34 file/path, 18 code
symbol, 13 config reference, 8 doc-anchor. The first row alone earns its
keep in THIS repo specifically, because agents read docs/ and then run
what they say -- a doc naming a nonexistent subcommand burns an agent
cycle and produces a confused report. This is the documentation-as-typed-
graph property frob exists to provide.

THE FIX IS A SCOPE DECISION, NOT A BURN-DOWN. Living documents (docs/,
src/ docstrings) carry pointer obligations. Historical records
(tickets/*/done-report.md, closed ticket bodies, the archive) do not.

Result: 117 DOC006 findings removed with ZERO loss of signal, leaving 23
real doc-drift findings -- at which point the rule is enforceable rather
than aspirational and can be promoted to ERROR for the v1.0.0 severity
freeze. Same treatment for the 13 COV003 and 11 REF001 in tickets/.

CARE REQUIRED ON THE BOUNDARY. An OPEN ticket's body is not a historical
record -- it describes work still to be done, and a dangling pointer
there is real. The exemption must key on TERMINAL state (done/dropped)
plus done-report files, never on the tickets/ path prefix alone.
Getting this wrong in the permissive direction silently stops checking
live tickets, which is the silent-zero shape (T-2391) this repo is
already burning down.

POSITIVE CONTROL, BOTH DIRECTIONS: a dangling pointer in an OPEN
ticket's body must still FIRE; the same pointer in a done-report must
NOT.