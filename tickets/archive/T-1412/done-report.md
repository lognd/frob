## Done report

Re-ran `frob check --only docanchor --only doclink --only docblocks` fresh
in a freshly-built worktree (natives rebuilt, graph snapshot cold) rather
than trusting main's possibly-stale cached graph. That surfaced only 6
DOC006 findings, not 5 as re-measured on main pre-worktree, and then only
5 real ones once the graph was fresh: `frob.tickets._evidence._gate_claim_criteria`
resolved cleanly on its own once the snapshot was rebuilt from a clean
worktree -- it was a genuinely real symbol, and the earlier finding against
main was a stale-cache artifact, not a real DOC006.

<!-- frob:waive DOC006 reason="T-1412's own Done report necessarily QUOTES the
unresolvable pointers it classified -- naming them is what a classification
report is. Every citation below is deliberately reproduced verbatim from the
finding it disposes of, so each one re-creates the very DOC006 it documents.
This is inherent to reporting on this rule at all, not drift: the alternative
is a report that cannot say which pointers it judged." -->
Classified the remaining 5:
- (a) genuine stale reference, fixed: tickets.md:8866's
<!-- frob:waive DOC006 reason="T-1412 Done report: this line quotes verbatim the unresolvable pointer it is classifying -- naming the finding is what the report IS, so the citation re-creates the DOC006 it disposes of. Inherent to reporting on this rule, not drift." -->
  `frob.app.ticket_runner._close_cmd.py` mixed dotted-module notation
  with a literal `.py` suffix -- an invalid pointer shape, not a rename.
  Repointed to the real file-path form
  `src/frob/app/ticket_runner/_close_cmd.py`.
<!-- frob:waive DOC006 reason="T-1412 Done report: this line quotes verbatim the unresolvable pointer it is classifying -- naming the finding is what the report IS, so the citation re-creates the DOC006 it disposes of. Inherent to reporting on this rule, not drift." -->
- (b) intentionally future-facing, waived: tickets.md:472 (`frob refactor
  split`, this ticket's own not-yet-built deliverable) and tickets.md:3944
  (`frob.security`, a hedged "e.g. ... or similar" proposed extraction
  target that does not exist because the extraction has not happened).
- (b) intentionally illustrative, waived: tickets.md:4978
<!-- frob:waive DOC006 reason="T-1412 Done report: this line quotes verbatim the unresolvable pointer it is classifying -- naming the finding is what the report IS, so the citation re-creates the DOC006 it disposes of. Inherent to reporting on this rule, not drift." -->
  (`src/demo/__init__.py`, T-1320's own name for a phantom entry that
  a corrupted coverage.xml merge introduced -- the incident note is
  ABOUT that path never having belonged there).
- (c) historical record, NOT fixed here: CHANGELOG.md:1952 references
  `_elaborate.py::_elaborate_module`, a symbol that never existed
  top-level in that module (elaboration was already split across
  `_elaborate_node`/`_elaborate_flow`/etc. when this 0.9.0 entry was
  written) -- a genuine historical-record case per the ticket's own
  disposition rules. I could not apply the waiver: CHANGELOG.md is
  land-owned (T-0731, agent-playbook.md section 4b) and a scaffolded
  pre-commit hook refuses ANY worktree commit that touches it, including
  a comment-only doc waiver. This is a structural gap in the DOC006
  disposition path for CHANGELOG.md specifically -- the file cannot be
  hand-edited (correctly, per T-0731) but `frob ticket land` has no
  mechanism to apply a DOC006 waiver comment on a worktree's behalf
  either, so a legitimate historical-record DOC006 finding in
  CHANGELOG.md currently has no in-worktree path to zero.

Filed T-1413 to fix the structural gap (give land a path to accept a
land-owned-file doc waiver, or exempt CHANGELOG.md from DOC006 the same
way tickets-archive.md already is) rather than working around the guard.

Leaving T-1412 in-progress rather than closing it: the ticket's
acceptance criterion (0 unwaived DOC006 in CHANGELOG.md and tickets.md)
is not met -- 1 finding remains in CHANGELOG.md, blocked on T-1413.

### Changed
```
 tickets.md | 52 +++++++++++++++++++++++++++++++++++++++++++++++++---
 1 file changed, 49 insertions(+), 3 deletions(-)
```

### Evidence
- `cmd:uv run frob check --only docanchor --only doclink --only docblocks exit=0 sha256=5303ea7cf4a3` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 0 error(s), 347 warning(s), 697 waived
- error-findings: none (measured, zero errors)
