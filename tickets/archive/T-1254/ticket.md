---
id: T-1254
title: 'ledger v2: file-per-ticket store backend (ticket.md + done-report.md)'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
blocked_by:
- T-1253
parent: T-1136
tier: ticket
sprint: null
scope:
- src/frob/tickets/_store.py
- src/frob/tickets/_models.py
- src/frob/tickets/_reporting.py
- tests/unit/test_ticket_store.py
- docs/modules/tickets.md
- design/frob.strata
- docs/design/ledger-v2.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: AFFECT001 requires updating storage-internals/public-api doc anchors for
    _store_mode/load_all/write_ticket/write_all/set_done_report changes (v2 backend)
  actor: logan
  at: '2026-07-29'
- op: add
  glob: design/frob.strata
  reason: 'SCOPE001: frob.strata''s tickets_ledger/testsuite interface= attrs and
    a keep-both merge conflict resolution needed editing this file; docs/design/ledger-v2.md
    is this ticket''s own design doc, cited by every new v2 symbol''s frob:doc anchor'
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/design/ledger-v2.md
  reason: 'SCOPE001: frob.strata''s tickets_ledger/testsuite interface= attrs and
    a keep-both merge conflict resolution needed editing this file; docs/design/ledger-v2.md
    is this ticket''s own design doc, cited by every new v2 symbol''s frob:doc anchor'
  actor: logan
  at: '2026-07-29'
evidence:
- tests/unit/test_ticket_store.py::TestV2StoreMode::test_v2_tree_present_is_v2
- tests/unit/test_ticket_store.py::TestV2WriteTicket::test_write_then_load_v2_mode
- tests/unit/test_ticket_store.py::TestV2WriteTicket::test_write_all_v2_prunes_removed_ticket
- tests/unit/test_ticket_store.py::TestSetDoneReport::test_v2_mode_writes_done_report_md_not_body
- tests/unit/test_ticket_store.py::TestV2DoneReport::test_write_then_read_back_byte_for_byte
- tests/unit/test_ticket_store.py::TestV2Attachments::test_attachment_written_under_ticket_dir
- tests/unit/test_ticket_store.py::TestLoadAllAndWriteTicket::test_write_then_load_single_mode
designated_repro_test: null
acceptance:
- text: 'Ledger v2 design (docs/design/ledger-v2.md section 1) needs the actual

    file-per-ticket store backend: `tickets/T-####/ticket.md` (frontmatter +

    body, reusing the existing `_serialize_ticket`/`_parse_ticket_file`

    per-file primitives) plus a NEW `done-report.md` split out of the body,

    plus `_store_mode` gaining a third "v2" detection branch

    (`tickets/*/ticket.md` present). Blocked by the lock-primitive ticket

    since every write here must take the new per-ticket lock, not the

    whole-ledger `ledger_lock`.'
  evidence:
  - tests/unit/test_ticket_store.py::TestV2WriteTicket::test_write_then_load_v2_mode
  - tests/unit/test_ticket_store.py::TestV2WriteTicket::test_write_all_v2_prunes_removed_ticket
- text: 'Do NOT touch `tickets.md`/`_render_ledger`/`splice_ledger` in this

    ticket -- v1 stays fully functional and is the default store mode until

    the separate migration ticket flips the default. This ticket only adds

    the v2 backend as an alternate, detectable mode alongside v1.'
  evidence:
  - tests/unit/test_ticket_store.py::TestLoadAllAndWriteTicket::test_write_then_load_single_mode
- text: 'GIVEN a repo with `tickets/T-0042/ticket.md` present

    WHEN `_store_mode(root)` is called

    THEN it returns "v2" (new third branch, existing single/dir detection

    unchanged for repos without a v2 tree).'
  evidence:
  - tests/unit/test_ticket_store.py::TestV2StoreMode::test_v2_tree_present_is_v2
- text: 'GIVEN a v2-mode ticket

    WHEN its Done report is written

    THEN it is written to `tickets/T-####/done-report.md`, a file distinct

    from `ticket.md`, and reading it back reproduces the same text

    byte-for-byte.'
  evidence:
  - tests/unit/test_ticket_store.py::TestSetDoneReport::test_v2_mode_writes_done_report_md_not_body
  - tests/unit/test_ticket_store.py::TestV2DoneReport::test_write_then_read_back_byte_for_byte
- text: 'GIVEN a v2-mode ticket with attachments

    WHEN an attachment is added

    THEN it is written under `tickets/T-####/attachments/`, resolving the

    open question in design section 8 in favor of the self-contained layout.'
  evidence:
  - tests/unit/test_ticket_store.py::TestV2Attachments::test_attachment_written_under_ticket_dir
threat: null
component: null
---
Ledger v2 design (docs/design/ledger-v2.md section 1) needs the actual
file-per-ticket store backend: `tickets/T-####/ticket.md` (frontmatter +
body, reusing the existing `_serialize_ticket`/`_parse_ticket_file`
per-file primitives) plus a NEW `done-report.md` split out of the body,
plus `_store_mode` gaining a third "v2" detection branch
(`tickets/*/ticket.md` present). Blocked by the lock-primitive ticket
since every write here must take the new per-ticket lock, not the
whole-ledger `ledger_lock`.

Do NOT touch `tickets.md`/`_render_ledger`/`splice_ledger` in this
ticket -- v1 stays fully functional and is the default store mode until
the separate migration ticket flips the default. This ticket only adds
the v2 backend as an alternate, detectable mode alongside v1.

GIVEN a repo with `tickets/T-0042/ticket.md` present
WHEN `_store_mode(root)` is called
THEN it returns "v2" (new third branch, existing single/dir detection
unchanged for repos without a v2 tree).

GIVEN a v2-mode ticket
WHEN its Done report is written
THEN it is written to `tickets/T-####/done-report.md`, a file distinct
from `ticket.md`, and reading it back reproduces the same text
byte-for-byte.

GIVEN a v2-mode ticket with attachments
WHEN an attachment is added
THEN it is written under `tickets/T-####/attachments/`, resolving the
open question in design section 8 in favor of the self-contained layout.