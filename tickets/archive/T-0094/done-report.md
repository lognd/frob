## Done report

Changed:
- src/frob/tickets/_models.py::TicketError.UnknownEvidence
- src/frob/tickets/__init__.py::_matches_collected
- src/frob/tickets/__init__.py::add_evidence
- src/frob/app/ticket_runner.py::_evidence
- src/frob/app/ticket_runner.py::run (dispatch case "evidence")
- src/frob/app/config.py::AppConfig.ticket_evidence_ids
- src/frob/__main__.py::_add_ticket_lifecycle_parsers (evidence subparser)
- docs/modules/tickets.md (Public API, Error types, Integration points)

`add_evidence` takes the collected node-id set as a parameter (dependency
injection) rather than importing `frob.testing` directly -- `frob.testing`
transitively imports `frob.graph`, which the module docstring explicitly
disclaims (docs/rework.md cycle-avoidance). The CLI runner
(`frob.app.ticket_runner._evidence`) is the one place that calls
`frob.testing.collect_python_tests` and passes the result in. A batch with
any unresolvable id is rejected wholesale (Err(UnknownEvidence)) rather than
partially applied, so a typo can never sneak an unrelated id into evidence.
Dogfooded: `uv run frob ticket evidence T-0094 <6 node ids>` recorded this
ticket's own evidence below.

Evidence: see structured `evidence:` list above (6 pytest node ids in
tests/test_tickets.py::TestEvidence, recorded via the new command itself).
Filed: none.
Gates: `frob check --ticket T-0094 --only gates` clean (exit 0; remaining
118 warn-level violations are pre-existing repo-wide PERF/ARCH debt outside
this ticket's scope, unaffected by this change). Widened scope mid-ticket
(recorded via `frob ticket sweep`) to include `src/frob/__main__.py`,
`docs/modules/tickets.md`, and `tickets.md` -- all required to wire the CLI
subcommand and document it per house rules, and not anticipated by the
ticket's original scope.
