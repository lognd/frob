---
id: T-0832
title: 'land: T-0754 re-verification compares -1 sentinel when fresh check cannot
  run (done ticket, no lease)'
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner.py
- tests/test_ticket_land.py
- src/frob/tickets/_models.py
- src/frob/tickets/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'Fixing the -1 sentinel required changing DoneReportClaims (gate_errors/

    warnings/waived become int | None) and its render/parse functions in

    _models.py, plus set_done_report''s capture logic in __init__.py -- these

    are the single source of truth the -1 sentinel was stored/rendered

    through. _land.py alone cannot represent "unmeasured" without them.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: 'Fixing the -1 sentinel required changing DoneReportClaims (gate_errors/

    warnings/waived become int | None) and its render/parse functions in

    _models.py, plus set_done_report''s capture logic in __init__.py -- these

    are the single source of truth the -1 sentinel was stored/rendered

    through. _land.py alone cannot represent "unmeasured" without them.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_unmeasured_fresh_check_skips_gate_reverification_land_proceeds
- tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_two_unmeasured_gate_claims_never_vacuously_match
designated_repro_test: null
threat: null
component: null
---
Hit live landing T-0830 (2026-07-23): the ticket was self-closed (done,
lease released), so the T-0754 post-merge re-verification's fresh
`frob check --ticket` refused to run (no lease) and exited 1 with no
parsable gate-summary. Instead of surfacing that, land compared the
recorded claim against a -1 sentinel and refused with "a fresh check now
shows -1 error(s) (warnings 1124->-1, waived 207->-1)" -- a nonsense
message that misdiagnoses an unrunnable check as a divergence. Second
gap: `frob ticket done-report` on the same done ticket also embeds the
-1 sentinel (warns "no parsable gate-summary line (exit=1)" but writes
anyway), after which the land PASSES because -1 == -1 -- the
re-verification is silently vacuous exactly when it could not measure.

Fix: when the fresh check cannot produce a gate-summary (missing lease,
crash, exit!=0 without summary), land must say that explicitly and treat
it as its own failure mode (or re-lease transiently for the check), never
compare or store the -1 sentinel; done-report should refuse to embed an
unmeasured claim.