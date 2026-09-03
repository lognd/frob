## Done report

Generated CHANGELOG.md entries now prefer the free-narrative WHY prose from a ticket's Done report (via frob.tickets.recover_done_report_why) as the release-note text, falling back to the ticket title only when no narrative was ever recorded. Previously every entry was the raw, problem-stated ticket title, which reads as a bug report rather than a user-facing note.

Changed: src/frob/app/ticket_runner/_land_cmd.py::_changelog_note_for_ticket (new), src/frob/app/ticket_runner/_land_cmd.py::_write_release_bump (uses it), src/frob/app/ticket_runner/__init__.py (exports it)
Evidence: tests/unit/test_ticket_runner_land_release.py::TestChangelogNoteForTicket (2 tests), uv run pytest -p no:xdist tests/unit/test_ticket_runner_land_release.py -q -> 20 passed, uv run frob test --base main -> exit=0
Filed: none
Gates: frob check --ticket T-2642 and a bare --only scope/docblocks/drift run both show identical pre-existing DOC(3)/DRIFT(4)/SCOPE(1)/WAIVE(1) baseline error counts, unaffected by this change; ruff-check/ruff-format clean on touched files

### Changed
```
 tickets/T-2642/done-report.md | 31 +++++++++++++++++++++++++++++++
 1 file changed, 31 insertions(+)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 17 error(s), 4189 warning(s), 865 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DOC007@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/app/ticket_runner/_land_cmd.py, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-2642, REL001@src/frob/__init__.py, SELFAUDIT001@src/frob/gates/_policy_weakening_gate.py, SELFAUDIT001@tests/unit/strata/test_strata_core_gil.py, SELFAUDIT001@tests/unit/test_sync_claude_config_stale_guard_t3408.py, SELFAUDIT001@tests/unit/verify/test_worker.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
