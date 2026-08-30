## Done report

T-3468 DEFECT 2 (mirror gap): frob ticket done-report writes to the worktree's own branch only, deliberately (LEDGER_VERB_STRATEGY, GENERIC_COMMIT_UNMIRRORED) since land carries it atomically with the code. That left the visibility gap silent. Added _warn_if_done_report_not_visible_on_primary (src/frob/app/ticket_runner/_verify.py, wired into _done_report), mirroring T-3137's fail-visibility-warning precedent: a loud ERROR log naming the primary checkout and warning against re-running done-report there (which would risk the add/add conflict the ticket describes), instead of mirroring the write early and breaking the deliberate state-machine-progress-follows-land design.

DEFECT 3 (heading collision): frob ticket body --append refused a literal '## Done report' heading with a generic BodyTextAmbiguousSection error and no pointer to the dedicated verb. _body (src/frob/app/ticket_runner/_mutate.py) now special-cases that error to name 'frob ticket done-report' explicitly.

_setters.py's body-refusal logic itself (out of this ticket's scope: src/frob/app/ticket_runner/** + src/frob/tickets/_reporting.py) was left untouched -- the message fix lives entirely in the thin CLI dispatch layer, in scope.

Tests: TestDoneReportNotVisibleOnPrimaryWarning (must-fire + must-stay-quiet) in tests/unit/test_ticket_runner_ledger_mirror.py; test_cli_ambiguous_done_report_heading_points_to_done_report_verb in tests/test_tickets_body.py. Doc: docs/modules/tickets-data-storage.md's body/CLI section updated (AFFECT001).

Filed: none -- both defects closed within declared scope.

### Changed
```
 tickets/T-3468/done-report.md | 25 +++++++++++++++++++++++++
 tickets/T-3468/ticket.md      | 30 ++++++++++++++++++++++++++++--
 2 files changed, 53 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestDoneReportNotVisibleOnPrimaryWarning::test_done_report_from_worktree_warns_when_not_visible_on_primary` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestDoneReportNotVisibleOnPrimaryWarning::test_done_report_from_primary_is_quiet` (pytest node id, verified passing when recorded)
- `tests/test_tickets_body.py::TestBodyCli::test_cli_ambiguous_done_report_heading_points_to_done_report_verb` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 16 error(s), 4797 warning(s), 864 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3468, REL001@src/frob/__init__.py, SELFAUDIT001@src/frob/gates/_policy_weakening_gate.py, SELFAUDIT001@tests/unit/strata/test_strata_core_gil.py, SELFAUDIT001@tests/unit/test_land_parity_gate.py, SELFAUDIT001@tests/unit/test_sync_claude_config_stale_guard_t3408.py, SELFAUDIT001@tests/unit/verify/test_worker.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
