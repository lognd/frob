## Done report

Changed:
- src/frob/outline/__init__.py::_RUST_EXTS (new)
- src/frob/outline/__init__.py::_OUTLINE_EXTS (extended to include `.rs`)
- tests/conftest.py::rust_sample (new fixture)
- tests/unit/test_outline.py::rust_file (new fixture)
- tests/unit/test_outline.py::test_rust_outline_ok
- tests/unit/test_outline.py::test_rust_outline_functions
- tests/unit/test_outline.py::test_rust_outline_classes
- tests/unit/test_outline.py::test_rust_outline_methods
- tests/unit/test_outline.py::test_rust_outline_as_text

No new adapter module was needed: `outline_file`'s existing symbol-walk
(`_outline_symbols`/`_build_classes`/`_assign_functions`) is already
generic over `SymbolKind` (FUNCTION/METHOD/CLASS/TYPE/CONST), which is
exactly what `frob.lang`'s rust walker (`_walk_rust.py`) produces, so
adding `.rs` to the extension allowlist was sufficient -- mirroring how
`.strata` was wired in for T-0129, drawn from
`frob.lang.supported_extensions()` rather than a bare literal.
`frob.lang.extract_imports` has no rust import walker registered
(`_IMPORT_WALKERS` in `src/frob/lang/_extract.py` only has
python/c/cpp), so rust outlines carry an empty `imports` list; this is
existing frob.lang behavior, not a gap introduced here.

Manually re-verified the exact repro from the ticket body:
`uv run frob outline strata-core/src/parse.rs` now emits a structured
outline (161 symbols, function/impl-method signatures with line numbers)
instead of `OutlineError.UnsupportedLanguage`.

Evidence:
- tests/unit/test_outline.py::test_rust_outline_ok (bound via `frob:tests
  src/frob/outline/__init__.py::outline_file kind="unit"`)
- tests/unit/test_outline.py::test_rust_outline_functions
- tests/unit/test_outline.py::test_rust_outline_classes
- tests/unit/test_outline.py::test_rust_outline_methods
- tests/unit/test_outline.py::test_rust_outline_as_text
- Collected and observed passing: `uv run pytest tests/unit/test_outline.py -q`
  -> 21 passed (16 pre-existing python/cpp/unsupported-language tests +
  5 new rust tests above), confirmed against a fresh
  `pytest --collect-only` pass (21 tests collected).

Filed: none (no out-of-scope work found; see disclosure below for one
item deliberately NOT filed as a new ticket).

Disclosure (not self-expanded): `docs/commands/outline.md`'s "Language
support" section still reads "Python (tree-sitter-python), C/C++
(tree-sitter-cpp)" and is now stale now that `.rs` is supported. That
file is not under this ticket's `scope` (`src/frob/outline/**`,
`tests/**`, `tickets.md`), so it was left untouched rather than
self-expanding scope. `frob check --ticket T-0238` did not flag this as
DRIFT/COV against the touched symbols in this pass, but the prose is
factually stale and should be corrected in a docs-scoped follow-up.

Gates: `frob check --ticket T-0238` clean -- 0 errors, 11 warnings (all
pre-existing, outside this ticket's touched files: TEST005 on
src/frob/testing/_collect.py, PERF004 x2, ARCH001 x7, none touching
src/frob/outline/**, tests/conftest.py, or tests/unit/test_outline.py),
202 waived (pre-existing repo-wide waivers, unrelated to this ticket).
`make coverage` run to completion in foreground beforehand (exit 0,
all suites green) and `--stamp-coverage` re-run so TEST006 (stale
coverage stamp) did not mask the real result.
