## Done report

T-1670's part 2 asked `frob ticket evidence` to "validate the node-id
shape at bind time and reject the pytest ::-separated form" -- but
investigation (recorded in T-1670's own Done report and this ticket's
body) found that literal reading would break correct behavior: real
collected pytest node ids ARE in the `path::Class::method` (2-`::`-
segment) form, `matches_collected` requires an exact match against that
form, and `normalize_evidence_separator` (T-0293) already converts a
dotted 1-`::`-segment id INTO that same 2-segment form for storage.
Rejecting the 2-segment shape would make it impossible to bind evidence
using a real id copied verbatim from `pytest --collect-only` output.

Implemented the narrower, safe half instead (item 1 of this ticket's own
plan): `validate_evidence` now rejects a genuinely malformed 3+-segment
id (e.g. `path::Class::method::extra`) via the new
`_has_excess_separator_segments` helper -- a shape no real pytest node id
or `cmd:` evidence entry ever takes. Checked on the RAW (pre-normalize)
string specifically, because `normalize_evidence_separator` converts a
valid dotted id INTO the 2-segment pytest form, so a post-normalize check
could not tell a legitimate dotted id apart from a genuinely malformed
one that happened to normalize to the same segment count.

Before this fix, a 3+-segment id passed `normalize_evidence_separator`'s
early-return unchanged (its own docstring: "the remainder after :: already
contains its own ::" case), then was only ever caught by
`_check_evidence_resolution` -- and only when a caller supplied a
`collected` set. A bare library `add_evidence(root, id, ids)` call with no
collector (`collected=None`) only WARNS "recorded UNRESOLVED" and proceeds,
so a malformed 3+-segment id could land in `ticket.evidence` completely
unchecked through that path. Now it is rejected at the schema layer
(`MalformedEvidence`) for every caller, collector or not.

Item 2 of the ticket's plan (whether `frob ticket evidence` should hint
the dotted `frob:tests`-directive form of a newly-bound id, to close a
directive-authoring UX gap) is investigated but NOT implemented here --
it is a separate, lower-confidence UX question (does the hint actually
help, where should it print, does it apply to `cmd:` evidence) that
deserves its own scoped ticket rather than folding into this one's
schema-validation fix. Left as a disclosed cut, not silently dropped.

Also re-applied T-1637's evidence rebind (`frob ticket evidence T-1637
--replace ...`) after discovering during this ticket's own gate check
that T-1714's land did NOT actually carry it onto main either --
`frob ticket land`'s squash-apply only splices the LANDING ticket's own
`tickets.md` section forward via `splice_ledger`'s newest-state-per-
section merge; a same-state-rank edit to a DIFFERENT ticket's section
(no state/report-richness change, just an evidence-list value change)
never wins `_newer`'s tiebreak and is silently dropped regardless of
which ticket sponsors the edit. This is a real, structural land-plumbing
gap distinct from T-1714's own fix -- filing a follow-up ticket for it
separately (see Done report closing note) since fixing `splice_ledger`'s
per-section merge itself is out of T-1706's own scope.

Filed T-1721 (renumbers at land) with the structural finding
and a reproduction sketch: `splice_ledger`'s per-section merge compares
state-rank/report-richness only, never raw content, so a same-state-rank
edit to a ticket's section always loses the tiebreak regardless of which
side actually changed. T-1637's evidence rebind is re-applied fresh in
this ticket's own worktree; whether THIS land finally carries it is
unverified until after landing -- will confirm via `git show
main:tickets.md` post-land and report the outcome.

### Changed
```
 tickets.md | 105 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++---
 1 file changed, 100 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestEvidenceValidation::test_validate_evidence_rejects_three_or_more_double_colon_segments` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestEvidenceValidation::test_validate_evidence_accepts_ordinary_two_segment_pytest_form` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 4 error(s), 267 warning(s), 716 waived
- error-findings: AFFECT001@src/frob/tickets/__init__.py, ARCH001@src/frob/tickets/_evidence.py, DOC009@docs/audits/docs-completeness-2026-08-06.md, unresolved-attribute@tests/test_ticket_work_and_land_finish.py
