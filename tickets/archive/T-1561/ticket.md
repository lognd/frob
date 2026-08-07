---
id: T-1561
title: 'evidence ops cannot reach archived tickets while COV003 still scans them:
  add --archived reach or an unarchive verb'
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_store.py
- src/frob/tickets/_evidence.py
- src/frob/_cli_parsers/_ticket/_closeout.py
- src/frob/app/config.py
- src/frob/app/_config_external.py
- src/frob/app/ticket_runner/_verify.py
- tests/unit/test_ticket_store.py
- tests/test_tickets_evidence_cli.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_store.py
  reason: 'evidence --replace --archived: write_archived_ticket in _store.py (per-ticket
    archive write), replace_evidence archived= param in _evidence.py, --archived CLI
    flag in _closeout.py, AppConfig field + whitelist, runner wiring in _verify.py,
    regression tests + docs'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: 'evidence --replace --archived: write_archived_ticket in _store.py (per-ticket
    archive write), replace_evidence archived= param in _evidence.py, --archived CLI
    flag in _closeout.py, AppConfig field + whitelist, runner wiring in _verify.py,
    regression tests + docs'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout.py
  reason: 'evidence --replace --archived: write_archived_ticket in _store.py (per-ticket
    archive write), replace_evidence archived= param in _evidence.py, --archived CLI
    flag in _closeout.py, AppConfig field + whitelist, runner wiring in _verify.py,
    regression tests + docs'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/app/config.py
  reason: 'evidence --replace --archived: write_archived_ticket in _store.py (per-ticket
    archive write), replace_evidence archived= param in _evidence.py, --archived CLI
    flag in _closeout.py, AppConfig field + whitelist, runner wiring in _verify.py,
    regression tests + docs'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'evidence --replace --archived: write_archived_ticket in _store.py (per-ticket
    archive write), replace_evidence archived= param in _evidence.py, --archived CLI
    flag in _closeout.py, AppConfig field + whitelist, runner wiring in _verify.py,
    regression tests + docs'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: 'evidence --replace --archived: write_archived_ticket in _store.py (per-ticket
    archive write), replace_evidence archived= param in _evidence.py, --archived CLI
    flag in _closeout.py, AppConfig field + whitelist, runner wiring in _verify.py,
    regression tests + docs'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: 'evidence --replace --archived: write_archived_ticket in _store.py (per-ticket
    archive write), replace_evidence archived= param in _evidence.py, --archived CLI
    flag in _closeout.py, AppConfig field + whitelist, runner wiring in _verify.py,
    regression tests + docs'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/test_tickets_evidence_cli.py
  reason: 'evidence --replace --archived: write_archived_ticket in _store.py (per-ticket
    archive write), replace_evidence archived= param in _evidence.py, --archived CLI
    flag in _closeout.py, AppConfig field + whitelist, runner wiring in _verify.py,
    regression tests + docs'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: docs/modules/tickets.md
  reason: 'evidence --replace --archived: write_archived_ticket in _store.py (per-ticket
    archive write), replace_evidence archived= param in _evidence.py, --archived CLI
    flag in _closeout.py, AppConfig field + whitelist, runner wiring in _verify.py,
    regression tests + docs'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: docs/commands/ticket.md
  reason: 'evidence --replace --archived: write_archived_ticket in _store.py (per-ticket
    archive write), replace_evidence archived= param in _evidence.py, --archived CLI
    flag in _closeout.py, AppConfig field + whitelist, runner wiring in _verify.py,
    regression tests + docs'
  actor: logan
  at: '2026-08-05'
- op: remove
  glob: docs/commands/ticket.md
  reason: docs/commands/ticket.md does not exist in this repo; docs/modules/tickets.md
    already carries the full evidence --replace/--archived writeup
  actor: logan
  at: '2026-08-05'
evidence:
- tests/unit/test_ticket_store.py::TestWriteArchivedTicket::test_v2_mode_writes_under_archive_dir
- tests/unit/test_ticket_store.py::TestWriteArchivedTicket::test_single_mode_splices_into_archive_file
- tests/unit/test_ticket_store.py::TestWriteArchivedTicket::test_single_mode_preserves_sibling_archived_ticket
- tests/test_tickets_evidence_cli.py::TestReplaceEvidenceCli::test_cli_replace_archived_reaches_the_archive
- tests/test_tickets_evidence_cli.py::TestReplaceEvidenceCli::test_cli_replace_without_archived_flag_cannot_reach_an_archived_ticket
designated_repro_test: null
acceptance:
- text: GIVEN an archived ticket whose bound evidence id goes stale (test renamed)
    THEN a frob CLI path exists to rebind it (evidence --replace --archived, or ticket
    unarchive) -- the gate never polices records the CLI cannot repair
  evidence:
  - tests/unit/test_ticket_store.py::TestWriteArchivedTicket::test_v2_mode_writes_under_archive_dir
  - tests/unit/test_ticket_store.py::TestWriteArchivedTicket::test_single_mode_splices_into_archive_file
  - tests/unit/test_ticket_store.py::TestWriteArchivedTicket::test_single_mode_preserves_sibling_archived_ticket
  - tests/test_tickets_evidence_cli.py::TestReplaceEvidenceCli::test_cli_replace_archived_reaches_the_archive
  - tests/test_tickets_evidence_cli.py::TestReplaceEvidenceCli::test_cli_replace_without_archived_flag_cannot_reach_an_archived_ticket
threat: null
component: null
---
2026-08-05: COV003 fired on archived T-1269/T-1495 after their bound tests were renamed by wave-4 unwind-semantics work; frob ticket evidence --replace answered NotFound because the store only reads tickets.md. Gate scans the archive, repair tooling does not reach it -- catalogued-is-not-enforced inverse: enforced-but-not-repairable. Coordinator worked around with an exact-string swap in tickets-archive.md.