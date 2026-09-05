## Done report

DESIGN QUESTIONS ANSWERED

1. NESTED QUOTES: refused by name, no escape mechanism. `_ATTR_RE`'s own
   `"([^"]*)"` grammar has no escape today, so extending the SAME
   convention to positional position means positional quoting inherits
   the same limit. When a quoted value or attribute value's leftover
   text (after `_ATTR_RE.sub`) still contains a raw `"`, `_parse_attrs`
   now returns a MalformedDirective naming it explicitly ("nested quote
   in ... -- a quoted value cannot itself contain a literal '\"' (no
   escape mechanism; rewrite the value without an embedded quote)")
   rather than silently truncating at the inner quote. An unterminated
   quote (no closing `"` anywhere on the logical line) is likewise a
   named refusal ("unterminated quoted target: ...").

2. WHERE IT IS HONOURED: the quoted target is unquoted by the parser
   into a plain Python string before it ever becomes `Edge.target` --
   every downstream reader (matches_collected, the gates/tickets
   resolvers, frob fmt) sees one opaque string, indistinguishable from
   an unquoted target, and does no further whitespace-splitting on it.
   Enumerated every positional-value reader in the DSL: the only one is
   `_parse_line`'s target/attrs split (now `_parse_target`, split out
   for ARCH001). `frob:transition`/`frob:requires` (the `_ATTR_ONLY_VERBS`)
   have no bare positional target at all -- their target IS an
   attribute (`proto=`), already quoted via `_ATTR_RE`, untouched by
   this change. `_waive004_dead_count_by_rule` in gates/_waive.py reads
   a rule-name token out of a violation MESSAGE (not a directive line)
   via `rest.split(" ", 1)`, but rule ids never contain spaces -- not a
   positional directive value, out of scope.

3. FMT ROUND TRIP: `canonicalize_text`'s wrap/unwrap is content-agnostic
   -- it treats the whole logical directive text as an opaque string and
   wraps only at word boundaries, joining with the empty string on
   unfold (T-0286's existing continuation-space convention already
   covers this). A quoted target is just more text to that pipeline, so
   no special-casing was needed; proved via
   test_quoted_target_round_trips_through_fmt_wrap, which re-wraps a
   quoted-target directive at every width from 20 to 116 cols and
   asserts the parsed target is byte-identical at every width.

POSITIONAL-VALUE READER ENUMERATION (T-3893's requirement 2): only one
exists in this DSL -- `_parse_line`/`_parse_target`'s target/attrs split.
Confirmed via a targeted search for `.partition(" ")`/`.split(" ", 1)`
sites in src/frob (dsl.py:1094 -- now inside `_parse_target`; two other
hits are gates/__init__.py and gates/_waive.py, both parsing NON-directive
text -- a comment-tail string and a violation message -- not a directive
line's positional value).

SCOPE-CLOSURE NOTE (pre-existing, not caused by this diff, not filed as
a duplicate ticket): `frob check --ticket T-3893` reports 7 SCOPE002
findings for OTHER pre-existing symbols in src/frob/graph/dsl.py
(fold_comment_runs, markdown_anchors x4, mask_frob_mentions, dedupe_slug,
_attrs_verb_error_waive) whose own frob:doc/frob:tests targets live in
docs/modules/graph.md, docs/modules/gates.md, and several test files not
in this ticket's scope. Measured: scoping in docs/modules/graph.md or
gates.md (both giant shared index docs describing symbols across nearly
the whole codebase) pulls in hundreds of further unrelated SCOPE002
findings transitively -- the exact same shape T-3903's done report
measured and worked around (dropping a frob:doc edge there; not
applicable here since these are OTHER, legitimate, already-documented
symbols this ticket does not touch). SCOPE002 fires with `file="tickets.md"`,
a virtual path with no real site for a same-file frob:waive, so it is
effectively unwaivable by source directive -- already named by T-3902's
own DOC006 finding (a `--scope002-ack` CLI option referenced but not real).
Not filing a duplicate ticket for this gap; T-3902 already names it.

gate:DEPR (fmt_runner.py), gate:DOC (tickets/T-3902/ticket.md), and
gate:DRIFT (verify/_worker.py) failures in the same `frob check --ticket`
run are pre-existing, unrelated to this diff (none of those three files
are touched by T-3893).

## Done report

Changed:
src/frob/graph/dsl.py::_QUOTED_TARGET_RE
src/frob/graph/dsl.py::_parse_target
src/frob/graph/dsl.py::_parse_line
src/frob/graph/dsl.py::_parse_attrs

Evidence:
tests/unit/graph/test_dsl.py::TestQuotedPositionalTarget::test_quoted_target_with_spaces_parses_as_one_value
tests/unit/graph/test_dsl.py::TestQuotedPositionalTarget::test_quoted_target_with_no_trailing_attrs
tests/unit/graph/test_dsl.py::TestQuotedPositionalTarget::test_unquoted_target_with_space_is_still_an_error
tests/unit/graph/test_dsl.py::TestQuotedPositionalTarget::test_nested_quote_in_quoted_target_is_a_named_refusal
tests/unit/graph/test_dsl.py::TestQuotedPositionalTarget::test_unterminated_quoted_target_is_a_named_refusal
tests/unit/graph/test_dsl.py::TestQuotedPositionalTarget::test_attribute_form_is_untouched
tests/unit/graph/test_dsl.py::TestQuotedPositionalTarget::test_quoted_target_round_trips_through_fmt_wrap

Filed: none

Gates: frob check --ticket T-3893 -- ARCH001/FMT001/LANDPARITY002/PRE001
clean. 7 pre-existing SCOPE002 findings (see scope-closure note above,
unrelated to this diff, effectively unwaivable per T-3903 precedent) and
3 pre-existing gate:DEPR/DOC/DRIFT findings on unrelated files remain;
none touch T-3893's scope (src/frob/graph/dsl.py,
tests/unit/graph/test_dsl.py, docs/guides/extending/comment-dsl-directives.md).

### Changed
```
 docs/guides/extending/comment-dsl-directives.md |  21 ++
 src/frob/graph/dsl.py                           | 117 ++++++++++-
 tests/unit/graph/test_dsl.py                    | 130 +++++++++++++
 tickets/T-3893/ticket.md                        | 248 +++++++++++++++++++++++-
 4 files changed, 507 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/graph/test_dsl.py::TestQuotedPositionalTarget::test_quoted_target_with_spaces_parses_as_one_value` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestQuotedPositionalTarget::test_quoted_target_with_no_trailing_attrs` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestQuotedPositionalTarget::test_unquoted_target_with_space_is_still_an_error` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestQuotedPositionalTarget::test_nested_quote_in_quoted_target_is_a_named_refusal` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestQuotedPositionalTarget::test_unterminated_quoted_target_is_a_named_refusal` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestQuotedPositionalTarget::test_attribute_form_is_untouched` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestQuotedPositionalTarget::test_quoted_target_round_trips_through_fmt_wrap` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 4 error(s), 4372 warning(s), 933 waived
- error-findings: DEPR003@src/frob/app/fmt_runner.py, DOC006@tickets/T-3902/ticket.md, DRIFT001@src/frob/verify/_worker.py, SCOPE002@tickets.md
