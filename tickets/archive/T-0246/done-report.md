## Done report

Reproduced first: `perf_rules` on a nested `for x in a: for y in b: if f(x)
== g(y):` join returned no PERF003 finding before the fix -- confirmed via
a standalone repro script, matching the ticket's exact `f(x) == g(y)`
shape. Also confirmed (via `git stash`) that a synthetic sibling-loop
attribute-access case (`for waiver in candidates: ...` / `for waiver in
candidates: assert waiver.src == waiver.dst`) already fires PERF003
*before* this change too -- that's a pre-existing, narrower FP class than
the 4 named in T-0161's Done report (those 4 real sites don't reduce to
the same base-identifier-adjacent-to-`==` shape my synthetic case does)
and is unrelated to and unaffected by this ticket's call-paren change.

Fix: `_operand_names` now also unwinds one level of call parens
(`f(x)`/`g(y)`), symmetric with the existing subscript unwind
(`a[i-1]`/`b[j-1]`). `_bracket_identifiers` gained a `brackets` parameter
(default `("[", "]")`, unchanged for existing callers) so the same
depth-tracked walk serves both bracket kinds instead of duplicating it for
parens. `_operand_names` itself was simplified to check `tokens[start]`
directly against `]`/`[`/`)`/`(` rather than pre-computing a single
`closer`/`opener` value keyed off `step` -- behaviorally identical for the
existing bracket case, and what makes adding the paren case a two-line
diff instead of a second near-duplicate branch tree. Attribute access
(`.`) is untouched -- the T-0161 narrowing stays exactly as narrow as
before.

Changed:
- src/frob/perf/_rules.py::_operand_names (unwinds call parens, one level)
- src/frob/perf/_rules.py::_bracket_identifiers (parameterized on
  `brackets`, reused for both `[]` and `()`)

Evidence (fresh `pytest --collect-only`, both new node ids confirmed
collected, `tests/test_perf.py: 28 tests collected`):
- tests/test_perf.py::test_perf003_fires_on_call_operand_join
- tests/test_perf.py::test_perf003_call_operand_join_stays_narrow_no_recursive_unwind

`uv run pytest tests/test_perf.py -q`: 28 passed (was 23 before this
ticket's + T-0230's new tests). Every pre-existing PERF003 test
(`test_perf003_does_not_fire_on_sibling_comprehensions`,
`test_perf003_does_not_fire_on_sibling_statement_loops`,
`test_perf003_fires_on_nested_join_with_intervening_statement`,
`test_perf003_does_not_fire_on_single_loop`) still passes unchanged.
`uv run ruff check` / `uv run ruff format --check` on
`src/frob/perf/_rules.py tests/test_perf.py`: clean under both.
`uv run ty check src/frob/perf/_rules.py`: All checks passed.

False-positive check (T-0161/T-0283 regression guard, same run as
T-0230's): `uv run frob check --only perf` on frob's own tree reports
`0 errors, 0 warnings, 24 waived` both before and after this change --
including the `src/frob/vet/_typosquat.py:26` waived
"algorithm-inherent edit-distance DP nested scan" PERF003 site, which is
exactly the subscript-join shape this change's sibling logic touches, and
it stays waived at the same count, not newly fired or newly silent.

Deletion-filter clean: `git diff main --diff-filter=D --stat` empty.

Filed: none.
Gates: `frob check --only perf` clean (0/0/24 waived, unchanged from
baseline).
