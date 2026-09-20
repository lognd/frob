## Done report

frob ticket new --json parsed --json into cfg.ticket_json (src/frob/app/ticket_runner/_new.py) but the _new handler never read it -- output stayed the plain human 'created T-####: <title>' line regardless of --json, unlike frob ticket show --json (ticket.model_dump_json, src/frob/app/ticket_runner/_query.py:180), which already honors the flag correctly.

Fix: _new now emits a JSON object (id, title, kind, warnings) on stdout via _emit_new_ticket_json when cfg.ticket_json is set, replacing the human line the same way show --json does, emitted LAST after every other write (evidence apply, clipboard attach, ledger commit) so id is never printed before the ticket is durable. The T-2177 scope-plausibility warnings (the one class of warning a scripted --json caller could otherwise never see, since it rarely reads stderr/log output) are echoed as a structured warnings list. Split _log_scope_plausibility_warnings and _emit_new_ticket_side_effects out of _new to keep it under ARCH001's line threshold after this addition.

MUST-FIRE: test_json_flag_prints_parseable_json_with_id proves --json produces valid, parseable JSON on stdout containing the created id/title/kind, and that the human line is NOT also printed. MUST-STAY-QUIET: test_without_json_flag_output_is_unchanged proves the plain-text path is unaffected and no JSON-parseable line leaks into it.

Filed: none (no out-of-scope discoveries this ticket).

Two DOC006 findings on tickets/T-3807 and tickets/T-3849 remain under --ticket T-3308 -- confirmed pre-existing on main via git show, unrelated to this ticket's scope.

### Changed
```
 src/frob/app/ticket_runner/_new.py | 106 +++++++++++++++++++++++++++++++------
 tests/unit/test_ticket_new_json.py |  84 +++++++++++++++++++++++++++++
 tickets/T-3308/ticket.md           |  15 ++++++
 3 files changed, 190 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_new_json.py::TestNewJsonOutput::test_json_flag_prints_parseable_json_with_id` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_json.py::TestNewJsonOutput::test_without_json_flag_output_is_unchanged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 2 error(s), 4371 warning(s), 924 waived
- error-findings: DOC006@tickets/T-3807/ticket.md, DOC006@tickets/T-3849/ticket.md
