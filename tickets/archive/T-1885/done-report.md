## Done report

Root cause (corrected per coordinator relay -- read before trusting my
earlier framing): this was NEITHER an abort NOR a swallowed crash. It was
a SILENTLY MISATTRIBUTED failure. `scan_evidence_citations`/`scan_
registry_citations` build valid `RewriteOp`s and `apply_plan` writes them
correctly -- the rewrite itself succeeds. One phase later, `verify_
import_resolution` `ast.parse`s every touched path with no extension
filter; a `tickets/<id>/ticket.md` or `docs/design/registry/*.yaml`
raises a real `SyntaxError` on ordinary prose/YAML content (observed:
"leading zeros in decimal integer literals are not permitted" on a
`T-0001`-shaped id). That `SyntaxError` is caught cleanly -- no crash --
and reported as `VerifyOutcome(passed=False, ...)`, which correctly
triggers `run_refactor`'s normal rollback. The transaction machinery
behaved exactly as designed; the bug is that Verify checked the wrong
thing for a non-Python file, and the resulting report gave the operator
no way to tell "genuinely broken" from "checked something it should
never have checked." T-1546's evidence carrier and T-1200's registry
carrier were therefore silently non-functional through the real
`run_refactor` path whenever they produced a hit -- confirmed by
reproduction (the new end-to-end test), not assumed.

Two-part fix, per the coordinator's explicit direction that the
extension filter alone is necessary but not sufficient:

1. `verify_import_resolution` (src/frob/refactor/_verify.py) filters
   `touched_files` to `.py` before the parse loop, so a non-Python
   carrier never reaches `ast.parse`.
2. `VerifyOutcome` (src/frob/refactor/_models.py) gains a new `skipped:
   tuple[str, ...] = ()` field: every touched path a check did NOT
   analyse because it is outside that check's own domain, disclosed
   DISTINCTLY from `passed` in both directions -- a skip is never folded
   into "checked and clean" (which is what would have re-created the
   exact conflation this bug's root cause depended on: an unanalysed
   input reported the same as a genuinely-verified one) nor into
   "checked and broken." `verify_import_resolution` populates `skipped`
   on every return path, and the `detail` string always mentions the
   skipped count when nonzero. `src/frob/refactor/_cli.py`'s two report
   renderers (`_render_split_chunk`/`_render_run_refactor_report`, the
   plain-text disclosure surfaces) now print a `(N skipped)` suffix per
   verify-outcome line whenever `skipped` is nonempty.

Checked T-1664 ("Semantic checks must report UNRESOLVED, never silently
pass when they cannot analyse") for existing vocabulary to reuse before
inventing anything: T-1664 is itself still `planned`, blocked on T-1663,
and scoped at the `frob check` gate-result-model layer (`src/frob/
gates/**`) -- it has not landed any model-level UNRESOLVED/DEGRADED
vocabulary yet for this ticket to adopt. `VerifyOutcome.skipped` is
deliberately scoped narrower and additive (a disclosure tuple, not a new
enum state) rather than pre-empting T-1664's own eventual design; it does
not touch `passed`'s existing bool contract, so every existing caller
(`_split.py`'s own `VerifyOutcome` construction, the CLI renderers, every
existing test) is unaffected without any change on their part.

Tests (tests/test_refactor.py, scope widened via `frob ticket scope
--add` for `_models.py`/`_cli.py`/`tests/test_refactor.py`/`docs/
commands/refactor.md`, each with an explicit `--reason`):
- TestVerify.test_import_resolution_skips_non_python_touched_file --
  unit-level: a ticket.md is skipped, not parsed, and the outcome's
  `skipped` tuple names it.
- TestVerify.test_import_resolution_still_catches_syntax_error_in_py_
  file_among_non_py -- a genuinely broken .py file among a mixed touched
  set still fails AND the non-.py file is still disclosed as skipped
  (skipped is orthogonal to passed, not just a happy-path field).
- TestRunRefactor.test_run_refactor_does_not_roll_back_on_ticket_md_
  evidence_carrier -- full end-to-end repro with a MIXED touched-file set
  (one real .py rename plus the ticket.md evidence carrier it rewrites):
  a real ticket's structured evidence citation now rewrites and commits
  successfully, AND the import_resolution VerifyOutcome discloses the
  ticket.md as skipped. This is the exact combination the coordinator
  flagged as the gap every prior test missed (a unit test on the filter
  alone would have passed before this bug too, since no prior test drove
  a mixed .py + non-.py touched set through the real pipeline).

Also updated a stale in-code comment (TestRunRefactor.test_per_ticket_
evidence_rewrite_routes_through_replace_evidence's docstring) that
referenced T-1885 as an open, unrelated gap -- it now points at the new
end-to-end regression test.

Priority note: agreeing with the coordinator that "medium" understated
this -- two shipped features (T-1546, T-1200) were silently disabled
through their real end-to-end path, invisible to every pre-existing
test because none of them exercised a mixed .py + non-.py touched set
through `run_refactor` itself.

### Changed
```
 tickets/T-1885/done-report.md | 62 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-1885/ticket.md      | 38 ++++++++++++++++++++++++--
 2 files changed, 98 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_refactor.py::TestVerify::test_import_resolution_skips_non_python_touched_file` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestVerify::test_import_resolution_still_catches_syntax_error_in_py_file_among_non_py` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestRunRefactor::test_run_refactor_does_not_roll_back_on_ticket_md_evidence_carrier` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 1 error(s), 778 warning(s), 694 waived
- error-findings: ARCH001@src/frob/refactor/_verify.py
