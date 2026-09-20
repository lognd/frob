## Done report

Fixed T-3724: DOC006 was scanning `tickets/<id>/ticket.md` YAML
frontmatter `*reason:` field values (scope_changes[].reason,
staleness_reason, scope_breadth_ack_reason, ...) as pointer-resolution
prose. These are free-text accountability strings written by
`frob ticket scope`/`fail`/`ack` at mutation time, never doc pointers --
a reason mentioning a future config key or nonexistent file tripped the
gate with no clean remedy short of a hand-edit.

Added `_blank_ticket_reason_fields` in src/frob/gates/_docptr.py: for
tracked `tickets/<id>/ticket.md` files, blanks the VALUE of every YAML
frontmatter key ending in `reason` (preserving line count/indentation so
other findings' line numbers stay correct), leaving the ticket BODY
untouched so a real dangling pointer there still fires. Wired into
doc006_gate right after the ticket.md text is read.

Added tests/test_docptr_gate.py::TestDoc006ReasonFieldExclusion with a
positive control both directions: a pointer-shaped span inside a
scope_changes reason does not fire, while an identical span in the same
ticket's BODY still fires.

Documented the exemption in docs/modules/gates.md's DOC006 section and
re-acked doc006_gate's frob:doc reference.

### Changed
```
 tickets/T-3724/done-report.md | 40 ++++++++++++++++++++++++++++++++++++++++
 tickets/T-3724/ticket.md      | 17 +++++++++++++++++
 2 files changed, 57 insertions(+)
```

### Evidence
- `tests/test_docptr_gate.py::TestDoc006ReasonFieldExclusion::test_scope_change_reason_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006ReasonFieldExclusion::test_open_ticket_body_still_flagged_alongside_reason` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestBlankTicketReasonFields::test_non_frontmatter_text_untouched` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestBlankTicketReasonFields::test_empty_text_untouched` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestBlankTicketReasonFields::test_unterminated_frontmatter_untouched` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestBlankTicketReasonFields::test_reason_value_blanked_key_kept` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestBlankTicketReasonFields::test_continuation_indented_more_is_blanked` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestBlankTicketReasonFields::test_blank_line_inside_continuation_also_blanked` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestBlankTicketReasonFields::test_reason_key_on_last_frontmatter_line_no_overrun` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 1 error(s), 4414 warning(s), 919 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json
