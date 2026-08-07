## Done report

Changed: src/frob/graph/dsl.py::_parse_attrs

`_parse_attrs` computed `leftover = _ATTR_RE.sub("", attr_text).strip()` and
reported any non-empty leftover as a `MalformedDirective`, with no
allowance for a trailing linter-suppression comment (`# noqa: E501` or
similar) sharing the physical line with a `frob:waive`/`frob:tests`/etc
directive. Fix: after the existing `_ATTR_RE.sub` pass, `leftover =
leftover.split("#", 1)[0].strip()` -- cuts a trailing '#'-led tail before
the emptiness check.

Quoted-value safety: `_ATTR_RE` (`(\w+)\s*=\s*"([^"]*)"`) is applied FIRST
via `.sub("", attr_text)`, so any `key="value with #stuff"` attribute --
including one whose value contains a literal `#` -- is fully consumed and
removed from `attr_text` before `leftover` is computed. A '#' that
survives into `leftover` was therefore never inside a quoted value; only a
genuine trailing comment tail (or genuinely malformed leftover text before
one) can reach the `.split("#", 1)` cut. Verified directly:
`reason="uses #hashtag"` with no trailing noqa parses with
`attrs["reason"] == "uses #hashtag"` unchanged (test
`test_hash_inside_quoted_value_is_preserved`).

Evidence:
- tests/unit/graph/test_dsl.py::TestNoqaTail::test_waive_with_trailing_noqa_parses
- tests/unit/graph/test_dsl.py::TestNoqaTail::test_tests_with_trailing_bare_noqa_binds
- tests/unit/graph/test_dsl.py::TestNoqaTail::test_hash_inside_quoted_value_is_preserved

Filed: none

Gates: `uv run pytest tests/unit/graph/test_dsl.py tests/test_graph.py -q`
-- 265 passed (combined with T-0313's tests, same run/file). `uv run ruff
check` and `ruff check` (both PATH and project-pinned) clean on
src/frob/graph/dsl.py and tests/unit/graph/test_dsl.py. `uv run ruff
format --check` clean after one auto-format pass. `uv run ty check` clean.
`uv run frob check --only coverage` -- 0 errors, 0 warnings (COV001=0).
`uv run frob check --delta` after `make coverage` -- `0/0 new` violations.
`git diff main --diff-filter=D --stat` empty (deletion-filter clean).
