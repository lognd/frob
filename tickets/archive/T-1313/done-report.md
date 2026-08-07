## Done report

Changed: none (evidence-only close)

Investigation: this ticket's body names two symbols at the 0.0% priority
tier: src/frob/__main__.py::_SuggestingArgumentParser.error and
src/frob/__main__.py::main. Both already carry `frob:tests` directives in
the source pointing at tests/unit/test_main_entry.py -- checked whether
those tests actually exercise real behavior before writing anything new.

- `main`: covered by TestMainSigint (SIGINT during dispatch prints a
  clean message + exits 130, not a raw traceback) and
  TestMainUnhandledException (an unhandled exception during dispatch is
  logged with exc_info and exits 1) -- both call main() directly and
  assert on real stdout/stderr/exit-code behavior.
- `_SuggestingArgumentParser.error`: covered by TestDidYouMean, which
  calls `parser.parse_args([...])` with a genuinely bad subcommand/flag,
  catches the resulting SystemExit, and asserts the actual "(did you
  mean: X?)" suggestion text landed in stderr -- this is the .error()
  override's real behavior, not a mock.

Ran the full file standalone: uv run pytest tests/unit/test_main_entry.py
-p no:cacheprovider -n0 -q -- all 10 pass. Also ran the scope's other two
test files (tests/test_gitio.py, tests/test_doctor.py: 37 tests combined)
-- all pass, confirming the rest of the root package (gitio.py, tomlio.py,
excludes.py, doctor.py) also has an existing, passing test surface; not
individually sampled symbol-by-symbol beyond this.

`frob check --ticket T-1313 --only test` in this worktree: 0 errors, 6
warnings, none TEST005 (TEST005 not computable here -- no coverage stamp
in this fresh worktree, TEST006 fires instead; playbook sec 6b makes
coverage stamping coordinator-only). No 0.0%-tier symbol here is
confirmed dead -- both are live entry points (main() is the literal CLI
entry point in pyproject's console_scripts; .error() is the argparse
override wired into every subparser) with real assertions already
exercising them, so acceptance[1]'s dead-code routing does not apply
(nothing to route). Binding acceptance[0] on the strength of this
verification plus the pre-existing frob:tests directives, not a fresh
full-package TEST005 recount (which this worktree cannot produce).

Evidence:
- tests/unit/test_main_entry.py::TestDidYouMean::test_unknown_subcommand_suggests_closest
- tests/unit/test_main_entry.py::TestMainSigint::test_keyboard_interrupt_prints_clean_message_and_exits_130
- tests/unit/test_main_entry.py::TestMainUnhandledException::test_unhandled_exception_prints_clean_message_and_exits_1

Filed: none

Gates: uv run frob check --ticket T-1313 --only test -- 0 errors, 6
warnings (none TEST005), 3 pre-existing waived warnings unrelated to this
ticket.

### Changed
```
 tickets.md | 436 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++----
 1 file changed, 411 insertions(+), 25 deletions(-)
```

### Evidence
- `tests/unit/test_main_entry.py::TestDidYouMean::test_unknown_subcommand_suggests_closest` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestMainSigint::test_keyboard_interrupt_prints_clean_message_and_exits_130` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestMainUnhandledException::test_unhandled_exception_prints_clean_message_and_exits_1` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 7 error(s), 463 warning(s), 684 waived
- error-findings: ARCH001@src/frob/refactor/_scan.py, ARCH001@src/frob/tickets/_land_finalize.py, OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py, RENDER001@src/frob/refactor/_cli.py, SELFAUDIT001@design, TICK003@tickets.md
