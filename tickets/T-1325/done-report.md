## Done report

Widened the shared ATTRVAL parser (strata-core/src/parse/grammar_core.rs::
Parser::parse_attrval) to accept a STRING-quoted alternate for both the
attribute NAME and its VALUE(s), via the existing expect_ident_or_string
helper (T-0138's claim-id precedent). This is the single call site both
grammar_node.rs's node/store `attr` clause and grammar_flow.rs's flow
`attr` clause already route through, so both surfaces gained the fix from
one change with no duplicated grammar logic.

Verified directly against the rebuilt native extension (uv run frob
natives build; maturin develop --release) that a real .strata source file
can now write `attr "exposure:public-web";` and `attr "subject:child" =
"true";` and parses to the expected elaborated attrs tuple
("exposure:public-web", "subject:child=true") -- exactly the vocabulary
_compliance.py's module docstring documents as needed but previously
unwritable in real source.

Added a regression test (tests/unit/strata/test_parse.py::TestParseModule
::test_attr_accepts_string_quoted_colon_vocabulary) covering both the
STRING key and STRING key=value forms plus a dashed bare-key form
(privacy-policy).

Scope note: added tests/unit/strata/test_parse.py and this ticket's own
tickets/T-1325/ticket.md to scope (SCOPE001/closure findings). Declined
to pull strata-core/src/parse/mod.rs into scope for the pre-existing
SCOPE002 "probable under-capture" warning on grammar_node.rs/
grammar_flow.rs calling mod.rs::tests.err -- that dependency predates
this ticket (those two files already called it before this change) and
adding mod.rs cascades into an unrelated lib.rs/docs closure; left as a
warning, not an error, and not something this narrow grammar fix should
absorb.

cargo test could not run standalone in this worktree (pyo3-build-config
picks up a stale non-worktree Python 3.10 vs this venv's 3.11 minimum);
verified instead via the actual build path this repo uses everywhere else
(uv run frob natives build -> maturin develop) plus the new pytest
regression, which exercises the compiled extension directly.

### Changed
```
 strata-core/src/parse/grammar_core.rs | 19 +++++++++++++++----
 tests/unit/strata/test_parse.py       | 24 ++++++++++++++++++++++++
 tickets/T-1325/ticket.md              | 33 ++++++++++++++++++++++++++++++++-
 3 files changed, 71 insertions(+), 5 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 590 warning(s), 732 waived
- error-findings: PRE001@tickets/T-1325
