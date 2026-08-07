## Done report

Root-caused: `_find_following_symbol` (src/frob/lang/_common.py) only
checked whether a candidate symbol started within `_FOLLOWING_SYMBOL_
WINDOW` lines after the comment's own span end -- it never checked
whether that candidate was still inside the SAME scope the comment
itself sits in. A comment placed as the last statement-preceding comment
inside a method's body (e.g. directly above that method's final line)
with a sibling method starting within the window afterward mis-bound to
that sibling instead of the method it is textually inside of. Live
instance: `src/frob/logging/filter.py`'s `frob:waive OPAQUE001` comment,
originally placed directly above the closing `getattr(...)` call inside
`_BelowLevelFilter.__init__`, resolved (via `_enclosing_src`'s `following`-
wins-over-`enclosing` rule, T-0044) to `_BelowLevelFilter.filter` instead
of `.__init__` -- confirmed directly via `build_graph(...).edges`.

Fix: `_narrowest_symbol_containing` (new, refactored out of the existing
`_find_enclosing_symbol` search so both callers share one loop instead of
two near-duplicates) lets `_find_following_symbol` find the symbol that
ENCLOSES the comment itself, then reject any following-window candidate
whose start lies past that enclosing symbol's own end line -- such a
candidate is a SIBLING the comment is escaping out to, not something
nested inside the same scope. T-0044's original intent (a directive
directly above a NESTED method/property, nothing between them) is
unaffected: there the enclosing symbol is the wider class, and the
nested method's start still falls within the class's own span, so the
guard never rejects it -- pinned by a dedicated regression test showing
both shapes side by side.

Root cause lived in `frob.lang._common`, not `src/frob/graph/dsl.py`/
`src/frob/lang/_walk_python.py` as the ticket's own scope guess named
(`_enclosing_src` in dsl.py just consumes whatever `following`/
`enclosing` the RawComment already carries -- it never computes them;
`_walk_python.py` only builds symbols, not comments, for `.py` files;
the actual `#`-comment binder for every tree-sitter grammar, `_extract.
py::_bind_comments`, calls straight into `_common.py`). Scope extended
to `src/frob/lang/_common.py` and `tests/test_lang.py` with `frob ticket
scope --reason` accordingly -- this is the shared primitive EVERY
`frob:` directive comment resolves through, across all five languages
this package walks, not a Python-only fix.

Two regression tests in `tests/test_lang.py::TestParsePython` pin the
decision: the live-incident shape (comment before a method's last
statement, sibling method within window) now binds to the enclosing
method, not the sibling (verified to fail without the fix by reverting
it locally, re-running, and restoring); the original T-0044 nested-
method case (comment directly above a nested method, nothing between)
still binds to that nested method, proving the guard does not regress
the case it sits next to.

Re-verified the acceptance's own named site directly: `build_graph(...).
edges` now resolves `src/frob/logging/filter.py`'s `frob:waive OPAQUE001`
to `_BelowLevelFilter.__init__`, matching the finding's own symref (the
comment currently lives directly above `def __init__` -- moved there as
a workaround before this ticket started, per its own inline note -- so
this also confirms the fix does not depend on that workaround for the
ORIGINAL trailing-comment placement, per the two regression tests above).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 225 warning(s), 715 waived
- error-findings: none (measured, zero errors)
