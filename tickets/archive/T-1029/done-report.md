## Done report

Added `frob.tickets.add_acceptance(root, ticket_id, criteria)`: appends one
or more fresh, unbound AcceptanceCriterion items to an EXISTING ticket's
`acceptance` tuple, under `ledger_lock` end to end (T-0458 single-writer
invariant) -- before this, `frob ticket new --acceptance` was the only CLI
path to attach a criterion at all, so a ticket that needed one added after
filing (T-0894's agent hit this closing a new-gate-rule ticket) had to be
hand-edited. Blank criteria are dropped after `.strip()`; if nothing
survives, `Err(TicketError.AcceptanceChangeEmpty)` -- the same "don't call
this for nothing" discipline `mutate_scope`/`mutate_labels` already
enforce, matching this repo's existing idiom exactly (new TicketError
variant, `_load_ticket_and_queue` + `ledger_lock` + `model_copy` + `write_
ticket` shape).

Wired the new `frob ticket accept <id> --criterion TEXT... |
--criterion-file PATH` subcommand end to end: AppConfig fields
(ticket_accept_criterion/ticket_accept_criterion_file), an argparse
subparser (_add_ticket_accept_parser, mirroring _add_ticket_scope_parser's
shape), a CLI handler (_accept in ticket_runner/_mutate.py, forwarding
only -- no re-derived validation) reusing `_new._parse_acceptance_file`
for --criterion-file so the file-parsing convention has exactly one
implementation, and a dispatch-table entry. Verified end to end with a
real `frob ticket new` + `frob ticket accept` + `frob ticket show` round
trip against a scratch git repo (both --criterion and --criterion-file
paths, plus the empty-criteria refusal), not just unit tests.

docs/modules/tickets.md gained a "`frob ticket accept` (T-1029)" section;
docs/modules/app.md's Config section documents the two new AppConfig
fields. `frob:ticket T-1029` added to `ticket_runner.run`'s directive
stack (its dispatch-table entry required touching this function) alongside
a reasoned `frob:waive AFFECT001` for the pre-existing
EXHAUSTIVENESS-GATE.md#reg010 doc binding that change orthogonally tripped
(a new SUBCOMMAND is not a live gate-rule-id drift, the concern that doc
anchor exists for).

`frob check --ticket T-1029` is clean except two pre-existing, unrelated
findings verified via `git diff main -- <file>` to be empty (not touched by
this ticket): a COV001 finding in src/frob/gates/_tracked_files.py, and 6
E501 ruff findings in src/frob/vet/_supplychain.py (both landed by sibling
agents mid-wave).

### Changed
```
 docs/modules/app.md                    |  8 ++++
 docs/modules/tickets.md                | 30 +++++++++++++++
 src/frob/_cli_parsers/_ticket.py       | 40 +++++++++++++++++++-
 src/frob/app/config.py                 | 10 +++++
 src/frob/app/ticket_runner/__init__.py | 12 +++++-
 src/frob/app/ticket_runner/_mutate.py  | 67 +++++++++++++++++++++++++++++++++-
 src/frob/tickets/__init__.py           | 55 ++++++++++++++++++++++++++++
 src/frob/tickets/_models.py            |  5 +++
 tests/test_tickets.py                  | 55 ++++++++++++++++++++++++++++
 tickets.md                             | 60 +++++++++++++++++++++++++++++-
 10 files changed, 336 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestAddAcceptance::test_appends_criteria_to_existing_ticket` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestAddAcceptance::test_empty_criteria_is_rejected` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestAddAcceptance::test_blank_criteria_are_dropped` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 7 error(s), 1043 warning(s), 425 waived
- error-findings: COV001@src/frob/gates/_tracked_files.py, E501@/home/logan/projects/frob/.claude/worktrees/w17-tickets/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w17-tickets/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w17-tickets/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w17-tickets/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w17-tickets/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w17-tickets/src/frob/vet/_supplychain.py:295
