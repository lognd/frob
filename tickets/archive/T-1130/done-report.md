## Done report

Extended T-1054's start-transition auto-commit to the remaining
ledger-writing verbs: `frob ticket new`/`drop`/`fail` now auto-commit
their own ledger change, with an opt-out flag, closing the gap where
"commit before dispatching" was coordinator memory instead of something
the tool itself guaranteed (the T-1018 incident cited in the ticket
body).

Generalized `frob.tickets._leases.commit_start_transition`'s own add-and-
commit primitive into `commit_ticket_ledger_change(root, ticket_id,
message, *, no_commit=False)`: same dirty-check/no-op/error-reporting
shape, but takes an arbitrary caller-supplied commit message and an
explicit `no_commit` opt-out. Both functions now funnel through the same
`_add_and_commit_tickets_md(root, ticket_id, message)` helper
(generalized to accept `message` instead of hardcoding "start
transition"). `start`'s own auto-commit is otherwise unaffected -- still
`commit_start_transition`, still gated by `warn_if_worktree_stale` (which
the new verbs deliberately do NOT run -- that warning is specific to the
moment a ticket is started, not every later ledger write on it).

New `--no-commit` flag added to the `new`/`fail`/`drop` argparse
subparsers (`src/frob/_cli_parsers/_ticket.py`), backed by a new
`AppConfig.ticket_no_commit: bool = False` field.

Per-verb wiring:
- `new` (frob.app.ticket_runner._new._new) commits LAST, after every
  other write the command makes (the new frontmatter block plus any
  `--evidence` ids applied right after) -- "new's commit must include the
  whole filed block" per the ticket body's own instruction -- with
  message `chore(tickets): file <id> <title>`.
- `drop` (frob.app.ticket_runner._close_cmd._drop) commits its Drop-
  reason line + DROPPED transition as one change -- `chore(tickets): drop
  <id>`.
- `fail` (frob.app.ticket_runner._close_cmd._fail) commits its Failure-
  log entry (plus any T-1131 requeue transition, landed just before this
  ticket) as one change -- `chore(tickets): <id> fail-logged`.

Worktree-side behavior is unchanged: both commit functions operate
identically under ANY git root (main or worktree) -- exactly the same as
`commit_start_transition` already did before this ticket; a worktree
agent's own eventual close/land commits already absorb the extra commit
the same way they always have.

Updated docs/modules/tickets.md (new "New/drop/fail auto-commit
(T-1130)" section, matching the existing T-1054 section's structure) and
docs/modules/app.md (a per-field paragraph for the new AppConfig.
ticket_no_commit field, matching that doc's own T-1069/T-1004 precedent
style) in the same change.

Out of scope, not touched: the pre-existing SCOPE002 scope-closure debt
(already tracked as T-1145); pre-existing INV006 (src/frob/app/
ticket_runner/_mutate.py) and DRIFT002 (test_app_daemon_proxy.py-related,
landed by a sibling wave-18 agent's daemon-proxy work) findings surfaced
by `frob check --ticket T-1130` are unrelated to this diff, confirmed by
symbol/file.

### Changed
```
 docs/modules/app.md                      |   8 ++
 docs/modules/tickets.md                  |  49 +++++++++++
 src/frob/_cli_parsers/_ticket.py         |  25 ++++++
 src/frob/app/config.py                   |   7 ++
 src/frob/app/ticket_runner/_close_cmd.py |  34 +++++++-
 src/frob/app/ticket_runner/_new.py       |  22 ++++-
 src/frob/tickets/_leases.py              |  70 ++++++++++++---
 tests/test_ticket_leases.py              | 145 +++++++++++++++++++++++++++++++
 tickets.md                               |  70 ++++++++++++++-
 9 files changed, 411 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_commits_dirty_ledger_with_given_message` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_no_op_when_ledger_already_clean` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_no_commit_flag_skips_entirely_even_when_dirty` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestNewDropFailAutoCommit::test_new_auto_commits_the_filed_block` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestNewDropFailAutoCommit::test_new_no_commit_leaves_ledger_dirty` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestNewDropFailAutoCommit::test_drop_auto_commits_the_state_change` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestNewDropFailAutoCommit::test_fail_auto_commits_the_failure_log_and_requeue` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 23 error(s), 1078 warning(s), 428 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_close_cmd.py, ARCH001@src/frob/doctor.py, ARCH103@src/frob/app/stats_runner.py, COV001@src/frob/app/stats_runner.py, COV001@src/frob/gates/_tracked_files.py, COV003@tickets/T-0138, COV003@tickets/T-0226, COV003@tickets/T-0629, COV003@tickets/T-0700, COV003@tickets/T-0702, DRIFT002@src/frob/app/exports_runner.py, DRIFT002@src/frob/app/stats_runner.py, DRIFT002@src/frob/serve/_tools.py, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/doctor.py:243, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:295, INV006@src/frob/app/stats_runner.py, PII012@tests/system/test_cli_doctor.py, SELFAUDIT001@design
