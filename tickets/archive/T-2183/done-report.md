## Done report

_directive_ticket_ids_in_diff used to regex-scan every +/- line of the
raw branch diff with no notion of comment position or file type, so a
frob:ticket citation in markdown prose or a python docstring refused a
land exactly like a real passenger comment did (T-1748, T-2189).

Fixed to decide from the file's grammar: the diff is now walked line by
line (_DiffLineTracker/_bucket_directive_lines), tracking each side's
running line number, and a directive occurrence is only bucketed when
_genuine_comment_lines (frob.lang.raw_tree + COMMENT_TYPES, deliberately
NOT the T-0342 docstring-directive walker) places that exact line inside
a real grammar COMMENT node of its own file version -- worktree HEAD
content for an added line, base_ref content (via git show into a temp
file) for a removed line. An unsupported extension (.md) or a
docstring's string-literal content never registers; a genuine
in-language comment still does. Guarded via tree_sitter_extensions()
before calling raw_tree so the routine tickets.md ledger diff every land
touches never trips frob.lang's own unsupported-extension WARNING.

T-1618's deliberate blindness to sibling ledger state and the T-2082
add/remove-count discriminator are both untouched -- this only changes
WHERE a directive is recognised, never WHICH ids are exempt.

Repro-first: committed the three new tests alone against unfixed code
(commit d4130eced), watched two of them genuinely FAIL (markdown-prose
and docstring false positives) while the genuine-comment control test
already passed, then committed the fix separately. Split
_genuine_comment_lines/_directive_ticket_ids_in_diff into smaller
single-purpose helpers afterward to clear ARCH001 (line-count) and
ARCH103 (mixed I/O+branching) findings the first version of the fix
introduced; bound frob:ticket T-2183 on the new test methods for COV002.

Filed: none. The pre-existing DRIFT001 on
src/frob/app/ticket_runner/_land_cmd.py surfaced by frob check is
untouched by this diff (confirmed via git diff main -- that file,
returns empty) and out of this ticket's scope.

### Changed
```
 src/frob/tickets/_land.py                    | 277 +++++++++++++++++++++++++--
 tests/unit/test_land_cross_ticket_leakage.py | 111 +++++++++++
 tickets/T-2183/ticket.md                     |  25 ++-
 3 files changed, 393 insertions(+), 20 deletions(-)
```

### Evidence
- `tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_directive_text_in_markdown_prose_is_not_a_passenger` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_directive_text_in_a_python_docstring_is_not_a_passenger` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_a_genuine_comment_directive_still_reports_that_id` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2183/src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2183, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md, WIRE001@src/frob/tickets/_land.py
