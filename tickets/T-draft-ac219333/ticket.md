---
id: T-draft-ac219333
title: resolve_local_import drops imported NAMES for 'from X import submodule', breaking
  verify_imports for the common package-submodule idiom
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/lang/_extract.py
- src/frob/lang/_nodes.py
- src/frob/graph/callgraph.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Filed while working T-2205 (wire verify_imports=True into DEAD001/COV006/
PROTO001-005). Wiring DEAD001's build_reference_graph call to
verify_imports=True (measured on this repo's own tree, post-T-2195) moved
DEAD001 46 -> 60 findings: 0 findings disappeared, 14 appeared. Judged all
14: at least 12 of the 14 are FALSE POSITIVES (genuinely live symbols
newly reported as dead) caused by a single systemic gap, not a per-file
fluke:

`frob.lang._extract._python_import_specifiers` (src/frob/lang/_extract.py)
only reads the `module_name` field off an `import_from_statement` node and
drops every imported NAME entirely:

    if n.type == "import_from_statement":
        mod = n.child_by_field_name("module_name")
        return [_child_text(mod)] if mod is not None else []

For `from frob.arch import (_python, _cpp, _patterns, ...)`
(src/frob/arch/__init__.py:21-30) this yields only the specifier
"frob.arch" -- never "frob.arch._python", "frob.arch._cpp", etc. When
`frob.lang.resolve_local_import` resolves "frob.arch" it lands on
`src/frob/arch/__init__.py` itself (the package init), never on the
submodule files the import statement actually names. The identical shape
recurs with `from frob.app import ticket_runner as _ticket_runner`
(src/frob/app/ticket_runner/_close_cmd.py, _land_cmd.py, _new.py) --
`_graph_snapshot` (defined in ticket_runner/__init__.py) is called from
all three sibling files via exactly this import form and was one of the
14 new findings.

Net effect: `_local_imports_by_path` (src/frob/graph/callgraph.py) never
records that `__init__.py` (or any sibling file) imports a submodule
brought in via `from package import submodule[, submodule2, ...]` --
an extremely common Python idiom, not an edge case. Every private symbol
in that submodule that is called ONLY from sibling files via this import
form reads as unreferenced under verify_imports=True, even though it is
genuinely live. Confirmed concretely for:
  - src/frob/arch/_python.py::_check_long_functions/_check_god_classes/
    _check_high_coupling/_check_deep_nesting (called from
    src/frob/arch/__init__.py)
  - src/frob/arch/_cpp.py::_check_long_functions/_check_god_classes
    (same)
  - src/frob/arch/_abstraction.py::_extract_signatures/
    _collect_file_dispatch_refs/_check_abstraction_opportunities (same)
  - src/frob/arch/_patterns.py::_check_type_switch/
    _check_scattered_construction (same)
  - src/frob/app/ticket_runner/__init__.py::_graph_snapshot (called from
    _close_cmd.py/_land_cmd.py/_new.py via
    "from frob.app import ticket_runner as _ticket_runner")

This blocks T-2205: wiring verify_imports=True into DEAD001 (or COV006/
PROTO001-005, which share the same `_local_imports_by_path` primitive)
would silently mark live symbols dead across every package that uses
"from package import submodule" -- exactly the failure direction T-2205's
own acceptance criteria call out as unacceptable ("DEAD001's failure
direction is reporting LIVE symbols as dead -- silent and destructive").

Fix belongs in `frob.lang._extract._python_import_specifiers` (or
`resolve_local_import`'s consumer of it): a `from X import Y[, Z, ...]`
statement needs to also resolve each imported NAME as a potential
submodule of X, not just X itself, when Y is not a symbol defined in X's
own `__init__.py`/module body. Scope: src/frob/lang/_extract.py,
src/frob/lang/_nodes.py, src/frob/graph/callgraph.py
(`_local_imports_by_path`) -- none of which are in T-2205's scope.

T-2205 itself should stay blocked/failed on this ticket rather than
proceeding to wire COV006/PROTO001-005 against the same broken primitive.
