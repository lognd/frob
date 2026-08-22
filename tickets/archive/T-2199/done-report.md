## Done report

Measured on T-2195: two attachment records recorded before `promote`
still cited the vanished draft directory (`T-draft-0bd874ac/attachments/
...`) while their FILES had already been relocated to
`tickets/T-2195/attachments/` by `renumber_one`/`renumber_one_v2` --
`finalize_draft` never rewrote the ticket's own `attachments` list, only
code/ledger prose references to the id.

Repro: tests/unit/test_draft_finalize_attachments.py, committed alone,
observed FAILING against the pre-fix code
(AssertionError: relocated.path == 'T-draft-.../attachments/01-x.png',
expected the final id's prefix) -- pasted in this ticket's own thread.

Fix: `_relocate_attachment_records` (src/frob/tickets/_draft_finalize.py)
runs after `renumber_one` succeeds in both `finalize_draft` and
`finalize_draft_for_land`. It rewrites each `<old_id>/attachments/...`
Attachment.path to `<new_id>/attachments/...` and RE-VERIFIES the
recorded sha256 against the file at the new path, failing loudly
(Err(TicketError.WriteFailed)) if the file is missing or corrupted. This
is a structured rewrite of the known Attachment.path shape, never a
lexical string substitution -- it does not touch the ticket's prose
citations of the old draft id.

Does NOT retroactively repair T-2195's own already-corrupted attachment
records on main (those 3 COV004 errors pre-date this fix and remain on
the unscoped floor) -- this fix only prevents the defect for future
promotions, per the ticket's own scope (src/frob/tickets/
_draft_finalize.py only).

Evidence:
- tests/unit/test_draft_finalize_attachments.py::TestFinalizeDraftRelocatesAttachmentRecords::test_attachment_path_follows_the_rename
- tests/unit/test_draft_finalize_attachments.py::TestFinalizeDraftRelocatesAttachmentRecords::test_sha256_is_reverified_at_the_new_location
- tests/system/test_cli_ticket_promote.py::TestPromoteCLI::test_promotes_a_draft_carrying_evidence_and_done_report (regression, still green)
- tests/system/test_cli_ticket_promote.py::TestPromoteCLI::test_promoting_an_already_final_id_is_a_no_op (regression, still green)

Filed: none (no out-of-scope work found beyond what T-2199's own scope
already covers)

Gates: `frob check --only gates-fast --ticket T-2199` shows 0 NEW errors
introduced by this change -- the 3 COV004 errors present are T-2195's own
pre-existing historical records (predate this fix, out of scope) and the
SCOPE001/TICK004/DOC011/DRIFT001/TEST010 findings are unrelated
repo-wide floor debt from concurrent series work / other tickets'
landed code, confirmed by `git diff main --stat` attribution.
`frob check --land-parity` reports 2 unrelated E501 findings in
src/frob/app/ticket_runner/_land_cmd.py and src/frob/lang/_nodes.py --
both pre-existing from T-2195's just-landed merge, neither touched by
this ticket's scope.

### Changed
```
 src/frob/tickets/_draft_finalize.py           |  96 ++++++++++++++++++-
 tests/unit/test_draft_finalize_attachments.py | 131 ++++++++++++++++++++++++++
 tickets/T-1696/ticket.md                      |   5 +-
 tickets/T-2199/ticket.md                      |  19 +++-
 4 files changed, 246 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_draft_finalize_attachments.py::TestFinalizeDraftRelocatesAttachmentRecords::test_attachment_path_follows_the_rename` (pytest node id, verified passing when recorded)
- `tests/unit/test_draft_finalize_attachments.py::TestFinalizeDraftRelocatesAttachmentRecords::test_sha256_is_reverified_at_the_new_location` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_ticket_promote.py::TestPromoteCLI::test_promotes_a_draft_carrying_evidence_and_done_report` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_ticket_promote.py::TestPromoteCLI::test_promoting_an_already_final_id_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1696/src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/t-1696/src/frob/lang/_nodes.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, SELFAUDIT001@design, TEST010@tests/test_lang.py, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
