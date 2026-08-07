## Done report

Root cause: _LEDGER_MARKER_RE matches any line of the exact form
"<!-- ticket:T-#### -->" anywhere in tickets.md, including inside a
ticket's own narrative body. A Done-report why-text that happens to
quote another ticket's literal marker verbatim (e.g. describing this
very corruption incident) forges a fake section boundary the next time
the ledger is parsed: _parse_ledger then reads the following span as
that foreign id's frontmatter, finds ordinary prose instead of YAML,
and the whole store refuses to load -- the exact duplicate-T-1315-
anchor shape from the incident. An unbalanced code fence in the same
narrative compounds the damage (the bogus chunk can swallow real
content further down) but the marker-lookalike line is the actual root
cause.

Fix (a): sanitize_narrative_for_ledger (src/frob/tickets/_store.py)
defuses any line that would exactly match the marker pattern by
inserting a space inside the HTML-comment token (<!-- becomes <! --),
keeping the text legible while guaranteeing it can never round-trip as
a real marker. compose_done_report (src/frob/tickets/_reporting.py)
now runs the caller's why text through this sanitizer before splicing
it into the composed Done-report section, so this class of narrative
can never corrupt a neighboring ticket's block again.

Fix (b): write_ticket's single-mode path (the one write path with no
post-write check at all -- write_all/write_archive/splice_ledger
already had _check_ledger_id_integrity) now re-parses its own spliced
output in memory via the new _post_splice_integrity_check before ever
calling atomic_write, and refuses (Err(LedgerIntegrityViolation)) if
the result fails to re-parse or drops any id that was present before
the write. write_ticket was split into a small dispatcher plus
_write_ticket_single_mode to stay under the ARCH001 length threshold
after adding this check.

Regression tests reproduce the exact incident shape: a why narrative
containing a marker-lookalike line plus an unbalanced ```yaml fence
(TestSanitizeNarrativeForLedger, TestComposeDoneReport::test_marker_
lookalike_line_in_why_is_defused), and a direct write_ticket call whose
ticket.body forges a sibling's marker, asserting the write refuses and
the sibling still loads clean afterward (TestWriteTicket).

Deferred, out of scope for this ticket: the same marker-lookalike
defense is not yet applied to other free-text entry points (scope
--reason-file, ticket --body-file, drop --reason, review --findings-
file) -- each goes through a different write path and would need its
own audit. Filing a follow-up.

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
 tickets.md                               | 412 +++++++++++++++++-
 14 files changed, 1531 insertions(+), 388 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_store.py::TestSanitizeNarrativeForLedger::test_defuses_marker_lookalike_line` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestSanitizeNarrativeForLedger::test_unbalanced_fence_around_marker_lookalike_still_defused` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestSanitizeNarrativeForLedger::test_no_marker_lookalike_line_passes_through_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestSanitizeNarrativeForLedger::test_defused_line_no_longer_matches_the_real_marker_pattern` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestWriteTicket::test_marker_lookalike_body_line_refuses_write` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestWriteTicket::test_ordinary_body_still_writes_clean` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestComposeDoneReport::test_marker_lookalike_line_in_why_is_defused` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
