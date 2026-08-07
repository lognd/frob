## Done report

Changed:
- src/frob/graph/dsl.py::_fold_continuations (new, private)
- src/frob/graph/dsl.py::parse_directives (rewritten to flatten `parsed.comments`
  into a file-ordered stream of physical `(lineno, text, src)` triples before
  folding continuations, then dispatch each folded logical line -- see note below
  on why the flatten step was necessary beyond the ticket's original sketch)
- tests/unit/graph/test_dsl.py (new file, class TestContinuation, 8 tests)
- tests/unit/graph/__init__.py (new, empty, package marker for the new test dir)
- docs/guides/extending/comment-dsl-directives.md (new "Multi-line directives
  (backslash continuation)" section with mechanics + worked long-reason example)
- docs/modules/graph.md#comment-dsl (added a continuation-syntax paragraph
  cross-referencing the extending guide)

Design deviation from the ticket sketch, and why: the ticket's plan assumed
folding could operate purely within one `comment.text.splitlines()` run.
Verified empirically that this is false for `#`/`//` comments -- `frob.lang`'s
extractor gives each stacked `#`/`//` line its OWN `RawComment` (confirmed via
the existing `test_binds_three_stacked_directives_to_def` test, which parses 3
stacked `#` lines into 3 separate edges, and via a failing first-pass run of
the new tests that logged "extracted 1 symbols, 2 comments" for a 2-line `#`
continuation). `_fold_continuations` therefore operates on ALL of
`parsed.comments` flattened into one file-ordered physical-line stream (each
line tagged with its absolute lineno and resolved `src` binding), not on a
single comment's `text`. This keeps `/* */` block comments (whose multi-line
`text` already lives in one `RawComment`) and `#`/`//` comments uniform, and
still satisfies "works uniformly across #, //, and /* */" from the ticket --
just via a different code path than the sketch implied. Folding requires the
next physical line to be exactly `lineno + 1` (no gap), matching the DSL's
existing treatment of non-adjacent comment lines as unrelated.

Design decisions (documented in `_fold_continuations`'s docstring and the
extending guide):
- Join uses the empty string, not a space -- callers put a trailing space
  before the backslash if they want one at the join point.
- Detection is on the right-stripped line (trailing whitespace after the
  backslash is tolerated and dropped); only the backslash itself is removed,
  whitespace before it is preserved.
