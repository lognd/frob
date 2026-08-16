---
id: T-2239
title: T-1433's .gitattributes CRLF-suppression glob does not match v2-mode nested
  attachment paths, breaking COV004 sha verification
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
- .gitattributes
- tests/unit/test_gitattributes_merge.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression::test_v2_nested_attachment_survives_checkout_unconverted
- tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression::test_v1_flat_attachment_still_covered
- tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression::test_unrelated_text_file_still_gets_autocrlf_conversion
designated_repro_test: tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression::test_v2_nested_attachment_survives_checkout_unconverted
threat: null
component: null
anchor: false
anchor_reason: null
---
Measured during T-2226 (2026-08-16). T-1433 added `.gitattributes`:

    tickets/attachments/** -text

to stop `core.autocrlf=true` from converting attachment file line endings
on checkout, which breaks COV004's byte-exact sha256 verification. That
glob only matches the OLD v1 flat-attachments layout
(`tickets/attachments/...`). Ledger v2 stores attachments per-ticket
under `tickets/<id>/attachments/...` -- a path shape the glob does not
match at all -- so v2-mode attachment files are still subject to CRLF
conversion on checkout, and their recorded sha256 (computed at attach
time, LF content) silently stops matching the on-disk (CRLF) content the
next time the tree is freshly checked out.

Directly reproduced during T-2226:

    tickets/T-2195/attachments/03-....md   recorded sha256 (LF)   e1de4998...
                                            actual sha256 (CRLF)   21258f4a...
    LF-normalized actual content sha256                            e1de4998...  <- matches recorded

    tickets/T-2197/attachments/01-....md   recorded sha256 (LF)   f5f7da4a...
                                            actual sha256 (CRLF)   4a0c6121...

Both files' PATH fields are already correct (real ticket id, not a stale
draft id) -- these are pure CRLF-driven COV004 false positives, unrelated
to T-2226's draft-attachment-path defect. This also BLOCKS T-2226's own
backfill from safely relocating the two remaining T-draft-0bd874ac ->
T-2195 attachment records: `_relocate_attachment_records`'s sha reverify
(deliberately, correctly, fails loud rather than blindly rewriting) sees
the same CRLF-corrupted bytes and refuses the write with WriteFailed.

## Acceptance criteria

1. `tickets/<id>/attachments/**` (v2-mode nested shape) is covered by the
   same `-text` CRLF-suppression `.gitattributes` treats the v1 flat
   layout with, verified by a fresh-checkout reproduction test analogous
   to the one above.
2. Existing v2-mode attachments whose recorded sha256 was computed
   against LF content are re-verified/backfilled where correction is
   possible, or reported where the original LF content cannot be
   recovered.
3. T-2226's two still-unresolved `T-draft-0bd874ac` attachment records
   (verified `backfill_stale_draft_attachment_paths` logic, blocked only
   by this CRLF corruption) are re-attempted and confirmed relocated
   once this lands.