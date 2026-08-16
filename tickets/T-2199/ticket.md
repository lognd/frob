---
id: T-2199
title: 'promote moves attachment FILES but leaves the ledger path: field pointing
  at the vanished draft directory, so pre-promotion attachments become unresolvable'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_draft_finalize.py
- tests/unit/test_draft_finalize_attachments.py
evidence_scope:
- tests/system/test_cli_ticket_promote.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_draft_finalize_attachments.py
  reason: new unit test file to hold the bug/2199 repro + regression evidence for
    finalize_draft's attachment path relocation
  actor: logan
  at: '2026-08-16'
evidence:
- tests/unit/test_draft_finalize_attachments.py::TestFinalizeDraftRelocatesAttachmentRecords::test_attachment_path_follows_the_rename
- tests/unit/test_draft_finalize_attachments.py::TestFinalizeDraftRelocatesAttachmentRecords::test_sha256_is_reverified_at_the_new_location
- tests/system/test_cli_ticket_promote.py::TestPromoteCLI::test_promotes_a_draft_carrying_evidence_and_done_report
- tests/system/test_cli_ticket_promote.py::TestPromoteCLI::test_promoting_an_already_final_id_is_a_no_op
designated_repro_test: tests/unit/test_draft_finalize_attachments.py::TestFinalizeDraftRelocatesAttachmentRecords::test_attachment_path_follows_the_rename
acceptance:
- text: 'Measured on T-2195, which carries its own internal control. Its ledger records
    three attachments: paths 01 and 02 read ''T-draft-0bd874ac/attachments/...'' while
    path 03 reads ''T-2195/attachments/...''. All three FILES live under tickets/T-2195/attachments/
    and tickets/T-draft-0bd874ac/ no longer exists. Attachments 01 and 02 were recorded
    BEFORE promote; 03 after. So promote relocates the files and rewrites nothing
    already recorded. This produces 3 COV004 errors on the unscoped floor. This test
    MUST fail against current main.'
  evidence:
  - tests/unit/test_draft_finalize_attachments.py::TestFinalizeDraftRelocatesAttachmentRecords::test_attachment_path_follows_the_rename
- text: 'Rewrite the attachment records from the ticket''s own STRUCTURED attachment
    list during promote -- the path, and re-verify the recorded sha256 against the
    file at its new location so a move that corrupts or loses a file fails loudly
    rather than silently pointing somewhere valid-looking. Do NOT text-substitute
    the old id across the ticket file: attachment paths are structured data with a
    known shape, and a blind string replace would also hit prose that legitimately
    cites the draft id historically.'
  evidence:
  - tests/unit/test_draft_finalize_attachments.py::TestFinalizeDraftRelocatesAttachmentRecords::test_attachment_path_follows_the_rename
- text: Do NOT fix this by leaving the draft directory in place so the old paths keep
    resolving -- that reintroduces the stranded-draft class (T-2197) and leaves two
    directories claiming the same attachments. The record must follow the file, not
    the reverse. Note attachment 03 already demonstrates the correct output form,
    so the fix has a working reference implementation in the same file.
  evidence:
  - tests/unit/test_draft_finalize_attachments.py::TestFinalizeDraftRelocatesAttachmentRecords::test_attachment_path_follows_the_rename
threat: null
component: null
anchor: false
anchor_reason: null
---
