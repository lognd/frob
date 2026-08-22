## Done report

T-2123 follow-up: added the filing-time acknowledgement path
`frob ticket new --scope-breadth-ack --scope-breadth-ack-reason TEXT`.

Wiring: CLI parser flags in src/frob/_cli_parsers/_ticket/_new.py ->
AppConfig fields (ticket_scope_breadth_ack/ticket_scope_breadth_ack_
reason) in src/frob/app/config.py, threaded through
src/frob/app/_config_external.py's bool/string field-copy tuples ->
TicketSpec fields (scope_breadth_ack/scope_breadth_ack_reason) in
src/frob/tickets/_models.py -> _ticket_spec_from_cfg (src/frob/app/
ticket_runner/_new.py) -> _ticket_from_spec (src/frob/tickets/
_new_renumber.py), which now sets both fields on the written Ticket.
_warn_over_broad_scope_on_new's existing `if ticket.scope_breadth_ack:
return` early-out (unchanged) fires immediately once the flag is set at
filing time -- no second acknowledgement mechanism, same field
`frob ticket scope-ack <id>` already writes post-filing.

A reason is required when the flag is set: enforced in
_validate_new_ticket_spec (src/frob/tickets/_new_renumber.py) via the
existing TicketError.ScopeBreadthAckReasonMissing, reusing the same
error set_scope_breadth_ack already raises for its own channel. This is
a plain function-level guard, not a pydantic TicketSpec validator --
found and filed a real gate inconsistency along the way (WIRE001's own
rescue predicate does not recognize a pydantic model_validator even
though WAIVE008 assumes it does; a fresh model_validator here false-
positived both checks with no clean waiver). Filed as a follow-up child,
disclosed in _validate_new_ticket_spec's own updated docstring.

MEASURED before touching severity (required by the ticket): how many
currently-queued (queued/planned/in-progress) tickets would fail a
refusal-unless-acknowledged posture. Result: 24 of 68 (about a third of
the live queue). That is large, so the filing-time check was NOT
escalated from WARN to a refusal -- doing so now would repeat the exact
mistake T-1783's DOC012 WARN-at-ship posture was designed to avoid.
Recorded in docs/modules/tickets-data-storage.md's new "Filing-time
acknowledgement path: --scope-breadth-ack (T-2302)" section, including
the measurement query.

Filed: one follow-up child (WIRE001/WAIVE008 pydantic-validator gate
inconsistency), NOT parented to T-2302 since it is an independent gate
defect discovered along the way, not literally part of this feature.

### Changed
```
 tickets/T-2302/ticket.md | 67 +++++++++++++++++++++++++++++++++++++++++++++---
 1 file changed, 64 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_new_ticket_scope_breadth_ack_flag.py::TestScopeBreadthAckFlag::test_acknowledged_broad_scope_is_silent_and_recorded` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_scope_breadth_ack_flag.py::TestScopeBreadthAckFlag::test_unacknowledged_broad_scope_still_warns` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_scope_breadth_ack_flag.py::TestScopeBreadthAckFlag::test_ack_without_reason_is_refused` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/gates/_fmt_directives.py, DRIFT002@scripts/fleet_status.py, DRIFT002@src/frob/verify/_drain.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2302/src/frob/_cli_parsers/_ticket/_new.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2302, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK004@tickets.md, WIRE003@docs/modules/cli.md
