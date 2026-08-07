---
id: T-0124
title: frob check --ticket exits 1 with no diagnostic output (repro on closed T-0075)
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/check_runner.py
- src/frob/check/**
- tests/system/test_cli_check.py
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_cli_check.py::TestCheckTicketScopedAlwaysReportsOnFailure::test_ticket_scoped_nonzero_exit_has_diagnostic_output
designated_repro_test: null
threat: null
component: null
---
frob check --ticket <ID> silently exits 1 with zero informative stdout/stderr beyond dispatch/WARNING noise, even for already-closed, evidenced tickets (repro: frob check --ticket T-0075 --skip-build). Repro'd while verifying T-0076; plain 'frob check' and 'frob check --json --only gates' both work fine and report exit 0 / expected diagnostic counts, and 'frob test --base main' passes cleanly, so this is isolated to the --ticket code path, not the underlying gates. Needs investigation into why the ticket-scoped runner swallows its failure reason. Likely related to T-0122 (summary can be swallowed) -- verify against its fix before independent work.
## Done report

Did not reproduce after T-0122/T-0125 landed: frob check --ticket
T-0075 (with and without --skip-build) exits 1 WITH full diagnostic
output; the silent exit was the logging save/restore race already
fixed at the root. Traced check_runner.run to confirm both report
branches log before sys.exit and no path exits silently. Added a
system regression test asserting a ticket-scoped nonzero exit is never
output-free, bound to check_runner.run. Verified on main at merge: 20
system tests pass.