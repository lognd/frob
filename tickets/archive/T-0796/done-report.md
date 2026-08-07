## Done report

Threaded `accepts: Sequence[int] | None` through `add_cmd_evidence`
(src/frob/tickets/__init__.py) using the same 0-based validation and
Err(AcceptanceIndexOutOfRange) shape as `add_evidence`, then delegated the
merge/write to the existing `_append_evidence_and_write` helper so cmd
evidence binds onto named acceptance criteria the same way pytest-node
evidence does. Wired `cfg.ticket_accepts` through both CLI call sites in
src/frob/app/ticket_runner.py (`_close`, `_evidence`, via `_apply_cmd_evidence`,
which gained the same `accepts` parameter). Added a regression test class
(tests/test_tickets_evidence_cli.py::TestCmdEvidenceAcceptsBinding) driving
both the `evidence` and `close` CLI subcommands with a docs-kind ticket,
`--evidence-cmd` and `--accepts 0`, asserting `ticket.acceptance[0].evidence`
is bound to the recorded cmd: entry.

### Changed
```
 src/frob/app/ticket_runner.py      | 25 +++++++++---
 src/frob/tickets/__init__.py       | 35 +++++++++++++----
 tests/test_tickets_evidence_cli.py | 79 ++++++++++++++++++++++++++++++++++++++
 tickets.md                         | 31 +++++++++++++--
 4 files changed, 154 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/test_tickets_evidence_cli.py::TestCmdEvidenceAcceptsBinding::test_evidence_cmd_with_accepts_binds_acceptance_via_cli` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestCmdEvidenceAcceptsBinding::test_close_evidence_cmd_with_accepts_binds_acceptance_via_cli` (pytest node id, verified passing when recorded)
