## Done report

T-1232's own two named follow-up sub-items (gate-gap class 6) are
resolved:

Sub-item 1 (ticket-id prose vs ledger): built as DOC011.
docstatus_gate (src/frob/gates/_doclink_docanchor.py) now also scans
every docs/**/*.md file (fenced/inline code spans blanked first, same
posture as DOC008's link scan) for T-####/T-draft-<hex> mentions and
flags any that do not resolve to a real ticket, active or archived
(_doc011_known_ticket_ids reads frob.tickets._store.load_all/
load_archive). Deliberately does NOT attempt the harder half (a
mention whose state contradicts the prose) -- that needs sentence-
level parsing of the surrounding claim, out of scope here.

Shipped at WARN, not ERROR: the first live run against this repo's
own docs tree found 10 genuine pre-existing stale citations (mostly
T-draft-<hex> ids that finalized to a real T-#### long ago, one true
orphan T-0104, one likely-intentional example T-9999), entirely
outside this ticket's declared scope to fix. A follow-up ticket
(T-1542, renumbers at land) tracks fixing those citations
and promoting DOC011 to ERROR once the list is empty.

Sub-item 2 (index completeness): INVESTIGATED, not built as proposed.
doclink_gate (DOC001) already treats a doc as non-orphaned via direct
index links, transitive link chains through other docs, frob:describes
anchors, or frob:doc edges -- strictly broader than the sub-item's
proposed "named in docs/index.md's own link inventory" check, which
would be a narrower, stricter rule that could false-positive on a
legitimately deep-linked doc DOC001 already tolerates. Concluded this
sub-item is subsumed by DOC001, not a genuinely distinct gap; recorded
in docs/audits/docs-staleness-2026-07-29.md rather than building
redundant code, per the ticket's own explicit "worth checking...
before building a new rule" framing.

Registered CHK-GATE-DOC011 in docs/design/registry/check-coverage.yaml
(gate_rule_total 286 -> 287) and "DOC011" in _KNOWN_GATE_RULES
(src/frob/gates/_waive.py) -- required scope additions beyond the
ticket's original three files (tests/unit/gates/test_doc011.py, new
test home since tests/test_gates.py is leased by T-1205;
src/frob/gates/_waive.py, mechanical rule-id registration).

Disclosed gap: docs/modules/gates.md's rule catalog table still needs
a DOC011 row (same table DOC009/DOC010 already appear in) -- could not
add it here, also leased by T-1205 for this ticket's whole duration.
docstatus_gate carries a frob:waive AFFECT001 with that exact reason;
the follow-up ticket (T-1542) now also covers this file.

### Changed
```
 design/frob.strata                       | 711 ++++++++++++++++---------------
 docs/audits/docs-staleness-2026-07-29.md |  32 +-
 docs/design/ledger-v2.md                 |  10 +
 docs/design/registry/check-coverage.yaml |   6 +-
 docs/modules/tickets.md                  |  18 +
 src/frob/gates/_doclink_docanchor.py     | 125 +++++-
 src/frob/gates/_waive.py                 |   4 +
 src/frob/tickets/_reporting.py           |  17 +-
 src/frob/tickets/_setters.py             |  91 +++-
 src/frob/tickets/_store.py               | 130 +++++-
 tests/test_tickets_velocity.py           | 129 +++++-
 tests/unit/gates/test_doc011.py          | 111 +++++
 tests/unit/test_ticket_store.py          | 123 ++++++
 tickets.md                               | 423 +++++++++++++++++-
 14 files changed, 1542 insertions(+), 388 deletions(-)
```

### Evidence
- `tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_unknown_ticket_id_in_prose_fires_doc011` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_known_active_ticket_id_passes` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_id_inside_fenced_code_block_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_id_inside_inline_code_span_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_no_ledger_at_all_still_flags_prose_mentions` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_duplicate_mention_on_one_line_reported_once` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 1 error(s), 264 warning(s), 789 waived
- error-findings: PRE001@tickets/T-1486
