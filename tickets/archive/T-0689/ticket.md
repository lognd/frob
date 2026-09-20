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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
- docs/modules/arch.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
body_changes:
- mode: append
  reason: condense stdlib C-extension raiser table rationale into T-0689 body
  actor: logan
  at: '2026-09-19'
  old_length: 590
  new_length: 1824
evidence:
- tests/unit/arch_suite/test_guards.py::TestMayRaiseResolver::test_undeclared_ctypes_style_call_is_unknown
- tests/unit/arch_suite/test_guards.py::TestMayRaiseResolver::test_declared_raises_substitutes_for_opaque_boundary_call
- tests/unit/arch_suite/test_guards.py::TestMayRaiseResolver::test_declared_raises_empty_set_is_honored_not_treated_as_absent
- tests/unit/arch_suite/test_guards.py::TestMayRaiseResolver::test_curated_stdlib_c_extension_table_resolves_precisely
- tests/unit/arch_suite/test_lang_adapters.py::TestPythonAdapter::test_adapt_parses_frob_raises_declaration_on_call_line
designated_repro_test: null
acceptance:
- text: GIVEN a call into an undeclared ctypes function WHEN the resolver runs THEN
    Unknown appears in the caller's may-raise set; GIVEN the same call with a frob:raises
    declaration THEN the declared set substitutes
  evidence:
  - tests/unit/arch_suite/test_guards.py::TestMayRaiseResolver::test_undeclared_ctypes_style_call_is_unknown
  - tests/unit/arch_suite/test_guards.py::TestMayRaiseResolver::test_declared_raises_substitutes_for_opaque_boundary_call
  - tests/unit/arch_suite/test_guards.py::TestMayRaiseResolver::test_declared_raises_empty_set_is_honored_not_treated_as_absent
  - tests/unit/arch_suite/test_guards.py::TestMayRaiseResolver::test_curated_stdlib_c_extension_table_resolves_precisely
  - tests/unit/arch_suite/test_lang_adapters.py::TestPythonAdapter::test_adapt_parses_frob_raises_declaration_on_call_line
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
User mandate: account for the builtins AND the ctypes-ish surface we know. Calls crossing into ctypes, cffi, or compiled C-extension modules (module has no Python source in the graph, or known binary-ext loader) contribute Unknown to the caller's may-raise set fail-closed. EXCEPTION: a boundary covered by a frob:raises declaration (sibling ticket) substitutes its declared set. Curate the stdlib C-extension raiser table for modules we know (json.loads -> JSONDecodeError, sqlite3 -> sqlite3.Error family, struct -> struct.error, ...) so common cases resolve precisely instead of Unknown.

<!-- narrative-moved:src/frob/arch/_mayraise_tables.py:117:T-0689 -->
: Curated stdlib C-EXTENSION raiser table (T-0689), keyed on the call's
: FULL dotted callee text (`"json.loads"`, not the bare `"loads"`) --
: deliberately a SEPARATE, more specific table from `_BUILTIN_RAISERS`
: (which matches on bare name): a bare-name match here would risk
: shadowing an unrelated same-module function that happens to share a
: name with one of these (`def pack(...)` in the caller's own module,
: say) the same way `_BUILTIN_RAISERS` already narrowly accepts for true
: builtins with no realistic same-module collision. Qualified stdlib
: C-extension calls (json's `_json` accelerator, sqlite3's `_sqlite3`,
: struct's `_struct`) resolve to their documented raised type instead of
: falling through to the opaque-boundary `UNKNOWN` default (this ticket's
: user mandate) -- extend as more curated stdlib C-extension surface is
: identified; anything NOT listed here (including ctypes/cffi calls,
: which have no fixed per-call raised type at all -- see
: `frob.arch._mayraise`'s module docstring) stays `UNKNOWN`, fail-closed,
: unless covered by a `frob:callee-raises` declaration
: (`NormalizedCall.declared_raises`).
frob:ticket T-0689