- Dangling backslash (trailing `\` on the last physical line available to
  continue into -- end of file, or the next line isn't adjacent) is treated
  LITERALLY: left in place, unfolded, NOT reported as malformed. Tested by
  `test_dangling_backslash_on_last_comment_line_is_literal`.
- CRLF-safe: `\r` is stripped alongside the backslash-continuation handling
  on both the folding line and the joined-in line. Tested by
  `test_crlf_before_trailing_backslash_is_safe`.
- Verb-agnostic: proven with a multi-line `frob:tests` directive
  (`test_verb_agnostic_multiline_tests_directive`), not just `frob:waive`.
- The lineno/src binding for a folded run is always the FIRST physical line,
  proven for a MALFORMED folded directive
  (`test_folded_directive_reports_first_physical_lineno`, asserts
  `malformed[0].line == 2` -- the directive's first physical line in the
  4-line test source -- not line 3, the continuation it was folded from).
- Regression: `test_normal_single_line_directive_unchanged` and the full
  existing `tests/test_graph.py::TestDsl` suite (26 tests, all still passing)
  confirm no-trailing-backslash directives are unaffected.
- Dogfooded: `src/frob/graph/dsl.py:176-179` uses continuation on its own
  `frob:tests` directive (a target that would otherwise exceed 88 cols) --
  verified by hand that it parses to the single correct edge with target
  `tests/unit/graph/test_dsl.py::TestContinuation.test_long_reason_continues_across_lines`
  (empty-string join means no character is lost or added at the fold point).

CHANGELOG: not updated -- `_fold_continuations` is a private, non-public
symbol and `parse_directives`'s signature/return type is unchanged, so this
is not a REL001-relevant public-API surface change.

Evidence: recorded via `frob ticket evidence T-0286` (8 ids, all resolved
against a fresh `pytest --collect-only` pass):
tests/unit/graph/test_dsl.py::TestContinuation::test_long_reason_continues_across_lines,
::test_folded_directive_reports_first_physical_lineno,
::test_join_uses_empty_string_not_space, ::test_three_line_continuation,
::test_normal_single_line_directive_unchanged,
::test_dangling_backslash_on_last_comment_line_is_literal,
::test_crlf_before_trailing_backslash_is_safe,
::test_verb_agnostic_multiline_tests_directive.

Filed: none -- no out-of-scope work discovered. (Note: T-0293, already on the
ledger, independently references this ticket as a blocker for prose-tolerant
directive parsing; not touched here, out of scope.)

Gates: `uv run ruff format --check` and `uv run ruff check` clean on
src/frob/graph/dsl.py and tests/unit/graph/test_dsl.py; `uv run ty check
src/frob/graph/dsl.py` clean; `uv run pytest tests/unit/graph/test_dsl.py
tests/test_graph.py -q` -- 34 passed, 0 failed. Full `frob check` and
deletion-filter verification pending in the same session (see command output
below this report was written against).

### Addendum (re-review fix, worktree-agent-a27f0ba0aa6ee7289 @ 6c2fa5d)

Reviewer REJECTED with a reproduced obligation-graph-corruption bug:
`_fold_continuations` bounded folding with a pure physical-line-number
adjacency check (`lines[i+1][0] == lines[i][0] + 1`), with no check that
the two physical lines came from the same originating directive/comment
run. Repro (previously: 0 edges, 1 MalformedDirective -- both directives
silently lost):

```python
class A:
    x = 1  # frob:ticket T-0001\
class B:  # frob:ticket T-0002
    y = 2
```

`# frob:ticket T-0001\` (bound to A) and `# frob:ticket T-0002` (bound to
B) are unrelated directives that happen to sit on physically consecutive
lines, with the first coincidentally ending in a trailing backslash --
the old guard folded them into one garbled line and lost both edges.

Tried and discarded `_enclosing_src` equality as the discriminator
first: it fails on this exact repro, because `frob.lang`'s
following/enclosing heuristic resolves BOTH physical lines' binding to
class `B` (the first comment's `following` lookup reaches past its own
statement into the next symbol), so `src` equality alone does not
distinguish the two directives.

Fix actually landed: the fold guard also requires that the NEXT physical
line's own text does NOT itself match `_LINE_RE` (i.e. is not itself a
complete, independently-parseable `frob:<verb> ...` directive). A
genuine continuation line is always free-text/attribute content (never
a fresh directive header), so this correctly rejects the repro while
preserving every existing continuation case (empty-string join,
right-strip detection, CRLF-safety, verb-agnostic, folded lineno = first
physical line, single-line directives unchanged, dangling trailing
backslash on the last line stays literal).

New regression test:
`tests/unit/graph/test_dsl.py::TestContinuation::test_unrelated_directives_on_consecutive_lines_do_not_fold`
-- asserts the repro now yields exactly 2 edges (`T-0001\` and `T-0002`),
zero MalformedDirective.

Verify (re-run): `uv run pytest tests/unit/graph/test_dsl.py
tests/test_graph.py -q` -- all green (9 TestContinuation cases + 26
TestDsl cases); `ruff check`/`ruff format --check`/`ty check` clean on
touched files; `uv run frob check --only coverage` -- COV001=0 (the
pre-existing unrelated MalformedDirective warnings elsewhere in the repo
were confirmed present identically before this change via `git stash`,
i.e. not a regression from this fix).

Left OPEN for re-review per dispatch instructions -- ticket NOT closed.
