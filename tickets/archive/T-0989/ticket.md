---
id: T-0989
title: Split frob.lang's tree-sitter node utilities into their own module
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/lang/__init__.py
- src/frob/lang/_nodes.py
- tests/unit/test_lang_primitives.py
- docs/modules/graph.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_lang_primitives.py
  reason: 'DRIFT001 fired because tests/unit/test_lang_primitives.py''s frob:tests

    directives pointed at src/frob/lang/__init__.py::{child_by_field,node_text,

    cpp_function_nodes,resolve_local_import}, which no longer resolve there

    after the T-0989 split -- updating those directive targets to

    src/frob/lang/_nodes.py is a direct, mechanical consequence of the split,

    not new scope. docs/modules/graph.md''s #public-api anchor is the

    AFFECT001-required doc touch for the same four moved symbols.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/graph.md
  reason: 'DRIFT001 fired because tests/unit/test_lang_primitives.py''s frob:tests

    directives pointed at src/frob/lang/__init__.py::{child_by_field,node_text,

    cpp_function_nodes,resolve_local_import}, which no longer resolve there

    after the T-0989 split -- updating those directive targets to

    src/frob/lang/_nodes.py is a direct, mechanical consequence of the split,

    not new scope. docs/modules/graph.md''s #public-api anchor is the

    AFFECT001-required doc touch for the same four moved symbols.

    '
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/test_lang_primitives.py::test_child_by_field_and_node_text_public_wrappers
- tests/unit/test_lang_primitives.py::test_cpp_function_nodes_public_wrapper
- tests/unit/test_lang_primitives.py::test_resolve_local_import_maps_to_repo_relative
- tests/test_lang.py::test_lang_pipeline_integration
designated_repro_test: null
threat: null
component: null
---
Found while working T-0980's ARCH102 burn-down: `src/frob/lang/__init__.py`'s
god-module waiver reason names 4 exports (`cpp_function_nodes`,
`child_by_field`, `node_text`, `resolve_local_import`) as genuinely
independent tree-sitter node utilities with no shared state and no call
edges into the rest of the module -- a real ARCH102 split candidate, not
disposed speculatively in the same pass as the waiver.

Plan: extract those four into `src/frob/lang/_nodes.py`, re-export from
`frob/lang/__init__.py` so every existing `from frob.lang import X` caller
is unaffected, and drop the corresponding lines from the ARCH102 waiver
reason in `frob/lang/__init__.py` (module export count/cluster count both
drop, so the waiver may become removable entirely -- re-measure via
`frob check --only gates-native --json` after the split before deciding).