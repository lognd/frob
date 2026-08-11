## Done report

No doc edit made -- this ticket's own premise is STALE. Both doc
sections it asks for already exist and are current on main:
"## Orphaned evidence deletion (T-1946)" and "## Evidence-only scope
(T-1944)" (docs/modules/tickets.md), added by T-1946's own land
(commit 2e3bcc6fa, `git log -S` confirms) despite the ticket body's
claim that T-1967's lease blocked committing them at the time -- by
the time T-1946 actually landed, that block had evidently cleared, and
the doc content went in as part of that same land rather than as a
deferred follow-up.

Verified both anchors' frob:describes targets still resolve to real,
current symbols: src/frob/tickets/_land.py::_check_orphaned_evidence_
deletion and src/frob/tickets/_scope.py::demote_to_evidence_only both
exist. `frob check --ticket T-1973 --only drift` is clean (0 errors).
No reference to T-1973 anywhere in src/ or docs/ -- nothing left
pointing at this ticket as a pending obligation. Closing as
already-satisfied, no content change needed.

### Changed
```
 tickets/T-1899/done-report.md | 32 ++++++++++++++++++++++++++++++++
 tickets/T-1899/ticket.md      |  6 +++++-
 tickets/T-1952/done-report.md | 34 ++++++++++++++++++++++++++++++++++
 tickets/T-1952/ticket.md      | 14 +++++++++++++-
 tickets/T-1973/ticket.md      |  6 +++++-
 tickets/T-1996/done-report.md | 42 ++++++++++++++++++++++++++++++++++++++++++
 tickets/T-1996/ticket.md      |  6 +++++-
 7 files changed, 136 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/t-1899/src/frob/gates/_root_asset_dirs.py, PRE001@tickets/T-1973, TICK004@tickets.md
