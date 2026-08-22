## Done report

Added `frob ticket body <id> (--append TEXT|--append-file PATH | --set
TEXT|--set-file PATH) --reason TEXT|--reason-file PATH` -- the validated,
single-writer CLI verb for amending a ticket's free-text body, closing the
only remaining gap that forced agents to hand-edit
tickets/T-####/ticket.md.

Implementation: `frob.tickets.set_body` (src/frob/tickets/_setters.py),
new `BodyChangeEntry` audit-trail model + `Ticket.body_changes` field
(src/frob/tickets/_models.py), CLI parser
(src/frob/_cli_parsers/_ticket/_metadata.py::_add_ticket_body_parser),
dispatch handler (src/frob/app/ticket_runner/_mutate.py::_body), AppConfig
fields (src/frob/app/config.py). `--reason` is mandatory (refused via
TicketError.BodyReasonMissing on blank/whitespace-only), same T-2353
accountability precedent as priority/kind/component/tier.

Friction encountered doing this work (as briefed, reporting it): the CLI
wiring needs `src/frob/app/_config_external.py`'s hardcoded field-name
tuples updated (`_STRING_FIELDS`/`_PATH_FIELDS`) for argparse Namespace
values to reach AppConfig at all. That file is held by T-2387's live
lease for the entire session -- exactly the scope-lease collision this
drive's coordinator warned about. Worked around it by testing `_body`
directly against a hand-constructed AppConfig (the `TestKindCliInvalidKey`
precedent in tests/test_ticket_evidence.py) rather than through argparse
end-to-end, and left a two-line follow-up patch to apply to
_config_external.py once T-2387's lease clears (see Filed below) -- the
verb is NOT reachable via the real `frob` CLI argv path until that lands.

BUG002: repro test committed alone first (5c4874a48), confirmed
FAILED_AT_PARENT, fix committed on top, --designate-repro validated
against 5c4874a48 as base-ref.

Filed: T-2402 (wires the AppConfig field-copy tuples once
T-2387's lease on _config_external.py clears -- this drive's own
contention-cluster problem, the exact thing T-2395 in this series makes
discoverable up front instead of by hitting it).

### Changed
```
 docs/modules/tickets-data-storage.md       |  42 +++++++
 src/frob/_cli_parsers/_ticket/__init__.py  |   4 +
 src/frob/_cli_parsers/_ticket/_metadata.py |  63 ++++++++++
 src/frob/app/config.py                     |  10 ++
 src/frob/app/ticket_runner/__init__.py     |   3 +
 src/frob/app/ticket_runner/_mutate.py      | 100 ++++++++++++++++
 src/frob/tickets/__init__.py               |   4 +
 src/frob/tickets/_models.py                |  45 ++++++++
 src/frob/tickets/_setters.py               |  86 ++++++++++++++
 tests/test_tickets_body.py                 | 180 +++++++++++++++++++++++++++++
 tickets/T-2392/ticket.md                   |  94 ++++++++++++++-
 tickets/T-2402/ticket.md         |  49 ++++++++
 12 files changed, 678 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_tickets_body.py::TestBodyAmend::test_append_appends_text` (pytest node id, verified passing when recorded)
- `tests/test_tickets_body.py::TestBodyAmend::test_set_replaces_text` (pytest node id, verified passing when recorded)
- `tests/test_tickets_body.py::TestBodyAmend::test_reason_missing_refuses` (pytest node id, verified passing when recorded)
- `tests/test_tickets_body.py::TestBodyAmend::test_append_records_body_change_entry` (pytest node id, verified passing when recorded)
- `tests/test_tickets_body.py::TestBodyAmend::test_positive_control_priority_reason_still_required` (pytest node id, verified passing when recorded)
- `tests/test_tickets_body.py::TestBodyCli::test_cli_append_writes_body` (pytest node id, verified passing when recorded)
- `tests/test_tickets_body.py::TestBodyCli::test_cli_missing_text_exits_nonzero` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/dev-friction/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/dev-friction/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/dev-friction/src/frob/vet/_capability.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE001@src/frob/_cli_parsers/_ticket/_metadata.py, WIRE003@docs/modules/cli.md
