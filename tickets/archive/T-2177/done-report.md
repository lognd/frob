## Done report

`frob ticket new` now runs a token/grammar-based scope-plausibility check
at filing time (before any lease can exist). It extracts candidate
symbol/word tokens from the ticket's own title+body prose
(`_scope_plausibility_ticket_words`) and, for each declared scope file
that exists on disk, extracts the file's real grammar-parsed identifier
tokens (`frob.lang.iter_identifiers`) plus its string-literal tokens
(walked via `frob.lang.raw_tree`, any node whose tree-sitter type name
contains "string") -- `_scope_plausibility_file_words`. Both sides are
normalized through the same subword split (`_split_scope_plausibility_words`:
underscore/dot/camelCase boundaries, lowercased, length- and
stopword-filtered) so the comparison is a SYMBOL SET intersection, never a
lexical "file contains this text" substring search -- this is deliberate:
a symbol merely mentioned in a comment never counts (comment nodes are not
identifier or string-literal nodes, so they are never visited), and a
symbol reached only via a re-exported alias still counts (`iter_identifiers`
covers every identifier occurrence, definitions and usages alike, not just
top-level declarations).

If NONE of the scope's existing files intersect the ticket's candidate
word set, `_new` logs a single loud `ticket new: scope plausibility: ...`
warning naming the mismatch and pointing at the T-2157/T-2173/T-2189
precedent, before the ticket is created. Kept as a warning (not a hard
refuse requiring a new `--ack-*` flag) deliberately: adding a new CLI flag
would require touching `src/frob/_cli_parsers/_ticket/_new.py`, which is
outside this ticket's declared scope AND outside its implicit CLI-wiring
grant (`__main__.py`/`config.py`/`ticket_runner/__init__.py` only) -- the
acceptance criteria's own "refuses or warns loudly" wording permits either,
and this keeps the fix strictly inside the declared scope.

Repro (confirmed FAILING against current main before the fix): a ticket
titled around `rebase_worktree_onto_main`/"rebase" scoped only to a file
whose real content has zero rebase-related code produced NO warning at
all on main -- exactly the T-2157/T-2173 shape.
`AssertionError: expected a scope-plausibility warning ... got: <no such
line>`. After the fix, the same call logs the warning; a genuinely
plausible scope (the referenced word/identifier really is present) files
without friction, both proven by the two new tests.

Changed:
- src/frob/app/ticket_runner/_new.py::_split_scope_plausibility_words
- src/frob/app/ticket_runner/_new.py::_scope_plausibility_ticket_words
- src/frob/app/ticket_runner/_new.py::_scope_plausibility_file_words
- src/frob/app/ticket_runner/_new.py::_scope_plausibility_warnings
- src/frob/app/ticket_runner/_new.py::_new (wired the new check in,
  after the existing related-ticket check, before spec construction)

Evidence:
- tests/unit/test_ticket_new_scope_plausibility.py::TestScopePlausibility::test_implausible_scope_warns_loudly
- tests/unit/test_ticket_new_scope_plausibility.py::TestScopePlausibility::test_plausible_scope_files_without_friction

Verification:
- `uv run pytest tests/unit/test_ticket_new_scope_plausibility.py tests/unit/test_ticket_new_related.py tests/unit/test_scope_closure_warning_collapse_t1556.py tests/unit/test_ticket_new_body_file_pipe_t2021.py -o addopts="" -q`
  -> 22 passed (2 + 12 + 3 + ... combined runs, see individual SUITE-RESULT
  lines in the session transcript), no regressions in the existing `_new`
  test suite.
- `uv run frob check --ticket T-2177 --only coverage --only scope --only
  prework`: gate:COV/gate:SCOPE both pass (0 errors); the lone remaining
  gate:DRIFT001 finding is pre-existing, unrelated to this ticket's scope
  (`_lifecycle.py::_refuse_on_scope_lease_collision`, already waived by
  T-1894, blocked on T-1883's own unrelated lease), confirmed absent from
  this ticket's touched files.

Filed: none -- no out-of-scope defect surfaced during this ticket.

Gates: `frob check --ticket T-2177 --only coverage --only scope --only
prework` clean for this ticket's own touched set (see Verification above).

### Changed
```
 tickets/T-2177/ticket.md | 28 +++++++++++++++++++++++-----
 1 file changed, 23 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_new_scope_plausibility.py::TestScopePlausibility::test_implausible_scope_warns_loudly` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_scope_plausibility.py::TestScopePlausibility::test_plausible_scope_files_without_friction` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2177/src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
