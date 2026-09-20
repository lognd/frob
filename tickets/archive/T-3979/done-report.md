## Done report

Fix: `_PROSE_KEY_RE` (src/frob/gates/_docptr.py) now also matches
`old_text`/`new_text`, the two `AcceptanceAmendmentEntry` fields written
by `frob ticket accept --amend/--remove`. `_blank_ticket_reason_fields`
blanks their values in the frontmatter scan before DOC006's prose scan
runs, the same T-3724/T-3843 mechanism already used for `*reason`/
`title` keys.

Why old_text/new_text specifically: `old_text` is the sharper case --
`--amend` is the SANCTIONED remedy for a DOC006 violation living in a
criterion's own text, and it is what WRITES the criterion's previous
(violating) wording into `old_text` as a permanent audit record. Before
this fix, re-amending to clear a DOC006 finding only appended another
record carrying the identical violating string -- the no-exit measured
on tickets/T-3976/ticket.md. `old_text` is by construction never live
(its whole purpose is preserving text already superseded by `new_text`),
so it can never be the genuinely-dead-pointer case DOC006 exists for.
`new_text` is blanked for the same reason `title` is: free-text prose
composed at mutation time, becoming `Ticket.acceptance[index].text`
(itself never scanned, for the identical reason), not a doc-pointer
site.

Fields verified against the real ledger (src/frob/tickets/_models.py)
and deliberately NOT added, stated per T-3979's own instruction:
- ScopeChangeEntry.glob, EvidenceChangeEntry.old_node/new_node,
  DesignatedReproChangeEntry.old_value/new_value: real identifiers this
  gate should keep checking (a scope glob is a repo path; a bound
  evidence id is a pytest node id) -- case (a) preserved.
- TriageChangeEntry.old_value/new_value: a single enum/label value
  (priority, kind, component), never composed narrative prose --
  structured data, not the old_text/title class.
- ReviewEntry.findings: a live reviewer's CURRENT assessment, not a
  record of superseded text -- the amendment no-exit does not apply, and
  a reviewer citing a genuinely dead symbol is exactly case (a), which
  must still fire.

Marked-non-pointer decision consulted, not reinvented: tickets/T-3893's
OWNER DECISION explicitly REJECTED a Zig-style @""-style do-not-resolve
sigil, on the grounds that DOC006's existing frob:waive DOC006
reason="..." mechanism is strictly better (carries a reason) for BODY
prose, and the frontmatter-blanking precedent (T-3843, extended here)
already covers the structured-field case a sigil would otherwise be
reached for. No new syntax invented.

tickets/** is NOT blanket-exempted: only two specific, named frontmatter
field keys are blanked, and only inside the frontmatter block -- a
genuinely dead pointer in the ticket BODY, or in any OTHER frontmatter
field, is unaffected and still fires
(test_open_ticket_body_still_flagged_alongside_old_text_and_new_text).

Fixtures (tests/test_docptr_gate.py::TestDoc006OldTextNewTextFieldExclusion):
- test_old_text_field_not_flagged: MUST-STAY-QUIET, old_text.
- test_new_text_field_not_flagged: MUST-STAY-QUIET, new_text.
- test_open_ticket_body_still_flagged_alongside_old_text_and_new_text:
  MUST-FIRE, a dead pointer in the ticket body still fires alongside the
  now-exempt frontmatter fields.
- test_amend_that_removes_a_doc006_violation_leaves_ticket_clean: THE
  NO-EXIT, made checkable -- an amended ticket shaped exactly like
  `frob ticket accept --amend`'s real output (corrected acceptance text,
  new_text matching it, old_text carrying the original violating string
  verbatim) is DOC006-clean end to end.

Evidence:
tests/test_docptr_gate.py::TestDoc006OldTextNewTextFieldExclusion::test_old_text_field_not_flagged
tests/test_docptr_gate.py::TestDoc006OldTextNewTextFieldExclusion::test_new_text_field_not_flagged
tests/test_docptr_gate.py::TestDoc006OldTextNewTextFieldExclusion::test_open_ticket_body_still_flagged_alongside_old_text_and_new_text
tests/test_docptr_gate.py::TestDoc006OldTextNewTextFieldExclusion::test_amend_that_removes_a_doc006_violation_leaves_ticket_clean
tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo

Filed: none.

Gates: `frob test --base main`: exit=0, 23 test(s) recorded stable.
`pytest tests/test_docptr_gate.py`: 89 passed, 0 failed. The CI
acceptance signal
`tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo`
is GREEN with zero offenders (re-run after the fix, confirming T-3976's
old_text finding no longer reproduces against frob's own live repo).
Cleared one pre-existing quarantine finding
(DOC006:tickets/T-3976/ticket.md), which IS the no-exit this ticket
fixes -- filed against T-3979 itself since this fix removes the
underlying cause.

### Changed
```
 src/frob/gates/_docptr.py |  82 +++++++++++++++++++++--
 tests/test_docptr_gate.py | 162 ++++++++++++++++++++++++++++++++++++++++++++++
 tickets/T-3979/ticket.md  |  10 ++-
 3 files changed, 245 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_docptr_gate.py::TestDoc006OldTextNewTextFieldExclusion::test_old_text_field_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006OldTextNewTextFieldExclusion::test_new_text_field_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006OldTextNewTextFieldExclusion::test_open_ticket_body_still_flagged_alongside_old_text_and_new_text` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006OldTextNewTextFieldExclusion::test_amend_that_removes_a_doc006_violation_leaves_ticket_clean` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 4 error(s), 4398 warning(s), 930 waived
- error-findings: ARCH001@src/frob/gates/_docptr.py, DRIFT001@src/frob/xref/__init__.py, LANDPARITY002@src/frob/gates/_docptr.py, SCOPE002@tickets.md
