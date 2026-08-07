## Done report

Added `frob ticket kind <id> <kind>` (new `_kind` handler in
src/frob/app/ticket_runner.py, forwarding to the new `frob.tickets.set_kind`,
mirroring `_priority`/`set_priority` exactly -- ledger-locked write, no
terminal-state special-case since `set_priority` has none either, INFO log
line on success). CLI wiring added in src/frob/__main__.py
(`_add_ticket_kind_parser`, hardcoded enum choices matching `new`'s
--kind list) and a new AppConfig.ticket_kind_value field in
src/frob/app/config.py (plus its from_external copy-loop entry) --
config.py/__main__.py were scope-added since they were not in T-0834's
declared scope.

Fixed the --evidence-cmd cwd bug: `_run_evidence_command` now accepts a
`cwd` parameter forwarded to `guarded_subprocess_run`'s `cwd=`;
`run_cmd_evidence` and `add_cmd_evidence` thread it through, with
`add_cmd_evidence` passing its own `root` argument (the ticket's resolved
--path) as cwd. Both the launch-failure and nonzero-exit log lines in
_run_evidence_command now name the resolved cwd. `reverify_cmd_evidence`
keeps cwd=None (inherits process cwd) since it is not scoped to any one
ticket's worktree.

Tests added in tests/test_ticket_evidence.py: TestSetKind (field update,
audit-trail-is-the-log-line, terminal-state parity with set_priority --
both simply succeed, no special-casing on either side), TestKindCliInvalidKind
(invalid kind refused via TicketKind(...) ValueError, persisted-change
round trip), TestEvidenceCmdCwd (relative-path probe only succeeds with
cwd=tmp_path, add_cmd_evidence runs against the ticket's own root, and a
failing command's log line names the resolved cwd).

### Changed
```
 src/frob/__main__.py          |  18 +++-
 src/frob/app/config.py        |   6 ++
 src/frob/app/ticket_runner.py |  41 ++++++++-
 src/frob/tickets/__init__.py  |  65 +++++++++++++--
 tests/test_ticket_evidence.py | 187 ++++++++++++++++++++++++++++++++++++++++++
 tickets.md                    |  78 +++++++++++++++++-
 6 files changed, 384 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/test_ticket_evidence.py::TestSetKind::test_updates_kind_field` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestSetKind::test_audit_trail_present` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestSetKind::test_terminal_state_matches_priority` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestKindCliInvalidKind::test_invalid_kind_refused` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestKindCliInvalidKind::test_kind_cli_changes_persisted_kind` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestEvidenceCmdCwd::test_relative_probe_only_succeeds_from_worktree` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestEvidenceCmdCwd::test_add_cmd_evidence_runs_against_ticket_path_worktree` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestEvidenceCmdCwd::test_failure_message_names_resolved_cwd` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 0 error(s), 1203 warning(s), 210 waived
