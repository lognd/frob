---
id: T-0541
title: 'gates: SCOPE001/PRE001 fully disabled with no active ticket / off-convention
  branch (B9)'
state: done
kind: bug
origin: auditor
created: '2026-07-21'
priority: medium
parent: T-0403
tier: ticket
sprint: null
scope:
- src/frob/gates/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestRunGates::test_run_gates_blocks_prework_when_diff_load_fails_with_no_ticket
- tests/test_gates.py::TestRunGates::test_run_gates_blocks_scope_and_prework_when_no_ticket_touches_source
- tests/test_gates.py::TestRunGates::test_run_gates_skips_scope_without_ticket
- tests/test_gates.py::TestRunGates::test_run_gates_still_skips_scope_and_prework_for_ledger_only_diff
designated_repro_test: null
threat: null
component: null
---
docs/audits/gates-accounting.md B9. _build_ticket_scoped_jobs only registers scope+prework jobs when st.ticket is not None; active_ticket derives the ticket purely from the branch name's T-#### prefix. A branch not named after a ticket (or work on main) skips scope and pre-work enforcement entirely rather than failing. Fix direction: a diff that touches source with no derivable active ticket should be a loud blocking condition, not a skip.