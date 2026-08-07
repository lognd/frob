---
id: T-0689
title: 'python may-raise: ctypes/cffi/C-extension call boundaries are opaque -- Unknown
  fail-closed unless declared'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: medium
blocked_by:
- T-0686
parent: T-0685
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
- docs/modules/arch.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/arch.md
  reason: 'AFFECT001 requires touching docs/modules/arch.md''s may-raise-resolver
    and

    normalized-code-model anchors since this ticket changes NormalizedCall and

    PythonAdapter.adapt, both described there -- doc-as-you-go for the same

    change, not new unrelated work.

    '
  actor: logan
  at: '2026-07-26'
evidence:
- tests/unit/test_arch.py::TestMayRaiseResolver::test_undeclared_ctypes_style_call_is_unknown
- tests/unit/test_arch.py::TestMayRaiseResolver::test_declared_raises_substitutes_for_opaque_boundary_call
- tests/unit/test_arch.py::TestMayRaiseResolver::test_declared_raises_empty_set_is_honored_not_treated_as_absent
- tests/unit/test_arch.py::TestMayRaiseResolver::test_curated_stdlib_c_extension_table_resolves_precisely
- tests/unit/test_arch.py::TestPythonAdapter::test_adapt_parses_frob_raises_declaration_on_call_line
designated_repro_test: null
acceptance:
- text: GIVEN a call into an undeclared ctypes function WHEN the resolver runs THEN
    Unknown appears in the caller's may-raise set; GIVEN the same call with a frob:raises
    declaration THEN the declared set substitutes
  evidence:
  - tests/unit/test_arch.py::TestMayRaiseResolver::test_undeclared_ctypes_style_call_is_unknown
  - tests/unit/test_arch.py::TestMayRaiseResolver::test_declared_raises_substitutes_for_opaque_boundary_call
  - tests/unit/test_arch.py::TestMayRaiseResolver::test_declared_raises_empty_set_is_honored_not_treated_as_absent
  - tests/unit/test_arch.py::TestMayRaiseResolver::test_curated_stdlib_c_extension_table_resolves_precisely
  - tests/unit/test_arch.py::TestPythonAdapter::test_adapt_parses_frob_raises_declaration_on_call_line
threat: null
component: null
---
User mandate: account for the builtins AND the ctypes-ish surface we know. Calls crossing into ctypes, cffi, or compiled C-extension modules (module has no Python source in the graph, or known binary-ext loader) contribute Unknown to the caller's may-raise set fail-closed. EXCEPTION: a boundary covered by a frob:raises declaration (sibling ticket) substitutes its declared set. Curate the stdlib C-extension raiser table for modules we know (json.loads -> JSONDecodeError, sqlite3 -> sqlite3.Error family, struct -> struct.error, ...) so common cases resolve precisely instead of Unknown.