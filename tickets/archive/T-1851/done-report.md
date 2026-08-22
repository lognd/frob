## Done report

Recovered from the stranded .claude/worktrees/gate-internals worktree (leases
reclaimed via T-1876's holder-liveness detection). That worktree carried 59
commits spanning several unrelated tickets (T-1824, T-1830, T-1831, T-1892..
T-1924, etc), so rather than land it wholesale (T-1618 passenger guard would
correctly refuse), the T-1851-specific commits (6e035b9b4, 2b9dcff4b) were
cherry-picked clean onto a fresh worktree cut from current main.

Adds --designate-repro-reason/--designate-repro-reason-file to
`frob ticket evidence <id> --designate-repro NODE-ID`, threads the value
through AppConfig.ticket_designate_repro_reason(_file) into
set_designated_repro_test's reason kwarg, and requires a reason whenever the
call is a genuine REdesignation (an already-set designated_repro_test
changing to a different bound id) -- mirroring T-1733's --replace --reason
precedent. A first-time designation or a redundant re-designation of the
same id needs no reason.

### Changed
```
 src/frob/_cli_parsers/_ticket/_closeout.py |  21 +++
 src/frob/app/_config_external.py           |   4 +
 src/frob/app/config.py                     |  14 ++
 src/frob/app/ticket_runner/_verify.py      |  85 ++++++++-
 tests/test_tickets_evidence_cli.py         | 270 +++++++++++++++++++++++++++++
 tickets/T-1851/ticket.md                   |  25 ++-
 6 files changed, 416 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_tickets_evidence_cli.py::TestDesignateReproReasonCli::test_first_time_designation_needs_no_reason` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestDesignateReproReasonCli::test_redesignation_without_reason_exits_nonzero_and_writes_nothing` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestDesignateReproReasonCli::test_redesignation_with_reason_records_audit_entry` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestDesignateReproReasonCli::test_redesignation_reason_file_is_read_verbatim` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestDesignateReproReasonCli::test_reason_and_reason_file_together_exits_nonzero` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestDesignateReproReasonCli::test_from_external_carries_both_new_fields` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
