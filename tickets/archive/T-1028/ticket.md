---
id: T-1028
title: 'graph symbol walker: module-level type-alias assignments (Literal/TypeAlias)
  not indexed as symbols'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/**
- src/frob/lang/**
- docs/modules/arch.md
- tests/test_lang.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/lang/**
  reason: T-1028's actual fix location is the python symbol walker (src/frob/lang/_walk_python.py,
    not src/frob/graph/** as originally filed -- the graph package only consumes RawSymbol
    output from frob.lang's per-language walkers); docs/modules/arch.md scope-added
    to remove the now-obsolete DOC006 waiver comment this fix makes stale
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/arch.md
  reason: T-1028's actual fix location is the python symbol walker (src/frob/lang/_walk_python.py,
    not src/frob/graph/** as originally filed -- the graph package only consumes RawSymbol
    output from frob.lang's per-language walkers); docs/modules/arch.md scope-added
    to remove the now-obsolete DOC006 waiver comment this fix makes stale
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/test_lang.py
  reason: T-1028's regression tests live in tests/test_lang.py (the walker's existing
    test module), not a new file
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_lang.py::TestParsePython::test_bare_literal_assignment_extracted_as_type_symbol
- tests/test_lang.py::TestParsePython::test_annotated_type_alias_extracted_as_type_symbol
- tests/test_lang.py::TestParsePython::test_py312_type_statement_extracted_as_type_symbol
- tests/test_lang.py::TestParsePython::test_private_type_alias_is_not_public
- tests/test_lang.py::TestParsePython::test_ordinary_assignments_are_unaffected_by_type_alias_detection
designated_repro_test: null
threat: null
component: null
---
Found while working T-1016 (DOC006 burn-down round 2): frob.gates._docptr's
CODE SYMBOL kind (and the graph symbol index it relies on,
frob.gates._docblocks._python_symbol_names_by_path, sourced from
GraphSnapshot.symbols) only indexes def/class definitions as top-level
python symbols -- a bare module-level type-alias assignment such as
`ArchCategory = Literal[...]` in src/frob/arch/_models.py is never
recorded as a graph symbol, so a doc pointer naming it
(frob.arch._models.ArchCategory, docs/modules/arch.md) is flagged DOC006
"does not resolve to a real symbol" even though the name is real and
public. Currently worked around with a targeted frob:waive DOC006 at the
one known call site; the underlying gap (module-level `Name = <value>`
assignments, e.g. Literal/TypeAlias/NewType, not walked into the graph as
symbols) likely affects other doc pointers too and is worth fixing at the
python graph-walker layer rather than waiver-by-waiver.