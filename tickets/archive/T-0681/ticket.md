---
id: T-0681
title: 'arch TS adapter phase 2: interface/type-alias/enum declarations + TSX'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0611
parent: T-0329
tier: ticket
sprint: null
scope:
- src/frob/arch/_normalized.py
- src/frob/arch/_typescript.py
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_interface_declaration
- tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_enum_declaration
- tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_type_alias_declaration
- tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_exported_interface_enum_type_alias
- tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_tsx_component
- tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_class_bases_and_fields
designated_repro_test: null
acceptance:
- text: GIVEN TS fixtures with interface, type alias, enum, and a TSX component WHEN
    TypeScriptAdapter.adapt runs THEN each is represented in the NormalizedModule
    and asserted by a test
  evidence:
  - tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_interface_declaration
  - tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_enum_declaration
  - tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_type_alias_declaration
  - tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_exported_interface_enum_type_alias
  - tests/unit/test_arch.py::TestTypeScriptAdapter::test_adapt_tsx_component
threat: null
component: null
---
T-0611's TypeScriptAdapter cannot map interface_declaration, type_alias_declaration, enum_declaration, or TSX/JSX -- no NormalizedModule entity exists for them yet. Extend the model (likely a NormalizedTypeDecl entity or fields on NormalizedClass) keeping _normalized.py tree_sitter-free, then map the four constructs in _typescript.py with fires/near-miss tests. Was T-0681 (ex-draft, id lost at land) in T-0611's worktree; drafts do not survive land until T-0637's fix lands.