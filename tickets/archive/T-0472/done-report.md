## Done report

Added `frob ticket requeue <id> [--reason TEXT]`, the state-machine-legal
in-progress -> queued transition, so a parked or mis-started ticket can be
honestly requeued via the CLI instead of hand-editing the ledger. The
`in-progress -> queued` edge already exists in `_TRANSITIONS`, so `_requeue`
calls the existing `transition()` and refuses (exit 1, logged) unless the
ticket is currently in-progress. `--reason` is optional and, when given, is
only logged (not persisted) -- requeue carries no Done-report/evidence
surface of its own. Since the T-0453 tree-lease is derived live from
IN_PROGRESS state + declared scope, the state transition alone releases the
lease; no separate release step was needed. Wired into `_ticket_dispatch_table`,
`AppConfig.ticket_reason`, the argparse subparser, and documented in
docs/modules/tickets.md (state-machine section + CLI command list).

### Changed
```
 docs/modules/tickets.md               | 19 +++++++++---
 src/frob/__main__.py                  | 12 +++++++-
 src/frob/app/config.py                |  4 +++
 src/frob/app/ticket_runner.py         | 55 ++++++++++++++++++++++++++++++---
 tests/unit/test_app_runners_batch7.py | 57 +++++++++++++++++++++++++++++++++++
 tickets.md                            | 48 +++++++++++++++++++++++++++--
 6 files changed, 183 insertions(+), 12 deletions(-)
```

### Evidence
(no evidence recorded)
