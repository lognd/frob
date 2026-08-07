## Done report

Audited every non-done-report free-text ledger entry point named in this
ticket for the T-1536 marker-lookalike-corruption class. Found and fixed
three vulnerable body-splice paths, all now routed through
sanitize_narrative_for_ledger:

- new_ticket (ticket new --body-file): _ticket_from_spec sanitizes
  spec.body before it becomes ticket.body.
- drop_ticket (ticket drop --reason/--reason-file): the appended
  "## Drop reason" line now sanitizes reason before splicing.
- record_failure (ticket fail): the appended "## Failure log" line now
  sanitizes entry.summary before splicing.

Audited and confirmed SAFE (no fix needed): ticket new --acceptance-file
(AcceptanceCriterion.text), scope --reason-file (ScopeChangeEntry.reason),
accept --reason (AcceptanceAmendmentEntry.reason/new_text), review
--findings-file (ReviewEntry.findings) -- all four route through
structured Pydantic frontmatter fields, never raw body prose. yaml.safe_dump
always either prefixes a marker-lookalike line with its own "key: " text
or indents it under a multi-line block scalar, so it can never round-trip
as a literal `^<!-- ticket:T-#### -->` line matching _LEDGER_MARKER_RE --
verified empirically (a bare "<!-- ticket:T-0001 -->" string value dumps
as "reason: <!-- ticket:T-0001 -->", not a standalone matching line).

_land_finalize.py/_land_verify.py also write ticket.body directly, but
only via programmatic id-rewrite/claims-block substitution on EXISTING
body text (renumber_one's reference rewrite, land's captured-claims
recap) -- neither ingests new caller-authored free text, so neither is
in this vulnerability class.

Added a marker-lookalike regression test for each of the three fixed
paths (new_ticket, drop_ticket, record_failure), each proving a
lookalike line survives as legible text but never as a real
_LEDGER_MARKER_RE match, and that the ticket round-trips through
load_queue afterward with no phantom ticket id.

### Changed
```
 docs/design/ledger-v2.md                   |  21 ++--
 docs/modules/cli.md                        |  12 +++
 docs/modules/tickets.md                    |  18 +++-
 src/frob/_cli_parsers/_ticket/_progress.py |   9 ++
 src/frob/app/_config_external.py           |   2 +
 src/frob/app/config.py                     |   5 +
 src/frob/app/ticket_runner/__init__.py     |   2 +-
 src/frob/app/ticket_runner/_query.py       |  21 +++-
 src/frob/tickets/_store.py                 |  40 +++----
 tests/test_ticket_land.py                  |  32 ++++++
 tests/test_tickets.py                      |  22 ++++
 tests/test_tickets_collision.py            |  17 +++
 tests/test_tickets_migration.py            |  63 ++++++++++-
 tests/test_tickets_velocity.py             |  20 +++-
 tickets.md                                 | 161 ++++++++++++++++++++++++++++-
 15 files changed, 402 insertions(+), 43 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestNewTicket::test_marker_lookalike_body_line_is_defused` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestFailureLog::test_marker_lookalike_summary_line_is_defused` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestDropTicket::test_marker_lookalike_reason_line_is_defused` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 1051 warning(s), 784 waived
- error-findings: none (measured, zero errors)
