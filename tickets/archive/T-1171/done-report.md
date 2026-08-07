## Done report

One cohesive family per land, per T-1152's precedent: extracted the
done-report/review/drop/attach family (mutate_labels, brief_ticket,
compose_done_report/_capture_done_report_claims/set_done_report,
record_failure, _resolve_review_commit/record_review/has_approved_
review_for_commit, drop_ticket, and the attach/_attachment_bytes/
_next_attachment_path/_record_attachment quartet) out of
src/frob/tickets/__init__.py into a new src/frob/tickets/_reporting.py
(__init__.py: 1266 -> ~640 lines). Verbatim moves: every frob:ticket/
frob:doc/frob:tests directive carried unchanged, public surface
re-exported from __init__ via explicit imports, zero caller-visible
behavior change. `_load_one`/`_load_ticket_and_queue` stayed in
__init__ per the ticket's own guidance (still depended on as bare
package attributes via `from frob.tickets import _load_one` elsewhere
in _land.py/_evidence.py/app/ticket_runner/_lifecycle.py) -- _reporting.py
late-imports both the same way _evidence.py/_setters.py already do.
Repointed docs/modules/tickets.md's frob:describes anchors and the
tests/*.py frob:tests directives that named the old __init__.py path,
added a `frob:ticket T-1171` edge to TestMutateLabels (COV002) and
extended scope to tests/test_tickets_organization.py, and carried a
DUP001 waiver for a split-induced false-positive template match against
an unrelated frob.vet._capability TS helper.

The _land.py half of T-1171's scope (4973 lines, still needing its own
preflight/merge-splice/verify/sweep split) was NOT touched -- filed as
a draft residue ticket per the playbook's per-family-per-land guidance;
its own size likely warrants a multi-ticket series of its own rather
than one land.

### Changed
```
 tickets.md | 78 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 76 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_tickets_organization.py::TestMutateLabels::test_add_and_remove_labels` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestMutateLabels::test_empty_call_is_error` (pytest node id, verified passing when recorded)
- `tests/test_tickets_brief.py::TestBriefTicket::test_composes_full_briefing` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestComposeDoneReport::test_composes_all_three_sections` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestComposeDoneReport::test_strips_duplicate_leading_heading_from_why` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestSetDoneReport::test_composes_and_writes_atomically` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestSetDoneReport::test_caller_never_touches_markdown` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestArchive::test_blocked_by_archived_ticket_resolves_closed` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestFailureLog::test_appends_creates_section` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestDropTicket::test_drops_queued_ticket_with_reason` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestAttach::test_file_source_copies_and_records_sha256` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestRecordReview::test_appends_approve_entry` (pytest node id, verified passing when recorded)
- `tests/test_tickets_review.py::TestHasApprovedReviewForCommit::test_true_only_for_matching_approve` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: 0 error(s), 649 warning(s), 678 waived
- error-findings: none (measured, zero errors)
