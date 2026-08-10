## Done report

Two pieces, both implemented:

1. CLI WIRING: `frob ticket anchor <id> --set|--clear (--reason TEXT |
--reason-file PATH)` forwards to T-1856's library-level `set_anchor`
(src/frob/tickets/_land.py) -- the same thin-forwarder shape `_priority`/
`_kind` already use. Parser registered in
src/frob/_cli_parsers/_ticket/_metadata.py, wired through
_cli_parsers/_ticket/__init__.py, runner added to
src/frob/app/ticket_runner/_mutate.py and dispatched in
src/frob/app/ticket_runner/__init__.py's command table. `--set`/`--clear`
are a required mutually-exclusive group; `--reason`/`--reason-file` reuse
the T-0737 pattern (`_resolve_anchor_reason`).

2. DOABLE-OUTPUT DESIGN DECISION (the open question in the dispatch
brief): EXCLUDE anchor=True tickets from `doable()`'s default result,
disclose them only via the new `--show-anchors` flag (annotated
`[ANCHOR: <reason>]` at the display layer). Justification, from the
measured evidence in the dispatch brief itself: the coordinator's own
argument for exclusion over pure annotation is that T-1820/T-1831 ALREADY
carried "(WIRE001 follow_up anchor)" in their TITLES -- a human-readable
annotation was already present in the exact listing a coordinator reads
before dispatching, and it was insufficient: two separate waves still
popped the same anchors and burned a full agent slot each rediscovering
"nothing to do here." A stronger, non-title annotation would not obviously
fix what a title-string annotation already failed to fix. Exclusion
removes the ticket from the specific "pop the top of doable" path that
caused the repeated cost, while `--show-anchors` keeps it fully visible,
auditable, and dispatchable-by-id for anyone who deliberately asks -- nothing
about the ticket's own state, priority, or lease eligibility changes
(verified directly, `test_anchor_remains_queued_and_lease_eligible_either_way`).
This is the "excluded from plain doable, shown under --show-anchors"
middle option the coordinator's message offered as an alternative to
outright removal from the queue -- I did not choose bare annotation
because the evidence in this exact ticket disproves it as sufficient on
its own, and did not choose permanent invisibility because that would
make an anchor's own existence undiscoverable without reading tickets.md
directly.

VERIFIED, per the coordinator's explicit MUST NOT and follow-up
instructions: T-1820, T-1831, and T-1778 (`grep "^anchor:"` against each
ticket.md on main) all already carry `anchor: true` -- someone set the
marker on all three before this ticket landed (not by this Done report;
confirmed via direct file read, no `set_anchor` call was needed or made
here). The filter (`doable()`'s `show_anchors` param keying on
`Ticket.anchor`, never kind/title/state) works correctly against real
data as a result: all three are excluded from the default `doable`
listing today.

Evidence: 6 real tests in tests/unit/test_ticket_anchor_cli.py --
TestAnchorCli (3: set/clear/reason-required, driving the real CLI runner
`_anchor` against a real git+ticket-store fixture) and
TestDoableAnchorDisclosure (3: exclusion by default, inclusion+annotation
with show_anchors=True, and the no-state-side-effect assertion), using
`doable()` directly against an in-memory `TicketQueue` (the same style
tests/test_tickets_priority.py already uses for `doable()`-level
assertions).

NOT done in this pass (residue, no new ticket needed -- captured here
per the coordinator's own framing): no NEW `frob:tests` doc coverage was
added for `doable()`'s pre-existing docstring beyond the frob:tests
directives already on the two new tests here; `doable`'s own module-
level frob:doc anchor (docs/modules/tickets.md, if any) was not
independently re-verified for drift beyond what `frob check --only
coverage --ticket T-1867` already reported clean.

### Changed
```
 rapid-debt.jsonl                           |   1 +
 src/frob/_cli_parsers/_ticket/__init__.py  |   4 +
 src/frob/_cli_parsers/_ticket/_metadata.py |  46 ++++++++
 src/frob/_cli_parsers/_ticket/_query.py    |  10 ++
 src/frob/app/config.py                     |  11 ++
 src/frob/app/ticket_runner/__init__.py     |   4 +
 src/frob/app/ticket_runner/_land_cmd.py    |  80 ++++++++++++--
 src/frob/app/ticket_runner/_mutate.py      |  59 ++++++++++
 src/frob/app/ticket_runner/_query.py       |  14 ++-
 src/frob/tickets/_doable.py                |  21 +++-
 tests/test_ticket_work_and_land_finish.py  |  66 ++++++++++++
 tests/unit/test_ticket_anchor_cli.py       | 167 +++++++++++++++++++++++++++++
 tickets/T-1867/ticket.md                   |  21 ++++
 tickets/T-1913/done-report.md              |  73 +++++++++++++
 tickets/T-1913/ticket.md                   |  15 ++-
 15 files changed, 578 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_anchor_cli.py::TestAnchorCli::test_set_anchor_via_cli` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_anchor_cli.py::TestAnchorCli::test_clear_anchor_via_cli` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_anchor_cli.py::TestAnchorCli::test_requires_reason` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_anchor_cli.py::TestDoableAnchorDisclosure::test_anchor_excluded_from_default_doable` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_anchor_cli.py::TestDoableAnchorDisclosure::test_anchor_included_and_annotated_with_show_anchors` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_anchor_cli.py::TestDoableAnchorDisclosure::test_anchor_remains_queued_and_lease_eligible_either_way` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 10 error(s), 1028 warning(s), 699 waived
- error-findings: AFFECT001@src/frob/tickets/_doable.py, DOC007@src/frob/app/ticket_runner/_mutate.py, DOC007@tests/unit/test_ticket_anchor_cli.py, DRIFT002@src/frob/app/ticket_runner/_mutate.py, DRIFT002@tests/unit/test_ticket_anchor_cli.py, PRE001@tickets/T-1867, REG002@docs/design/registry/check-coverage.yaml, SELFAUDIT001@design, WIRE001@src/frob/_cli_parsers/_ticket/_metadata.py, WIRE001@src/frob/_cli_parsers/_ticket/_query.py
