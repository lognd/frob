## Done report

T-1720's lease had already freed (confirmed: no
.git/frob-leases/T-1720.json). Re-acked
src/frob/app/ticket_runner/_rapid_sweep.py::_file_regression_ticket
and ::run_deferred_post_land_sweep, then dropped both waivers
(AFFECT001 on _file_regression_ticket, DRIFT001/AFFECT001 on
run_deferred_post_land_sweep) that cited the T-1720 lease block --
their reason no longer applies now that the ack succeeded. No doc
CONTENT edit was owed (T-1935 only changed reported wording, not the
attribution/filing/sweep behavior the doc describes), confirming the
ticket body's own premise.

Scope extended from docs/modules/tickets.md alone to also include
src/frob/app/ticket_runner/_rapid_sweep.py -- the two waivers this
ticket's own body says to drop live there, not in the doc file.

### Changed
```
 tickets/T-1899/done-report.md | 32 ++++++++++++++++++++++++++++++++
 tickets/T-1899/ticket.md      |  6 +++++-
 tickets/T-1952/ticket.md      | 14 +++++++++++++-
 tickets/T-1973/ticket.md      |  6 +++++-
 tickets/T-1996/ticket.md      |  6 +++++-
 5 files changed, 60 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/t-1899/src/frob/gates/_root_asset_dirs.py, PRE001@tickets/T-1952, TICK004@tickets.md
