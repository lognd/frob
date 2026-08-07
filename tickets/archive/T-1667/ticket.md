---
id: T-1667
title: frob:waive comment inside a method's last statement mis-binds to the following
  sibling method (_enclosing_src)
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/dsl.py
- src/frob/lang/_walk_python.py
- src/frob/lang/_common.py
- tests/test_lang.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/lang/_common.py
  reason: root cause is _find_following_symbol/_find_enclosing_symbol in frob.lang._common,
    shared by every comment walker (_extract.py's tree-sitter walk, _walk_strata.py)
    -- dsl.py/_walk_python.py named in the ticket's own scope guess do not contain
    the actual span-lookup logic; extending to the real fix location per the ticket's
    own note ('_enclosing_src and whatever span-lookup it delegates to')
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_lang.py
  reason: root cause is _find_following_symbol/_find_enclosing_symbol in frob.lang._common,
    shared by every comment walker (_extract.py's tree-sitter walk, _walk_strata.py)
    -- dsl.py/_walk_python.py named in the ticket's own scope guess do not contain
    the actual span-lookup logic; extending to the real fix location per the ticket's
    own note ('_enclosing_src and whatever span-lookup it delegates to')
  actor: logan
  at: '2026-08-06'
evidence:
- tests/test_lang.py::TestParsePython::test_comment_before_a_methods_last_statement_binds_to_that_method
- tests/test_lang.py::TestParsePython::test_comment_directly_above_a_nested_method_still_binds_to_it
designated_repro_test: null
threat: null
component: null
---
Found while auditing OPAQUE001's newly symbol-exact waiver matching (T-1659):
a `frob:waive OPAQUE001` comment placed as the LAST statement-preceding
comment inside `_BelowLevelFilter.__init__`
(src/frob/logging/filter.py:22-25, directly above the `getattr(...)` call
at line 26) resolves, via `frob.graph.dsl`'s comment-to-symbol binding
(`_enclosing_src`), to the WRONG method: `_BelowLevelFilter.filter`
instead of `_BelowLevelFilter.__init__`.

Verified directly:

    src/frob/logging/filter.py::_BelowLevelFilter.filter OPAQUE001
    {'reason': "T-1038: below is a log-level name from this process's own
    dictConfig-declared logging setup, ..."}

(via `build_graph(...).edges`, filtered to `EdgeKind.WAIVE` for this file)
-- while the actual OPAQUE001 finding's own `Violation.symref` correctly
computes to `src/frob/logging/filter.py::_BelowLevelFilter.__init__` (via
`frob.lang.parse_file`'s span-containment lookup, the same primitive
`opaque_gate` now uses, T-1659). The waiver and the finding disagree on
which symbol the comment belongs to, so `_match_waiver`'s symbol-exact
branch (T-1652/T-1659) never matches this site -- not because the waiver
is wrong, but because `_enclosing_src` mis-binds it.

`__init__` (span 20-26 per `parse_file`) is the LAST method-body line
before the class's next sibling method (`filter`, span 28-30) begins.
`_enclosing_src`'s own binding logic likely attaches a trailing comment to
the NEXT following symbol rather than the one it is textually inside of,
in this specific "last line of a method body, comment sits right above
the method's final statement" shape. This is worth root-causing
independently of any single rule's waiver population: `_enclosing_src` is
the shared primitive EVERY `frob:` directive comment (not just
`frob:waive`) resolves through, so a systematic mis-binding here could be
silently misfiling `frob:doc`/`frob:ticket`/`frob:tests`/`frob:invariant`
edges onto the wrong symbol too, not just OPAQUE001 waivers.

Scope: src/frob/graph/dsl.py (`_enclosing_src` and whatever span-lookup it
delegates to). Out of T-1659's own declared scope
(src/frob/gates/_cache_gate.py, src/frob/gates/_opaque.py) -- filed
separately rather than folded in.

Suggested acceptance: a reduced repro (a comment sitting on the line
immediately preceding a method's LAST statement, in a class with a
following sibling method) reproducibly binds to the wrong symbol via
`_enclosing_src`/`build_graph`, and the fix makes it bind to the
textually-enclosing method instead. Re-verify
src/frob/logging/filter.py:22's `frob:waive OPAQUE001` binds to
`_BelowLevelFilter.__init__` once fixed, and re-run
`frob check --only opaque` on that file to confirm the waiver matches
again.