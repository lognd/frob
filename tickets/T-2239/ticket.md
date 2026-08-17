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
land_commit: null
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

## Done report

T-1433's `.gitattributes` `-text` CRLF-suppression rule only matched the v1
flat attachment layout (`tickets/attachments/**`). Ledger v2 stores
attachments per-ticket under `tickets/<id>/attachments/**`, a path shape the
v1 glob never matches, so v2 attachments were still CRLF-converted on
checkout under `core.autocrlf=true`, desyncing their on-disk sha256 from the
sha256 recorded at attach time (LF content). Extended coverage to the v2
shape (`tickets/*/attachments/** -text`) while keeping the v1 rule intact --
both layouts exist on main today (v1: `tickets/attachments/T-1433/...`, v2:
`tickets/T-2195/attachments/...`, `tickets/T-2197/attachments/...`) and both
are now covered.

Reproduced by writing an LF-terminated file under a v2-shaped path in a
throwaway repo carrying the real `.gitattributes` with `core.autocrlf=true`
set locally on that throwaway repo only, forcing a real checkout-time filter
pass (delete + `git checkout --`, not merely reading the committed blob),
and asserting the sha256 survives unconverted -- fails against the
unfixed `.gitattributes` (FAILED_AT_PARENT, verified via `frob ticket
evidence --check-repro`), passes against the fix.

Also directly re-verified the real end state in this worktree, not just the
test: the two live COV004 attachment-sha findings on main whose ledger path
was already correct (`T-2195/attachments/03-...`, recorded sha `e1de4998...`;
`T-2197/attachments/01-...`, recorded sha `f5f7da4a...`) both had a raw
on-disk (CRLF) sha that did NOT match their recorded sha, while their
LF-normalized content sha DID match -- the exact T-2239 discriminator.
Force-renormalized both (delete + `git checkout --` under the fixed
`.gitattributes`) and confirmed the on-disk sha256 now matches the recorded
sha256 exactly, with `frob check --only coverage` no longer reporting COV004
for either file. The two remaining COV004 findings (`T-2195` attachments 01
and 02, still ledger-pathed at the stale `T-draft-0bd874ac/...`) are T-2226's
separate draft-path defect -- not fixed here, but their disk content was also
renormalized (byte content matches their recorded sha once relocated) so
CRLF corruption no longer blocks T-2226's sha-reverify safety check from
relocating them.

Did not weaken the sha-reverify guard, did not rewrite recorded shas to the
CRLF bytes, did not set `core.autocrlf=false` locally.

## Done report

Changed:
.gitattributes -- widened v1 CRLF-suppression rule to also cover v2 nested attachment layout
tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression -- reproduction + must-still-pass v1 control + negative control

Evidence:
tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression.test_v2_nested_attachment_survives_checkout_unconverted (designated repro, FAILED_AT_PARENT at 85c1cb459)
tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression.test_v1_flat_attachment_still_covered
tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression.test_unrelated_text_file_still_gets_autocrlf_conversion

Filed: none

Gates: frob check --ticket T-2239 clean for this ticket's scope (SCOPE/PREWORK/diff-driven COV002-TODO001/FMT/AFFECT all clean); all other FAIL lines are repo-wide pre-existing state per the check's own scope-note, unrelated to .gitattributes/tests/unit/test_gitattributes_merge.py.

### Changed
```
 .gitattributes                         |   9 ++-
 tests/unit/test_gitattributes_merge.py | 120 +++++++++++++++++++++++++++++++++
 tickets/T-2239/ticket.md               |   8 ++-
 3 files changed, 134 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression::test_v2_nested_attachment_survives_checkout_unconverted` (pytest node id, verified passing when recorded)
- `tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression::test_v1_flat_attachment_still_covered` (pytest node id, verified passing when recorded)
- `tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression::test_unrelated_text_file_still_gets_autocrlf_conversion` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2239/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2239/tests/test_ticket_work_and_land_finish.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2239, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md, WIRE001@tests/unit/test_gitattributes_merge.py
