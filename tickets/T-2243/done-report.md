## Done report

Premise check: `git grep -n "retire_unidentifiable_findings|..."` -- N/A here; for
T-2243 the premise check was `git grep` for any existing prose-vs-citation handling
in TICK006's own extraction path, which found none (only T-2218's SEPARATE
BUG003-only `_quoted_char_ranges`) -- the defect genuinely existed unfixed.

Archaeology done before writing any code, per this ticket's own instruction not to
guess: `git show 3a688f28b:tickets/T-2226/done-report.md` (the actual Done-report
commit that produced T-2238) plus `git show 455608775:tickets/T-2238/ticket.md`
(the phantom ticket's own quoted-excerpt body, which the fix engine writes
verbatim from the claim window) together pin down EXACTLY which text triggered
it: "Filed T-draft-76b5731f (high) for the .gitattributes glob fix; acceptance
[3] there is \"T-2226's two still-unresolved T-draft-0bd874ac records are
re-attempted and confirmed relocated once this lands\"." This is NOT inside a
fenced/indented code block or a `>` blockquote -- T-2218's existing
`_quoted_char_ranges` alone does not exclude it. It IS inside a matched ASCII
double-quote pair (an inline echo of a DIFFERENT ticket's own acceptance-criterion
text), the sentence-level counterpart to a blockquote.

Fix: extended the SHARED `_quoted_char_ranges` primitive (home:
`src/frob/gates/_mutation_evidence.py`, T-2218) with a new `_quoted_span_ranges`
delimiter scan (matched ASCII `"` pairs, excluding anything inside a code span so
a stray quote in `` `a "quoted" example` `` can never seed/close a pairing) and a
new `_double_quote_char_ranges` STRICT SUBSET accessor. `_tick006_phantom_ids`
(`src/frob/gates/_tickets_gate.py`) now: (1) checks the "filed" trigger word's own
position against the FULL `_quoted_char_ranges` (replacing T-1700's narrower
`_code_span_mask`/`strip_code_spans`, deleted -- now dead), and (2) checks each
CANDIDATE ID's own position against the NARROWER `_double_quote_char_ranges` only.

The narrower id-side check is deliberate and load-bearing, not an oversight:
applying the FULL quoted-ranges set (code spans included) to the id's own
position regressed T-1700's own settled, already-tested precedent
(`test_backtick_styled_id_in_a_real_claim_still_fires`: an id styled in
backtick code right after plain-prose "Filed:" is still a real, checkable
claim) -- caught by running the FULL existing TestTick006PhantomFiling suite
before finalizing, not just the new fixture. Two pre-existing tests
(`test_phantom_filed_colon_fires`, `test_backtick_styled_id_in_a_real_claim_still_fires`)
broke on the first version of this fix and are the reason the id-check uses
`_double_quote_char_ranges` (double-quote pairs only) rather than
`_quoted_char_ranges` (the full union).

Repro discipline: `test_prose_quoting_another_tickets_criterion_does_not_fire`
(using the real T-2226 text shape) committed alone first (3c476ec85), confirmed
FAILED_AT_PARENT via `frob ticket evidence T-2243 --check-repro ... --base-ref
3c476ec85`, then the fix committed separately (4ff754360).

Must-still-pass control: `test_genuine_dangling_citation_outside_any_quote_still_fires`
-- two ids near "filed", neither quoted, both must fire (proves the fix narrows
WHICH ids count, not "stop after the first id"). Also re-ran the FULL existing
`TestTick006PhantomFiling` class (14 tests, all pass) and the full
`TestQuotedRanges` class (9 tests, all pass) plus the entire `tests/test_gates.py`
file (732 tests, all pass) to confirm no other TICK006/BUG003 consumer regressed.

Validated directly against the real, un-paraphrased T-2226 Done-report text
(`git show 3a688f28b:tickets/T-2226/done-report.md`) via `_tick006_phantom_ids`:
before the fix it returned `T-draft-0bd874ac` among its candidates (the exact
phantom that became T-2238); after the fix it does not, while the two genuine
citations (`T-draft-76b5731f`, `T-draft-141cad63`) both still appear.

