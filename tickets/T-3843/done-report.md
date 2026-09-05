## Done report

Extended `_blank_ticket_reason_fields` (T-3724) to also blank a ticket's
YAML frontmatter `title:` value, generalizing `_REASON_KEY_RE` into
`_PROSE_KEY_RE` (now matching `\w*reason` OR `title`). Chose option (b)
from the ticket body: blank every known free-text frontmatter key, not
just `title`, with the prose-vs-structured enumeration of `Ticket`'s
frontmatter fields published in the ticket body and in the helper's own
docstring -- (a) only fixes today's instance and leaves the next prose
key to be rediscovered through a red CI leg; (c) throws away legitimately
checkable structured frontmatter for no benefit, since none of it
currently holds citation-shaped text anyway.

Added a body-level `frob:waive DOC006` comment ahead of this ticket's own
illustrative quote of the measured finding (T-3807's `[check.stack]`
citation), since a ticket BODY pointer must still fire and this one is a
genuine quotation, not a real dangling reference.

Added 9 fixtures: 3 unit-level (`TestBlankTicketReasonFields`, mirroring
the existing reason-key unit tests) covering single-line title blanking,
wrapped-continuation title blanking with line-count preservation, and a
no-regression check that `reason:` blanking is unaffected; 6 gate-level
(`TestDoc006TitleFieldExclusion`) covering the must-stay-quiet cases
(single-line and wrapped title), the must-fire cases (open ticket body,
plain docs/ prose), and the line-number-preservation case (a body
violation below a blanked wrapped title reports its ORIGINAL line
number, not one shifted by the blanking).

Did NOT touch DOC006's docstring/message or weaken body-level checking --
`_blank_ticket_reason_fields` only ever touches the frontmatter block; a
ticket BODY pointer, and ordinary docs/ prose, are unaffected and both
have must-fire fixtures proving it.

Verification: reproduced the failing assertion before the change
(`test_doc004_doc006_zero_against_live_repo` failed with 2 offenders --
T-3807's title and this ticket's own body quote, before the waive comment
was added); after the fix + waive comment, the full
`tests/test_docptr_gate.py` suite (85 tests) passes, and
`--check-repro` confirms the designated repro genuinely
FAILED_AT_PARENT.

Filed: none -- no out-of-scope work discovered.

### Changed
```
 tickets/T-3843/ticket.md | 66 ++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 66 insertions(+)
```

### Evidence
- `tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006TitleFieldExclusion::test_single_line_title_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006TitleFieldExclusion::test_wrapped_title_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006TitleFieldExclusion::test_open_ticket_body_still_flagged_alongside_title` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006TitleFieldExclusion::test_body_violation_below_blanked_title_reports_original_line` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006TitleFieldExclusion::test_docs_prose_pointer_still_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestBlankTicketReasonFields::test_title_value_blanked_key_kept` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestBlankTicketReasonFields::test_wrapped_title_continuation_blanked_line_count_preserved` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestBlankTicketReasonFields::test_reason_key_blanking_not_regressed_by_title_addition` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 1 error(s), 4348 warning(s), 923 waived
- error-findings: PRE001@tickets/T-3843
