## Done report

Added `tests/test_refactor_corpus.py`: one fixture repo combining every
call-site shape T-3066/T-3105/T-3109 needed real scale to surface --
a function-local import, a `TYPE_CHECKING`-guarded import, a
`try`/`except ImportError`-guarded import, an import nested several
blocks deep, a from-import line naming both a moved and an untouched
symbol, a many-name re-export line (the `gates/__init__.py` shape), a
relative import of the source module, an aliased import, and a
`tickets/<id>/ticket.md` structured evidence citation -- exercised by
one real `run_split` (mirroring T-3086's real target shape: several
symbols moved out of a heavily-imported module, the rest left behind).
The corpus asserts the WHOLE tree stays parseable afterward, not just
the plan's own touched files -- the exact minimum bar T-3105 failed
while reporting `success=True`.

Demonstrated catch of all three known defects (checked locally, never
committed): reverted each fix's exact `_scan.py` diff in turn and
reran the corpus --
  - T-3109's fix reverted: corpus fails with 4 files losing indentation
    ("expected an indented block") -- the identical repro shape.
  - T-3105's fix reverted: corpus fails, caught by
    `verify_import_resolution`'s local-name check (`kept_c` not defined
    in the destination module) -- an even earlier catch than T-3105's
    original `success=True` escape, because a later hardening of that
    check (landed alongside T-3105's own fix) closed that gap too.
  - T-3066's fix reverted (old `ast.walk`-based
    `_shares_line_with_sibling_statement`): corpus fails -- every
    nested import misclassified as semicolon-joined, split reports 1
    unresolved reference and never rewrites the function-local caller.
Each revert-then-restore left the working tree clean; no permanent
change to src/frob/refactor/_scan.py was made or committed by this
ticket (T-3110's scope is test-only).

Fourth defect: none found while building or exercising the corpus
against the current (fixed) code.

Post-apply import check: NOT added to production code -- out of
T-3110's declared scope (tests/test_refactor_corpus.py only). Filed as
a follow-up instead (see Filed below), since `verify_import_resolution`
only checks the plan's own touched-files list, not the whole tree, and
this is exactly the gap T-3105 exploited.

Evidence:
- tests/test_refactor_corpus.py::TestRefactorCorpus::test_split_moves_symbols_across_every_call_site_shape

Filed: a draft ticket (auto-renumbered on land) titled "frob refactor
verbs' Verify phase never checks import breakage outside the plan's own
touched files" -- the unconditional whole-tree post-apply import check
this ticket's brief asked to "consider", scoped to
src/frob/refactor/_commit.py and src/frob/refactor/_verify.py.

Gates: frob check --ticket T-3110 clean (0 errors scoped to
tests/test_refactor_corpus.py; 3 pre-existing-pattern DUP001 notes
waived following test_refactor.py's own precedent for the shared
git-fixture helper shape; 1 FMT001 line-length warning fixed via
`frob fmt`).

### Changed
```
 tests/test_refactor_corpus.py      | 304 +++++++++++++++++++++++++++++++++++++
 tickets/T-3110/ticket.md           |   4 +-
 tickets/T-draft-561192d7/ticket.md |  54 +++++++
 3 files changed, 361 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_refactor_corpus.py::TestRefactorCorpus::test_split_moves_symbols_across_every_call_site_shape` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 10 error(s), None warning(s), None waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, CYCLE001@src/frob/__init__.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bp/tests/unit/verify/test_quarantine.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/unit/test_main_entry.py