No hand-written second markdown scanner: the double-quote pairing lives inside
`_mutation_evidence.py` next to (and reusing the same parse walk as)
`_quoted_char_ranges` itself -- one home, extended, for both consumers (BUG003
and TICK006).

Did NOT retroactively clean up the 3 still-queued phantom tickets (T-2113,
T-2228, T-2238) -- out of this ticket's declared scope per its own "Do NOT fix
it this way" list.

Changed:
  src/frob/gates/_mutation_evidence.py::_quoted_span_ranges (new)
  src/frob/gates/_mutation_evidence.py::_double_quote_char_ranges (new)
  src/frob/gates/_mutation_evidence.py::_quoted_and_double_quote_char_ranges (new, shared walk)
  src/frob/gates/_mutation_evidence.py::_quoted_char_ranges (now delegates to the shared walk)
  src/frob/gates/_tickets_gate.py::_tick006_phantom_ids (rewired onto the shared primitive)
  src/frob/gates/_tickets_gate.py::_code_span_mask (deleted -- dead after the rewire)
  tests/test_gates.py::TestTick006PhantomFiling (+2 tests)
  tests/test_gates_mutation_evidence.py::TestQuotedRanges (+2 tests)

Evidence:
  tests/test_gates.py::TestTick006PhantomFiling::test_prose_quoting_another_tickets_criterion_does_not_fire (accepts 0, 3)
  tests/test_gates.py::TestTick006PhantomFiling::test_genuine_dangling_citation_outside_any_quote_still_fires (accepts 1)
  tests/test_gates.py::TestTick006PhantomFiling::test_code_spanned_filed_claim_does_not_fire (accepts 2)
  tests/test_gates_mutation_evidence.py::TestQuotedRanges::test_double_quoted_span_quoted (accepts 3)
  Full runs: tests/test_gates.py (732 passed), tests/test_gates_mutation_evidence.py (60 passed)

Filed: none -- no out-of-scope work discovered.

Gates: gate:FMT/gate:PRE/gate:SCOPE/gate:WIRE/gate:static(ty) all clean for this
ticket (`frob check --only <group> --ticket T-2243`, re-run after `frob ticket
sweep T-2243` refreshed the stale pre-work sweep post-scope-widen and `ruff
format` fixed line wrapping). The only unscoped ERROR-level findings anywhere in
the tree (ruff E501 in src/frob/lang/_nodes.py, F541 in
tests/test_ticket_work_and_land_finish.py; the same 3 pre-existing DRIFT001
digest-moved findings this session has seen on every ticket; 2 unrelated COV001/
COV004 findings in scripts/fleet_status.py and a stale T-2195 attachment sha) are
PRE-EXISTING on `main` itself after a fresh `git merge main` -- `git diff main
--stat` for every one of those files is empty; none touched by this ticket.
`git diff main --diff-filter=D --stat` is empty (no deletions) after the merge.

### Changed
```
 src/frob/gates/_mutation_evidence.py  | 110 +++++++++++++++++++++++++++++++---
 src/frob/gates/_tickets_gate.py       |  74 +++++++++++++----------
 tests/test_gates.py                   |  75 ++++++++++++++++++++---
 tests/test_gates_mutation_evidence.py |  40 +++++++++++++
 tickets/T-2243/ticket.md              |  81 +++++++++++++++++++++++--
 5 files changed, 328 insertions(+), 52 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTick006PhantomFiling::test_prose_quoting_another_tickets_criterion_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick006PhantomFiling::test_genuine_dangling_citation_outside_any_quote_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick006PhantomFiling::test_code_spanned_filed_claim_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestQuotedRanges::test_double_quoted_span_quoted` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1335, COV003@tickets/T-1353, COV003@tickets/T-1362, COV003@tickets/T-1363, COV003@tickets/T-1373, COV003@tickets/T-1397, COV003@tickets/T-1426, COV003@tickets/T-1433, COV003@tickets/T-1526, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DUP001@src/frob/gates/_mutation_evidence.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2243/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2243/tests/test_ticket_work_and_land_finish.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
