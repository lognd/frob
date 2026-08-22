## Done report

Fixed src/frob/gates/_mutation_evidence.py's three unanchored, whole-
body-scanning directive regexes (_BUG002_WAIVER_RE, _NO_BEHAVIOR_
CHANGE_RE, _MUST_STILL_PASS_RE) treating a ticket body's PROSE
DISCUSSION of a directive as if it were a live DECLARATION. Measured
self-referential instance: tickets/T-2215/ticket.md:56 describes the
escape-hatch shape (backtick-quoted `frob:waive BUG003 reason="..."`
as an example while explaining a gap) and matched _BUG002_WAIVER_RE,
self-waiving.

Fix: added _quoted_char_ranges(body), a grammar-based helper using
tree_sitter_language_pack's "markdown" + "markdown_inline" grammars
(the same loading mechanism frob.lang itself uses) to compute the
character-offset ranges of a fenced code block, indented code block,
blockquote, or inline code span -- markdown's own real grammatical
distinction between "quoted as an example" and "asserted as prose".
markdown's own two-stage grammar design required parsing block
structure first (fenced/indented code blocks, blockquotes resolve
here) then re-parsing each opaque "inline" leaf node's raw text with
the separate markdown_inline grammar (code spans only resolve there).
Byte offsets are converted to character offsets via a bytes.decode
slice since tree-sitter operates in UTF-8 bytes and Python's re
module in characters.

Each of the three directive-extraction functions now iterates matches
via .finditer (instead of .search/.findall) and skips any match whose
start() falls inside a quoted range, via the shared _is_quoted
predicate; the first (or, for must-still-pass, every) non-quoted match
is accepted exactly as before.

SCOPING FOLLOWED, per the filing agent's own survey: did NOT touch
_WAIVE_DOC004_RE/_WAIVE_DOC006_RE (src/frob/gates/_docptr.py) -- they
use a bounded lookbehind window, not a whole-body scan, and were
explicitly excluded. Did NOT reach for frob.lang raw_tree/
COMMENT_TYPES -- confirmed empirically it requires a real filesystem
path with a registered grammar and returns nothing useful for an
in-memory ticket.body string; used the same tree_sitter_language_pack
loading primitive frob.lang itself uses instead, staying inside
src/frob/gates/_mutation_evidence.py's own scope with no frob.lang
change. Did NOT narrow via column/line-position heuristics or a
literal '...' exclusion -- both explicitly ruled out in the ticket
body as fixing one instance while leaving the class.

Repro: tests/test_gates_mutation_evidence.py::TestBug002Waiver::
test_directive_inside_inline_code_span_does_not_suppress (plus 7
sibling repro cases across all three functions -- fenced code block,
blockquote, and the equivalent shapes for no-behavior-change and
must-still-pass), watched FAIL against pre-fix code (8 of 17 new
tests failed; the pre-existing 9 continued to pass) by temporarily
restoring HEAD's version of the file and re-running. Fix committed
separately.

MUST-STILL-PASS CONTROLS (the critical half, per this ticket's own
explicit requirement -- a fix that stops recognizing real directives
would satisfy the repro while silently disabling the whole escape
hatch): one per function, each combining a quoted example alongside a
genuine declaration in the SAME body, asserting the genuine one is
still recognized and the quoted one is not:
- test_genuine_declared_waiver_still_suppresses (BUG002)
- test_genuine_declared_directive_still_recognized (no-behavior-change)
- test_genuine_directive_alongside_quoted_example_still_extracted
  (must-still-pass, BUG003's own control mechanism)
All pass post-fix.

Verified directly against the REAL, actual tickets/T-2215/ticket.md
file (not a synthetic fixture): `_bug002_waiver_reason` on the loaded
T-2215 ticket now returns None (correctly -- no live waiver), where
pre-fix it would have extracted "..." and self-waived.

pytest tests/test_gates_mutation_evidence.py -o addopts="" -q: 58
passed, 0 failed (was 53 before this ticket's 5 new test classes/
methods).

frob test --base main: python exit=0, 14 outcomes recorded, all green.

frob check --only lint: ty clean; the two remaining ruff-check errors
are in files this ticket did not touch (confirmed via git status).

frob check --only cycle: unmoved at 3 errors, 1 warning (T-2202's
tracked debt), measured before and after.

### Changed
```
 src/frob/gates/_mutation_evidence.py  | 138 ++++++++++++++++++++++++++++--
 tests/test_gates_mutation_evidence.py | 155 ++++++++++++++++++++++++++++++++++
 tickets/T-2218/ticket.md              |  20 ++++-
 3 files changed, 303 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_directive_inside_inline_code_span_does_not_suppress` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_directive_inside_fenced_code_block_does_not_suppress` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_directive_inside_blockquote_does_not_suppress` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_genuine_declared_waiver_still_suppresses` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestNoBehaviorChange::test_directive_inside_inline_code_span_does_not_recognize` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestNoBehaviorChange::test_genuine_declared_directive_still_recognized` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMustStillPassControls::test_directive_inside_fenced_code_block_is_not_extracted` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestMustStillPassControls::test_genuine_directive_alongside_quoted_example_still_extracted` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2218/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2218/tests/test_ticket_work_and_land_finish.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2218, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
