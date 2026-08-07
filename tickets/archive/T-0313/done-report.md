## Done report

Changed: src/frob/graph/dsl.py::_resolve_block_srcs (new), src/frob/graph/dsl.py::parse_directives

Root cause: the generic tree-sitter comment path (`frob.lang._extract`)
already block-widens `RawComment.following` correctly via `_block_ends` --
python/rust/C/TS reproductions of "frob:doc then 2 frob:ticket lines above
a def" already bound correctly under that path (confirmed by direct repro
before any fix). The `.strata` walker (`frob.lang._walk_strata`,
out-of-scope for this ticket) is a different, narrower binder:
`_extract_comments` calls `find_following_symbol(span, symbols)` with
`span = (idx+1, idx+1)` -- the comment's OWN single line, never widened to
the block's end line -- so a directive several lines above the symbol,
with other directive lines between it and the symbol, can fail to resolve
`following` even though a directive on the line directly above the symbol
resolves fine. Because the true root cause sits in a walker file outside
this ticket's declared scope (`src/frob/graph/dsl.py` only), the fix is a
scope-respecting compensating mechanism entirely inside `dsl.py`: a new
`_resolve_block_srcs(comments, path)` groups the comments in a `ParsedFile`
into maximal RUNS of line-number-adjacent comments (in reverse/bottom-up
order) and, for any comment whose own `following` is `None`, propagates
the nearest ALREADY-RESOLVED `following` binding from later in the same
unbroken run backward onto it. A comment whose own `following` DOES
resolve is always left as-is (source of truth for its own line); a gap
(non-adjacent line number) breaks the run and falls back to the previous
enclosing/bare-path behavior exactly as before. `parse_directives` now
calls this once per file and looks up each comment's `src` from the
returned dict instead of calling `_enclosing_src` inline per comment.

This fix works language-agnostically (it does not special-case strata) and
is order-independent within a block by construction: verified directly
against a synthetic `ParsedFile` reproducing the narrow-following-window
symptom (`test_narrow_following_window_propagates_backward_through_run`,
following=None on lines 1-2, following='FooNode' resolved only on line 3
-- all three directives bind to `a.strata::FooNode` after the fix). A
genuine gap between comments still correctly fails to propagate
(`test_gap_still_breaks_propagation`). The generic-walker case (python,
already correct before this ticket) is also covered as a standing
regression guard (`test_doc_before_two_ticket_lines_still_binds_via_generic_walker`).

Note for future ticket: the true fix location for `.strata` files
specifically -- widening `find_following_symbol`'s span in
`frob.lang._walk_strata._extract_comments` the way the generic
tree-sitter path already does via `_block_ends` -- is out of this
ticket's scope (`src/frob/lang/**` is not in `scope`). This ticket's
dsl.py-level propagation fixes the observable symptom (COV001 false
positive) for every walker, including strata, without touching lang code,
but a walker-level fix would be the more direct remedy if `frob.lang` is
ever in scope for a follow-up.

Evidence:
- tests/unit/graph/test_dsl.py::TestBlockBinding::test_doc_before_two_ticket_lines_still_binds_via_generic_walker
- tests/unit/graph/test_dsl.py::TestBlockBinding::test_narrow_following_window_propagates_backward_through_run
- tests/unit/graph/test_dsl.py::TestBlockBinding::test_gap_still_breaks_propagation

Filed: none

Gates: `uv run pytest tests/unit/graph/test_dsl.py tests/test_graph.py -q`
-- 265 passed (combined with T-0309's tests, same run/file); also ran
`tests/unit/test_parse.py`, `tests/unit/test_lang_primitives.py`,
`tests/unit/test_lang_strata.py` together with the above -- 265 passed
total, no regressions in T-0286/T-0294 continuation/reserved-marker
coverage. `uv run ruff check` and `ruff check` (both PATH and
project-pinned) clean. `uv run ruff format --check` clean after one
auto-format pass. `uv run ty check` clean. `uv run frob check --only
coverage` -- 0 errors, 0 warnings (COV001=0). `uv run frob check --delta`
after `make coverage` -- `0/0 new` violations. `git diff main
--diff-filter=D --stat` empty (deletion-filter clean).
