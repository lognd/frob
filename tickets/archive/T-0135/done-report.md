## Done report

Changed:
- src/frob/gates/__init__.py::sys_gate (moved
  `from frob.strata import load_design_ids` from the function's first
  statement to after the `(root/design_dir).is_dir()` opt-in check)
- src/frob/gates/__init__.py::_design_dir (SECOND import site found:
  `_design_dir` -- called as `sys_gate`'s first statement, before the
  same opt-in check -- did its own unconditional
  `from frob.strata import DEFAULT_DESIGN_DIR`. Not mentioned in the
  ticket body, but it is literally the same bug class in the same
  function's control flow, and the ticket's own verify step -- "a bare
  venv running frob check on a tmp fixture repo exits WITHOUT a
  traceback" -- fails without also fixing this: `sys_gate`'s FIRST
  executable statement is `design_dir = _design_dir(root)`, so moving
  only the `load_design_ids` import left this one still unconditional.
  Fixed by replacing the import with a private `_DEFAULT_DESIGN_DIR`
  literal duplicate of `frob.strata._design_load.DEFAULT_DESIGN_DIR`,
  documented as mirroring it, so `_design_dir` never touches
  `frob.strata` for a repo with no design dir either.)
- .github/workflows/ci.yml (removed the T-0135 `continue-on-error` on
  the standalone-install job's "frob check on a tiny fixture repo must
  not crash" step and its pointing comment, per the ticket's exit
  criterion; replaced with a short note on what T-0134/T-0135 fixed)
- tests/test_gates.py::TestSysGate.test_default_design_dir_mirror_stays_in_sync
  (reviewer follow-up: the `_DEFAULT_DESIGN_DIR` mirror literal added
  above is a deliberate duplication with no compiler/linter to keep it
  honest -- this test imports both `frob.gates` and
  `frob.strata.DEFAULT_DESIGN_DIR` INSIDE the test function body, never
  at module level, so collecting `test_gates.py` still never imports
  `frob.strata`, and asserts the two literals are equal so any future
  drift fails a test instead of silently diverging)

Verify (per the ticket's "prove it locally before un-gating CI"):
- `uv build --wheel` + `uv venv /tmp/frob-standalone-venv` + `uv pip
  install` the wheel (no native extras) + `frob --help`: exit 0.
- Design-less fixture (`git init`, one `.py` file, no `design/` dir):
  `frob check` exit 1 (legitimate TEST006 "no coverage stamp" gate
  failure only), zero SYS violations, NO
  "Traceback (most recent call last):" in the output.
- Design-having fixture (`design/m.strata` present, native extension
  absent in that venv): `frob check` exit 1, output includes
  `SYS004: design/m.strata failed to load (The strata_core native
  extension is not installed ...)` -- the typed T-0134 degrade, not a
  crash -- and still NO traceback.
- Both fixtures and the venv were removed after verification (not
  committed).

Evidence:
- tests/test_gates.py::TestSysGate::test_no_design_dir_never_imports_frob_strata
- tests/test_gates.py::TestSysGate::test_design_dir_degrades_with_typed_error_on_native_extension_missing
- tests/test_gates.py::TestSysGate::test_default_design_dir_mirror_stays_in_sync
- Full suite (real numbers, `uv run pytest tests/test_gates.py -q`):
  all green.
- Full strata+gates+lang_strata suite together (`uv run pytest
  tests/test_gates.py tests/unit/strata/ tests/unit/test_lang_strata.py
  -q`): all green (no failures).
- `frob test --base main`: python exit=0 (touched-set selection
  covering both this ticket's and T-0134's changes together).
- `uv run ty check`: All checks passed.
- `uv run ruff check` / `ruff format --check .`: clean.

Filed: none.

Gates: `frob check --ticket T-0135` (re-run after honest re-scoping and
`frob ticket sweep T-0135`) is NOT clean end-to-end -- 7 errors, not 0:
one pre-existing `DOC001` (docs/guides/install.md, from T-0133's merge,
untouched here) plus SIX `SCOPE001` errors covering
`src/frob/strata/_design_load.py`, `_errors.py`, `_facts.py`,
`_parse.py`, and their two test files
(`tests/unit/strata/test_facts.py`, `test_parse.py`). Cause: same
worktree-sharing effect named in T-0134's Done report, from the other
direction -- T-0135's scope-gate diff-scan sees T-0134's uncommitted
files (now narrowly and honestly scoped to T-0134, not the previous
over-broad `src/frob/strata/**` that used to swallow this silently) and
correctly flags them as outside T-0135's own scope
(`src/frob/gates/__init__.py`, `tests/test_gates.py`,
`.github/workflows/ci.yml`, `tickets.md`). Real cross-ticket file
visibility from two uncommitted sibling tickets in one worktree, not a
false positive, and it resolves once either ticket is committed/closed.
All findings on T-0135's own files remain zero-unwaived; the 22 waived
findings and the COV002 informational entries (symbols covered by this
ticket's or T-0134's own open scope) are the only other output.
