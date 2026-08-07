---
id: T-0609
title: 'arch: normalized code model (language-agnostic node types + adapter protocol)'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0329
tier: ticket
sprint: null
scope:
- src/frob/arch/_models.py
- src/frob/arch/_normalized.py
- docs/modules/arch.md
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestNormalizedModel::test_hand_built_python_snippet_shape
- tests/unit/test_arch.py::TestNormalizedModel::test_language_adapter_is_a_runtime_checkable_protocol
designated_repro_test: null
threat: null
component: null
---
Define the normalized-code-model types (module, class, function, method, param, branch, loop, call, import, override, field-access, return, raise/throw, catch) as pydantic models in src/frob/arch/_normalized.py, plus an Adapter protocol each language walker implements to map its tree-sitter grammar onto the model. No behavior change yet: existing python/cpp checks keep running unchanged. Acceptance: model types + protocol defined, unit tests construct a normalized tree by hand for a trivial python snippet and assert shape; docs/modules/arch.md documents the model.