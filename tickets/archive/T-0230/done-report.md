## Done report

Reproduced first: `perf_rules` on a 5-line `find_all` function with a loop
containing `haystack.index(x)` at line 4 reported `PERF002` at line 1 (the
`def` line) before the fix -- confirmed via a standalone repro script
calling `perf_rules` directly, matching the ticket's lithos/rust reports.

Root cause: `RawSymbol.body_tokens` is a flat, position-free leaf-token
stream by design (`frob.lang._common.leaf_tokens`, whitespace never a
node) -- every PERF00x finding anchored at `symbol.span[0]` because no
per-token line number exists anywhere in the pipeline. Fixing this
properly (a `body_token_lines` parallel array on `RawSymbol`) would touch
every `frob.lang` walker (`_walk_python.py`, `_walk_c.py`,
`_walk_rust.py`, `_walk_typescript.py`, `_walk_strata.py`,
`_common.py::leaf_tokens`) -- outside this ticket's declared scope
(`src/frob/perf/**`, `tests/**`, `tickets.md`). Instead, added a second,
line-aware pass confined entirely to `src/frob/perf/_rules.py`: once the
existing token-stream logic decides a rule FIRES (unchanged), a new
`_source_lines` helper re-reads `file.path` (the same repo-relative/
absolute string `frob.lang._display_path` already hands every other
consumer) and regex-locates the real offending line within the symbol's
span -- `_perf001_line`/`_PERF002_LINE_PATTERN`/`_perf004_line`/
`_EQ_PATTERN` for PERF001/002/004/003 respectively. Falls back to the old
`span[0]` anchor if the file can't be re-read or nothing matches, so
behavior never regresses to a missing/None line.

Changed:
- src/frob/perf/_rules.py::_source_lines (new)
- src/frob/perf/_rules.py::_first_matching_line (new)
- src/frob/perf/_rules.py::_perf001_line (new)
- src/frob/perf/_rules.py::_perf004_line (new)
- src/frob/perf/_rules.py::_python_violations (now anchors each hit at its
  own offending line, not `span[0]`)
- src/frob/perf/_rules.py::_best_effort_violations (same, for TS/rust
  `.includes(`/`.indexOf(`/`.contains(`)
- src/frob/perf/_rules.py::_symbol_violations (threads `lines`/`span_start`
  through; PERF003 now anchors at the `==` line)

Evidence (fresh `pytest --collect-only`, all 5 new node ids confirmed
collected, `tests/test_perf.py: 28 tests collected`):
- tests/test_perf.py::test_perf002_anchors_to_index_call_line_not_def_line
- tests/test_perf.py::test_perf004_anchors_to_sort_call_line_not_def_line
- tests/test_perf.py::test_perf003_anchors_to_equality_line_not_def_line
(plus the 2 T-0246 tests below, same file/run)

`uv run pytest tests/test_perf.py -q`: 28 passed (was 23 before this
ticket's + T-0246's new tests).
`uv run ruff check` / `uv run ruff format --check` on
`src/frob/perf/_rules.py tests/test_perf.py`: clean under both.
`uv run ty check src/frob/perf/_rules.py`: All checks passed.

False-positive check (T-0161/T-0283 regression guard): `uv run frob check
--only perf` on frob's own tree reports the identical `0 errors, 0
warnings, 24 waived` both before (git-stashed) and after this change --
no new PERF findings, waived or otherwise, on frob's own source.

Deletion-filter clean: `git diff main --diff-filter=D --stat` empty.

Filed: none.
Gates: `frob check --only perf` clean (0/0/24 waived, unchanged from
baseline).
