## Done report

Changed: `_run_gates` in src/frob/check/_python.py now special-cases
`GateError.QueueUnavailable` as a hard ERROR ToolResult (exit_code=1,
remedy text), never a soft skip; all other GateError variants keep the
existing soft-skip behavior. Companion fix: `validate_evidence` and
`add_evidence` (src/frob/tickets/__init__.py) plus `TicketSpec.evidence`
(src/frob/tickets/_models.py, new `MalformedEvidence` error) give an
in-process, schema-validated path for evidence to land on a ticket, so a
malformed entry can no longer be constructed via `new_ticket`. A CLI
flag to drive `add_evidence` from `frob ticket close --evidence` would
touch src/frob/__main__.py, src/frob/app/**, and docs/** -- all outside
this ticket's scope; filed as a follow-up.
Evidence: see evidence: list above (all collected, pytest --collect-only verified).
Filed: T-0106 (CLI wiring for `frob ticket close --evidence`; renumbered from
branch-local T-0103 at merge -- id collision with the store-capacity bug).
Gates: `frob check --ticket T-0102` and plain `frob check` both exit 0
(gates stage genuinely executes, no violations introduced).
