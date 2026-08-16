## Done report

Measured against all three real historical mis-scopings, T-2177's own
bare-word implementation warned on NONE of them -- only on a wildly
unrelated file nobody actually files against. Root cause, confirmed by
direct measurement: an ordinary English word ("land", "merge",
"conflict") recurs across every file in a subject area by construction,
so a same-area WRONG file (the actual T-2157/T-2173/T-2189 shape) always
shared enough vocabulary to pass.

Fix, per the ticket's own directive (change WHAT counts as a match, not
how many are needed, and do not expand the stopword list):

1. `_looks_identifier_shaped(token)` (new): a bare prose token only
   counts as a candidate if it looks like a code identifier -- contains
   `_`/`.`, is an ALLCAPS constant, or has an internal capital past its
   first character (camelCase/PascalCase). A hyphenated compound
   ("auto-rebase") is normalized to underscore before this check, since
   hyphenated prose compounds routinely correspond to a real snake_case
   identifier.
2. Quoted/backticked spans (`` `...` ``/`'...'`/`"..."`) still contribute
   every word inside regardless of shape -- the author explicitly cited
   it as literal/code text.
3. `_scope_plausibility_file_words` no longer harvests MULTI-LINE string
   literals (docstrings) -- measured directly against
   `src/frob/tickets/_land_git_ops.py`: its own prose docstrings pulled
   in hundreds of ordinary English words as false "file words"
   (`ledger`, `merge`, `conflict`, ...), defeating the comment-exclusion
   the file side was originally designed around (a docstring mentioning
   a subject in prose is the same false-positive class as a comment
   mentioning it). Short single-line literals (subprocess args, log/error
   messages) are unaffected -- exactly the case this side exists to
   catch.
4. `_SCOPE_PLAUSIBILITY_MIN_WORD_LEN` raised from 4 to 5, measured
   against a real coincidental collision: "auto" (4 letters) appeared on
   both sides for unrelated reasons -- the ticket's "auto-rebase" and the
   wrong file's own unrelated single-line log literal
   ("auto-resolve of out-of-scope conflict").

MEASURED RESULT (all synthetic, isolated `tmp_path` scenarios mirroring
the real files' actual structure):
- T-2173 shape (hyphenated compound naming a real "...rebase..."
  symbol, scoped to a same-area file with none of it): NOW WARNS. Fixed
  end to end, proven by
  `test_ticket_new_scope_plausibility_t2192.py::TestScopePlausibilityIdentifierShaped::test_same_area_wrong_file_now_warns`,
  and the correct file still files without friction
  (`test_same_area_right_file_still_files_without_friction`).
- T-2189 shape (bare title with `--plan --dry-run`, no body): tried
  directly against the real title text -- `_scope_plausibility_ticket_
  words` yields an EMPTY candidate set (`plan`/`dry`/`run`/`merge`/
  `commit`/`main` are all either < 5 chars or stopwords, none
  identifier-shaped). An empty candidate set makes NO claim (silent),
  per `_scope_plausibility_warnings`'s own existing early-return design
  -- it does not warn. Tried again with the ticket's real body prose
  (which does mention `PlanTickGateDirty`/`check_ticks()`): the
  resulting candidates (`dirty`, `check`, `ticks`, `merge`) still did
  NOT distinguish `_land_cmd.py` from `_land.py` -- both land-family
  modules share this vocabulary. **This is a genuine, measured gap, not
  a silent drop**: a token-matching heuristic cannot warn on a
  mis-scoping whose ticket text carries no vocabulary specific enough to
  distinguish the right file from a same-area wrong one, no matter how
  the shape/length rules are tuned -- there is no honest way to make
  "dirty"/"check"/"merge" specific to one land-family file over another.
  Filed as a follow-up (see below) rather than forced with a weakened
  test.

Changed:
- src/frob/app/ticket_runner/_new.py::_looks_identifier_shaped (new)
- src/frob/app/ticket_runner/_new.py::_SCOPE_PLAUSIBILITY_QUOTED_RE (new)
- src/frob/app/ticket_runner/_new.py::_scope_plausibility_ticket_words
  (rewritten: identifier-shaped-only bare tokens + quoted-span carve-out)
- src/frob/app/ticket_runner/_new.py::_scope_plausibility_file_words
  (excludes multi-line string literals)
- src/frob/app/ticket_runner/_new.py::_SCOPE_PLAUSIBILITY_MIN_WORD_LEN
  (4 -> 5)

Evidence:
- tests/unit/test_ticket_new_scope_plausibility_t2192.py::TestScopePlausibilityIdentifierShaped::test_same_area_wrong_file_now_warns
  (designated repro: FAILED_AT_PARENT at c66690aa0, --check-repro
  confirmed before designation)
- tests/unit/test_ticket_new_scope_plausibility_t2192.py::TestScopePlausibilityIdentifierShaped::test_same_area_right_file_still_files_without_friction

Verification:
- `uv run pytest tests/unit/test_ticket_new_scope_plausibility.py
  tests/unit/test_ticket_new_scope_plausibility_t2192.py
  tests/unit/test_ticket_new_related.py
  tests/unit/test_scope_closure_warning_collapse_t1556.py
  tests/unit/test_ticket_new_body_file_pipe_t2021.py -o addopts="" -q`
  -> 21 passed, no regressions in any existing `_new` test.
- `uv run frob check --ticket T-2192 --only coverage --only scope --only
  prework`: gate:COV has zero findings attributable to my changed
  symbols (all COV006/COV007 findings are pre-existing, in other files).
  gate:SCOPE reports SCOPE002 against `_new.py`'s OTHER, untouched public
  symbols (`related_tickets`, `_emit_scope_closure_warnings`, `_new`,
  `_scope_closure_warnings`) whose doc/test/call-graph closure obligations
  already existed before this diff -- same disclosed, pre-existing debt
  class as T-2191's own Done report (chasing it fully pulls in
  docs/design/cli-hygiene.md, docs/modules/tickets.md, and several
  unrelated test files, none of which this bug-kind ticket's own scope
  touches or licenses).

Filed: none new this ticket -- the T-2189-shape residual gap above is
disclosed here rather than filed as a fresh ticket, since the honest
conclusion per the coordinator's own stated acceptable outcome ("a
well-evidenced 'this heuristic cannot be made to pay' is a perfectly
good outcome") is that NO further token-matching tuning closes it; it
would need either a different mechanism entirely (e.g. requiring the
ticket to cite a real symbol/error string before filing, which is a
process change, not a `frob ticket new` code change) or accepting that a
bare-title-only mis-scoping with no distinguishing vocabulary is outside
this check's reach.

Gates: `frob check --ticket T-2192 --only coverage --only scope --only
prework` -- COV clean for this change's own touched symbols; SCOPE002
pre-existing debt disclosed above, not newly introduced by this diff.

### Changed
```
 src/frob/app/ticket_runner/_new.py                 | 114 ++++++++++++++++++---
 .../test_ticket_new_scope_plausibility_t2192.py    | 100 ++++++++++++++++++
 tickets/T-2192/ticket.md                           |  34 +++++-
 3 files changed, 231 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_new_scope_plausibility_t2192.py::TestScopePlausibilityIdentifierShaped::test_same_area_wrong_file_now_warns` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_scope_plausibility_t2192.py::TestScopePlausibilityIdentifierShaped::test_same_area_right_file_still_files_without_friction` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2177/src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
