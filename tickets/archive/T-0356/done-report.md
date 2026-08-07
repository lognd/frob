## Done report

Changed:
- src/frob/dup/_legacy_py.py::_harvest_with (grammar-walk fix)
- src/frob/dup/_legacy_py.py::_harvest_with_item (new helper)

Root cause confirmed interactively against the live tree-sitter-python
grammar: for `with open("a") as fh, open("b") as (a, b):`, `with_item`
nodes are NOT direct children of `with_statement` -- they nest one level
down under an intermediate `with_clause` node. The bound name is not a
field on `with_item` at all; it lives on `with_item`'s `value` child
(`as_pattern`), under that node's `alias` field, pointing at an
`as_pattern_target` (which wraps either a plain `identifier` or a
`tuple`/`list` pattern for `with X as (a, b):`).

Fix: `_harvest_with` now walks both with_item-directly-under-with_statement
and with_item-nested-under-with_clause shapes; a new `_harvest_with_item`
helper reads `with_item.value` (`as_pattern`) -> `alias`
(`as_pattern_target`) and hands the target to the existing
`_harvest_pattern` recursive walker, so tuple/list `with ... as (a, b):`
targets are collected too (same mechanism already used for `for`-loop and
assignment targets).

Before: `with open("f") as fh, open("g") as gh:` binding names `fh`/`gh`
were never added to `_collect_locals_py`'s local set (leaked into the
un-renamed alpha-rename token stream).
After: `fh`/`gh` are collected as locals, same as other binding forms.

Updated `tests/unit/test_dup_legacy_py.py::test_collect_locals_py_covers_every_binding_shape`,
which previously asserted the buggy behavior (`"fh" not in locals_`), to
assert the correct behavior (`fh`/`gh` present in the collected local set).

Evidence: tests/unit/test_dup_legacy_py.py::test_collect_locals_py_covers_every_binding_shape
(recorded via `frob ticket evidence`; full `pytest tests/unit/test_dup_legacy_py.py -v`
run: 7 passed). `--cov=frob.dup._legacy_py --cov-branch` on that file: 86%
line, 96 branches (19 partial) -- all pre-existing gaps unrelated to
`_harvest_with`/`_harvest_with_item`, which are both fully exercised.

`ruff check` clean on both changed files, under both `ruff` (PATH) and
`uv run ruff`.

`git diff main --diff-filter=D --stat` empty (no unintended deletions).

Filed: none (no out-of-scope work found).
Gates: not run via `frob check` this pass (targeted pytest + ruff only, per
dispatch instructions); ticket left open for reviewer close per playbook
section 11.4 (review-gated flow).
