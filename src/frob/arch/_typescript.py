"""TypeScript architectural adapter: maps a `tree-sitter-typescript` parse
onto the T-0609 `NormalizedModule` shape (T-0611), mirroring
`frob.arch._python.PythonAdapter`'s node-walk structure one-for-one --
mirroring, not reusing, since the two grammars' node-type vocabularies and
field names differ throughout. Kept as its own module (not folded into
`frob.arch._normalized`, which stays a pure, tree_sitter-free model
module per T-0609's design) exactly mirroring `_python.py`'s placement
relative to `_normalized.py`.

Constructs mapped: `class_declaration` (`extends_clause`/`implements_clause`
bases, `public_field_definition` fields, `method_definition` methods
including `constructor`), `function_declaration`, a top-level `const x =
(...) => ...` arrow function bound to a name, `override_modifier` (->
`NormalizedFunction.overrides`, set to the method's own name -- the same
"explicit ... language's own override keyword/annotation" case the
`NormalizedFunction.overrides` docstring calls out; TypeScript's
`override` keyword makes this a real signal, unlike python which has
none), branches (`if_statement`, boolean `&&`/`||` `binary_expression`,
`ternary_expression`), loops (`for_statement`, `for_in_statement` --
both `for...of`/`for...in`), calls (`call_expression`), field accesses
(`this.x` `member_expression`s), returns (`return_statement`), throws
(`throw_statement` -> `NormalizedRaise`), catches (`catch_clause` ->
`NormalizedCatch`), and imports (`import_statement`, every clause shape:
named/default/namespace/side-effect-only).

T-0681 (phase 2) adds: `interface_declaration` (-> `NormalizedClass`,
mirroring `_kotlin.py`'s "an interface is a class with no separate
entity" precedent -- `extends_type_clause` bases, `property_signature`
fields, `method_signature` methods with no body, `body_line_count=0`),
`enum_declaration` (-> `NormalizedClass` with no bases/methods, each
`property_identifier`/`enum_assignment` member -> a `NormalizedField`
with `type=None`, mirroring `_rust.py`'s `enum_item` -> `NormalizedField`
variant handling), `type_alias_declaration` (-> the new
`NormalizedTypeAlias` entity on `NormalizedModule.type_aliases`, since a
bare alias binding carries no fields/methods/members an existing entity
could hold), and TSX (`.tsx` files parse through the `tsx` tree-sitter
grammar per `frob.lang`'s extension table, but still carry the
`"typescript"` `NormalizedModule.language` label -- `jsx_element`/
`jsx_self_closing_element` nodes need no new model entity since JSX only
ever appears as an expression inside a function body a component
function/arrow-function already becomes a `NormalizedFunction` for; the
walk simply recurses through JSX nodes like any other expression,
picking up whatever calls/branches/field-accesses they contain).

NOT mapped (no `NormalizedModule` entity exists for these, and none of
the four T-0681 constructs above needs one): TSX prop-typing internals
(`jsx_expression`, `jsx_attribute` values are not separately modeled --
only the surrounding function's existing events matter), ambient
`declare` blocks, and `namespace`/`module` declarations.
"""

from __future__ import annotations

from typing import cast

from tree_sitter import Node, Tree

from frob.arch._normalized import (
    NormalizedBranch,
    NormalizedCall,
    NormalizedCatch,
    NormalizedClass,
    NormalizedField,
    NormalizedFieldAccess,
    NormalizedFunction,
    NormalizedImport,
    NormalizedLoop,
    NormalizedModule,
    NormalizedParam,
    NormalizedRaise,
    NormalizedReturn,
    NormalizedTypeAlias,
)
from frob.lang import child_by_field as _child
from frob.lang import node_text as _node_text

_TS_LOOP_KINDS = {"for_statement": "for", "for_in_statement": "for"}
_TS_BOOLEAN_OPERATORS = frozenset({"&&", "||"})


def _ts_is_boolean_binary(node: Node) -> bool:
    """Whether a `binary_expression` node is a `&&`/`||` short-circuit
    (a decision point) rather than an arithmetic/comparison operator."""
    op = _child(node, "operator")
    return op is not None and _node_text(op) in _TS_BOOLEAN_OPERATORS


def _ts_branch_condition_text(node: Node) -> str:
    """Source text of a branch node's own test condition: an `if_statement`
    reads its `condition` field (unwrapping a `parenthesized_expression`
    down to the inner test, matching python's unwrapped condition text);
    a boolean `binary_expression`/`ternary_expression` has no separate
    condition field, so its own text stands for it."""
    if node.type in ("if_statement", "ternary_expression"):
        cond = _child(node, "condition")
        if cond is None:
            return _node_text(node)
        if cond.type == "parenthesized_expression":
            inner = next(iter(cond.named_children), None)
            return _node_text(inner) if inner is not None else _node_text(cond)
        return _node_text(cond)
    return _node_text(node)


def _ts_call_callee_text(node: Node) -> str:
    """The callee text of a `call_expression`: a bare identifier (`f(...)`)
    or the dotted `obj.method` form (`obj.method(...)`)."""
    func = _child(node, "function")
    return _node_text(func) if func is not None else _node_text(node)


def _ts_is_field_write(node: Node) -> bool:
    """Whether a `this.x` `member_expression` is the assignment-target of
    an `assignment_expression` (a write) rather than being read."""
    parent = node.parent
    if parent is None or parent.type != "assignment_expression":
        return False
    target = _child(parent, "left")
    return target is not None and target.id == node.id


def _ts_is_this_member(node: Node) -> bool:
    """Whether a `member_expression` node's object is the `this` keyword --
    the shape `NormalizedFieldAccess` tracks (`this.x`, matching python's
    `self.x`); a plain `obj.x` on some other object is not a field access."""
    obj = _child(node, "object")
    return obj is not None and obj.type == "this"


def _ts_raise_exception_type(node: Node) -> str | None:
    """The exception type name of a `throw_statement` where staticaly
    determinable (`throw new Error(...)` -> `"Error"`; a bare `throw err`
    re-throw of an identifier -> that identifier's own text), else `None`."""
    for c in node.named_children:
        if c.type == "new_expression":
            ctor = _child(c, "constructor")
            if ctor is not None:
                return _node_text(ctor)
        elif c.type == "identifier":
            return _node_text(c)
    return None


def _ts_catch_exception_type(node: Node) -> str | None:
    """The caught exception type name of a `catch_clause`, or `None` -- a
    bare `catch (e)`/`catch` catch-all binding carries no static type in
    the common case; a `catch (e: unknown)`/`catch (e: any)` typed binding
    (TS 4.4+) reads its `type_annotation`'s inner type text when present."""
    param = _child(node, "parameter")
    if param is None:
        return None
    ann = _child(param, "type")
    if ann is None:
        return None
    inner = next(iter(ann.named_children), None)
    return _node_text(inner) if inner is not None else None


# frob:waive ARCH001 reason="a single flat per-node-type dispatch table over typescript's grammar, intentionally mirroring _kt_collect_body_events/_rust_collect_body_events's exact walk shape (T-0609) so the three adapters stay structurally comparable; splitting by node-type would fragment one coherent walk into disconnected pieces without reducing the branching itself"  # noqa: E501
def _ts_collect_body_events(
    node: Node,
    branches: list[NormalizedBranch],
    loops: list[NormalizedLoop],
    calls: list[NormalizedCall],
    field_accesses: list[NormalizedFieldAccess],
    returns: list[NormalizedReturn],
    raises: list[NormalizedRaise],
    catches: list[NormalizedCatch],
) -> None:
    """Flatten every structural event (T-0609 shape) inside `node`'s
    subtree, stopping at a nested `function_declaration`/`method_definition`/
    `arrow_function`/`class_declaration` boundary -- those become their own
    `NormalizedFunction`/`NormalizedClass` (`_ts_build_function`/
    `_ts_build_class`), not events folded into the parent."""
    for c in node.children:
        if c.type in (
            "function_declaration",
            "method_definition",
            "arrow_function",
            "function_expression",
            "class_declaration",
        ):
            continue
        if c.type == "if_statement" or (
            c.type == "binary_expression" and _ts_is_boolean_binary(c)
        ):
            branches.append(
                NormalizedBranch(
                    line=c.start_point[0] + 1,
                    condition_text=_ts_branch_condition_text(c),
                )
            )
        elif c.type == "ternary_expression":
            branches.append(
                NormalizedBranch(
                    line=c.start_point[0] + 1,
                    condition_text=_ts_branch_condition_text(c),
                )
            )
        if c.type in _TS_LOOP_KINDS:
            loops.append(
                NormalizedLoop(line=c.start_point[0] + 1, kind=_TS_LOOP_KINDS[c.type])
            )
        if c.type == "call_expression":
            calls.append(
                NormalizedCall(
                    callee=_ts_call_callee_text(c), line=c.start_point[0] + 1
                )
            )
        if c.type == "member_expression" and _ts_is_this_member(c):
            field_name_node = _child(c, "property")
            if field_name_node is not None:
                field_accesses.append(
                    NormalizedFieldAccess(
                        name=_node_text(field_name_node),
                        line=c.start_point[0] + 1,
                        is_write=_ts_is_field_write(c),
                    )
                )
        if c.type == "return_statement":
            value = next(iter(c.named_children), None)
            returns.append(
                NormalizedReturn(
                    line=c.start_point[0] + 1,
                    value_text=_node_text(value) if value is not None else None,
                )
            )
        if c.type == "throw_statement":
            raises.append(
                NormalizedRaise(
                    line=c.start_point[0] + 1,
                    exception_type=_ts_raise_exception_type(c),
                )
            )
        if c.type == "catch_clause":
            catches.append(
                NormalizedCatch(
                    line=c.start_point[0] + 1,
                    exception_type=_ts_catch_exception_type(c),
                )
            )
        _ts_collect_body_events(
            c, branches, loops, calls, field_accesses, returns, raises, catches
        )


_TS_NESTING_TYPES = frozenset(
    {
        "if_statement",
        "for_statement",
        "for_in_statement",
        "while_statement",
        "try_statement",
        "switch_statement",
    }
)
_TS_CYCLOMATIC_TYPES = frozenset(
    {
        "if_statement",
        "for_statement",
        "for_in_statement",
        "while_statement",
        "catch_clause",
        "ternary_expression",
    }
)


def _ts_max_nesting(body_node: Node) -> int:
    """Deepest control-flow nesting depth inside a function/method body,
    matching `frob.arch._python._py_max_nesting`'s semantics for TS's
    grammar's own nesting node types."""

    def depth(node: Node, current: int) -> int:
        best = current
        for c in node.children:
            nxt = current + 1 if c.type in _TS_NESTING_TYPES else current
            best = max(best, depth(c, nxt))
        return best

    return depth(body_node, 0)


def _ts_cyclomatic(node: Node) -> int:
    """Cheap cyclomatic-complexity proxy over TS's grammar, matching
    `frob.arch._python._py_cyclomatic`'s semantics: a decision-point node
    (`if`/`for`/`for-in`/`for-of`/`while`/`catch`/ternary) plus one boolean
    `&&`/`||` `binary_expression` short-circuit."""
    count = 0
    if node.type in _TS_CYCLOMATIC_TYPES:
        count += 1
    elif node.type == "binary_expression" and _ts_is_boolean_binary(node):
        count += 1
    for c in node.children:
        count += _ts_cyclomatic(c)
    return count


def _ts_annotation_text(node: Node | None) -> str | None:
    """The stripped inner type text of a `type_annotation` node (`: string`
    -> `"string"`), or `None` if absent."""
    if node is None:
        return None
    inner = next(iter(node.named_children), None)
    if inner is not None:
        return _node_text(inner)
    return _node_text(node).lstrip(":").strip()


def _ts_normalize_params(params_node: Node) -> list[NormalizedParam]:
    """`NormalizedParam`s for a TS `formal_parameters` node, in source
    order: `required_parameter`/`optional_parameter` (name via the
    `pattern` field, type via `type`, a default value or the `?` optional
    marker both mapped to `has_default=True` -- a caller may omit either),
    falling back to the node's own text as the name for any other
    parameter shape (destructuring patterns, rest parameters) this first
    pass does not decompose further."""
    out: list[NormalizedParam] = []
    for p in params_node.named_children:
        if p.type in ("required_parameter", "optional_parameter"):
            pattern = _child(p, "pattern")
            name = _node_text(pattern) if pattern is not None else "?"
            ann = _child(p, "type")
            has_default = (
                p.type == "optional_parameter" or _child(p, "value") is not None
            )
            out.append(
                NormalizedParam(
                    name=name,
                    type=_ts_annotation_text(ann),
                    has_default=has_default,
                )
            )
        else:
            out.append(NormalizedParam(name=_node_text(p)))
    return out


def _ts_function_line_count(body: Node | None) -> int:
    """Line span of a function/method's body node (0 when it has none)."""
    if body is None:
        return 0
    return body.end_point[0] - body.start_point[0] + 1


def _ts_has_override_modifier(node: Node) -> bool:
    """Whether a `method_definition` carries TypeScript's `override`
    keyword -- an explicit, language-native override signal (unlike
    python, which has none) that lets `NormalizedFunction.overrides` be
    set with certainty rather than left `None`."""
    return any(c.type == "override_modifier" for c in node.children)


def _ts_build_function(node: Node, name: str, is_method: bool) -> NormalizedFunction:
    """One `function_declaration`/`method_definition`/`arrow_function` as a
    `NormalizedFunction` -- events flattened via `_ts_collect_body_events`,
    `max_nesting_depth`/`cyclomatic` computed via `_ts_max_nesting`/
    `_ts_cyclomatic` over the body (kept as SEPARATE fields, not derived
    from the flattened event lists -- see `NormalizedFunction.
    max_nesting_depth`'s docstring), mirroring
    `frob.arch._python._py_build_function`'s shape for TS's grammar."""
    params_node = _child(node, "parameters")
    ret_node = _child(node, "return_type")
    body = _child(node, "body")
    branches: list[NormalizedBranch] = []
    loops: list[NormalizedLoop] = []
    calls: list[NormalizedCall] = []
    field_accesses: list[NormalizedFieldAccess] = []
    returns: list[NormalizedReturn] = []
    raises: list[NormalizedRaise] = []
    catches: list[NormalizedCatch] = []
    if body is not None:
        _ts_collect_body_events(
            body, branches, loops, calls, field_accesses, returns, raises, catches
        )
    return NormalizedFunction(
        name=name,
        line=node.start_point[0] + 1,
        body_line_count=_ts_function_line_count(body),
        params=_ts_normalize_params(params_node) if params_node is not None else [],
        return_type=_ts_annotation_text(ret_node),
        is_method=is_method,
        overrides=name if is_method and _ts_has_override_modifier(node) else None,
        max_nesting_depth=_ts_max_nesting(body) if body is not None else 0,
        cyclomatic=_ts_cyclomatic(body) if body is not None else 0,
        branches=branches,
        loops=loops,
        calls=calls,
        field_accesses=field_accesses,
        returns=returns,
        raises=raises,
        catches=catches,
    )


def _ts_fields_of_type(body: Node, member_node_type: str) -> list[NormalizedField]:
    """Every `member_node_type`-typed direct child of `body` as a
    `NormalizedField` (extracted T-0861): the ONE field-member-walk shape
    `_ts_class_fields` (`public_field_definition`) and `_ts_interface_fields`
    (`property_signature`) both need, parameterized by which grammar node
    type each container's fields use."""
    out: list[NormalizedField] = []
    for c in body.named_children:
        if c.type != member_node_type:
            continue
        name_node = _child(c, "name")
        if name_node is None:
            continue
        ann = _child(c, "type")
        out.append(
            NormalizedField(
                name=_node_text(name_node),
                line=c.start_point[0] + 1,
                type=_ts_annotation_text(ann),
            )
        )
    return out


def _ts_class_fields(body: Node) -> list[NormalizedField]:
    """`public_field_definition` class members directly inside a class
    body (covers both `public`/`private`/`protected`-modified and
    unmodified fields -- TS's grammar uses one node type for all three)."""
    return _ts_fields_of_type(body, "public_field_definition")


def _ts_class_bases(class_node: Node) -> list[str]:
    """Base names of a `class_declaration` as written: the `extends_clause`
    superclass plus every `implements_clause` interface name -- an adapter
    does not resolve or distinguish inheritance from interface conformance,
    matching `NormalizedClass.bases`'s "as written" contract."""
    heritage = next(
        (c for c in class_node.children if c.type == "class_heritage"), None
    )
    if heritage is None:
        return []
    bases: list[str] = []
    for clause in heritage.children:
        if clause.type == "extends_clause":
            value = _child(clause, "value")
            if value is not None:
                bases.append(_node_text(value))
        elif clause.type == "implements_clause":
            for t in clause.named_children:
                bases.append(_node_text(t))
    return bases


def _ts_methods_of_type(body: Node, member_node_type: str) -> list[NormalizedFunction]:
    """Every `member_node_type`-typed direct child of `body` as a
    `NormalizedFunction` (extracted T-0861): the ONE method-member-walk
    shape `_ts_class_methods` (`method_definition`) and
    `_ts_interface_methods` (`method_signature`) both need, parameterized
    by which grammar node type each container's methods use."""
    out: list[NormalizedFunction] = []
    for c in body.named_children:
        if c.type != member_node_type:
            continue
        name_node = _child(c, "name")
        name = _node_text(name_node) if name_node is not None else "?"
        out.append(_ts_build_function(c, name, is_method=True))
    return out


def _ts_class_methods(body: Node) -> list[NormalizedFunction]:
    """`NormalizedFunction`s for every `method_definition` (including
    `constructor`) directly inside a class body."""
    return _ts_methods_of_type(body, "method_definition")


def _ts_build_class(class_node: Node) -> NormalizedClass:
    """One `class_declaration` as a `NormalizedClass`: base names
    (`_ts_class_bases`), fields (`_ts_class_fields`), and methods
    (`_ts_class_methods`)."""
    name_node = _child(class_node, "name")
    name = _node_text(name_node) if name_node is not None else "?"
    body = _child(class_node, "body")
    fields: list[NormalizedField] = []
    methods: list[NormalizedFunction] = []
    if body is not None:
        fields = _ts_class_fields(body)
        methods = _ts_class_methods(body)
    return NormalizedClass(
        name=name,
        line=class_node.start_point[0] + 1,
        bases=_ts_class_bases(class_node),
        fields=fields,
        methods=methods,
    )


def _ts_import_module_text(string_node: Node | None) -> str:
    """The unquoted module/path text of an import's `source` string node."""
    if string_node is None:
        return ""
    frag = next(
        (c for c in string_node.named_children if c.type == "string_fragment"), None
    )
    if frag is not None:
        return _node_text(frag)
    return _node_text(string_node).strip("\"'")


def _ts_named_import_names(named_imports: Node) -> list[str]:
    """Bound names from one `named_imports` (`{ a, b }`) clause (extracted
    from `_ts_build_import` to cut nesting, T-0394)."""
    names: list[str] = []
    for spec in named_imports.named_children:
        if spec.type == "import_specifier":
            name_node = _child(spec, "name")
            if name_node is not None:
                names.append(_node_text(name_node))
    return names


def _ts_import_clause_names(clause: Node) -> list[str]:
    """Every bound name in an `import_clause` -- a default import
    identifier and/or a `named_imports` group (extracted from
    `_ts_build_import` to cut nesting, T-0394)."""
    names: list[str] = []
    for c in clause.children:
        if c.type == "identifier":
            names.append(_node_text(c))
        elif c.type == "named_imports":
            names.extend(_ts_named_import_names(c))
    return names


def _ts_build_import(node: Node) -> NormalizedImport:
    """One `import_statement` as a `NormalizedImport`: the module text
    (`_ts_import_module_text`) and every bound name -- `named_imports`
    (`import_specifier`s), a default import identifier, or both together
    (`import Default, { a, b } from "mod"`); a bare namespace import
    (`import * as fs from "mod"`) or side-effect-only import (`import
    "mod"`) binds no individually-named symbol, so `names` stays `[]`."""
    module = _ts_import_module_text(_child(node, "source"))
    clause = next((c for c in node.named_children if c.type == "import_clause"), None)
    names = _ts_import_clause_names(clause) if clause is not None else []
    return NormalizedImport(module=module, line=node.start_point[0] + 1, names=names)


def _ts_interface_bases(node: Node) -> list[str]:
    """Base interface names of an `interface_declaration` as written: every
    named child of its `extends_type_clause`, or `[]` when absent -- an
    interface has no `implements_clause` of its own (only a class does),
    matching `NormalizedClass.bases`'s "as written" contract."""
    clause = next((c for c in node.children if c.type == "extends_type_clause"), None)
    if clause is None:
        return []
    return [_node_text(t) for t in clause.named_children]


def _ts_interface_fields(body: Node) -> list[NormalizedField]:
    """`property_signature` members directly inside an `interface_body` as
    `NormalizedField`s."""
    return _ts_fields_of_type(body, "property_signature")


def _ts_interface_methods(body: Node) -> list[NormalizedFunction]:
    """`method_signature` members directly inside an `interface_body` as
    `NormalizedFunction`s -- these carry no `body` field (an interface
    method has no implementation), so `_ts_build_function` naturally
    produces `body_line_count=0` and empty event lists for them, the same
    shape a bodyless abstract method gets from any other adapter."""
    return _ts_methods_of_type(body, "method_signature")


def _ts_build_interface(node: Node) -> NormalizedClass:
    """One `interface_declaration` as a `NormalizedClass` (T-0681) --
    mirroring `_kotlin.py`'s "an interface is a class with no separate
    entity" precedent: bases (`_ts_interface_bases`), fields
    (`_ts_interface_fields`), and methods (`_ts_interface_methods`)."""
    name_node = _child(node, "name")
    name = _node_text(name_node) if name_node is not None else "?"
    body = _child(node, "body")
    fields: list[NormalizedField] = []
    methods: list[NormalizedFunction] = []
    if body is not None:
        fields = _ts_interface_fields(body)
        methods = _ts_interface_methods(body)
    return NormalizedClass(
        name=name,
        line=node.start_point[0] + 1,
        bases=_ts_interface_bases(node),
        fields=fields,
        methods=methods,
    )


def _ts_enum_members(body: Node) -> list[NormalizedField]:
    """Every member of an `enum_body` as a `NormalizedField` with no type
    (a bare `property_identifier` member, or the name half of an
    `enum_assignment` member with an explicit value) -- mirroring
    `_rust.py`'s `enum_item` -> `NormalizedField` variant handling: no
    detector today needs the assigned value itself, only the member's
    name and line."""
    out: list[NormalizedField] = []
    for c in body.named_children:
        if c.type == "property_identifier":
            out.append(NormalizedField(name=_node_text(c), line=c.start_point[0] + 1))
        elif c.type == "enum_assignment":
            name_node = _child(c, "name")
            if name_node is not None:
                out.append(
                    NormalizedField(
                        name=_node_text(name_node), line=c.start_point[0] + 1
                    )
                )
    return out


def _ts_build_enum(node: Node) -> NormalizedClass:
    """One `enum_declaration` as a `NormalizedClass` with no bases/methods
    (T-0681): each member (`_ts_enum_members`) becomes a `NormalizedField`,
    mirroring `_rust.py`'s `enum_item` handling of the same construct."""
    name_node = _child(node, "name")
    name = _node_text(name_node) if name_node is not None else "?"
    body = _child(node, "body")
    return NormalizedClass(
        name=name,
        line=node.start_point[0] + 1,
        bases=[],
        fields=_ts_enum_members(body) if body is not None else [],
        methods=[],
    )


def _ts_build_type_alias(node: Node) -> NormalizedTypeAlias:
    """One `type_alias_declaration` as a `NormalizedTypeAlias` (T-0681):
    the alias name and the raw source text of its `value` type
    expression (`type X = A | B;` -> `target_text="A | B"`)."""
    name_node = _child(node, "name")
    name = _node_text(name_node) if name_node is not None else "?"
    value_node = _child(node, "value")
    target_text = _node_text(value_node) if value_node is not None else ""
    return NormalizedTypeAlias(
        name=name, line=node.start_point[0] + 1, target_text=target_text
    )


def _ts_build_module(tree: object, rel: str) -> NormalizedModule:
    """The whole-file `NormalizedModule` for a parsed TypeScript (or TSX,
    T-0681 -- both carry the `"typescript"` language label, see this
    module's docstring) file: top-level imports, classes (including
    interfaces/enums, T-0681), free functions, and type aliases
    (`TypeScriptAdapter.adapt`) -- unwraps a top-level `export [default]`
    wrapper around a class/interface/enum/function/const-arrow-function/
    type-alias declaration first, since export status itself has no
    `NormalizedModule` field to carry (matching `NormalizedClass`/
    `NormalizedFunction`'s "as written structure only, no visibility"
    contract the python adapter also keeps)."""
    t: Tree = cast("Tree", tree)
    classes: list[NormalizedClass] = []
    functions: list[NormalizedFunction] = []
    imports: list[NormalizedImport] = []
    type_aliases: list[NormalizedTypeAlias] = []
    for raw_child in t.root_node.children:
        c = raw_child
        if c.type == "export_statement":
            decl = _child(c, "declaration")
            if decl is None:
                continue
            c = decl
        if c.type == "class_declaration":
            classes.append(_ts_build_class(c))
        elif c.type == "interface_declaration":
            classes.append(_ts_build_interface(c))
        elif c.type == "enum_declaration":
            classes.append(_ts_build_enum(c))
        elif c.type == "type_alias_declaration":
            type_aliases.append(_ts_build_type_alias(c))
        elif c.type == "function_declaration":
            name_node = _child(c, "name")
            name = _node_text(name_node) if name_node is not None else "?"
            functions.append(_ts_build_function(c, name, is_method=False))
        elif c.type == "lexical_declaration":
            for declarator in c.named_children:
                if declarator.type != "variable_declarator":
                    continue
                value = _child(declarator, "value")
                if value is None or value.type != "arrow_function":
                    continue
                name_node = _child(declarator, "name")
                name = _node_text(name_node) if name_node is not None else "?"
                functions.append(_ts_build_function(value, name, is_method=False))
        elif c.type == "import_statement":
            imports.append(_ts_build_import(c))
    return NormalizedModule(
        path=rel,
        language="typescript",
        imports=imports,
        classes=classes,
        functions=functions,
        type_aliases=type_aliases,
    )


# frob:doc docs/modules/arch.md#normalized-code-model
# frob:tests tests/unit/test_arch.py::TestTypeScriptAdapter.test_adapt_stays_sane_on_realistic_snippet  # noqa: E501
class TypeScriptAdapter:
    """`LanguageAdapter` (T-0609) for TypeScript (T-0611, phase 2 T-0681):
    maps a `raw_tree`-parsed `.ts`/`.tsx` file's tree-sitter `Tree` onto a
    `NormalizedModule` by walking `tree-sitter-typescript`'s own node
    shapes -- mirroring `frob.arch._python.PythonAdapter`'s structure, not
    its node-type vocabulary (see this section's module-level comment for
    the exact construct-to-field mapping and the constructs this pass
    does not map)."""

    language = "typescript"

    # frob:doc docs/modules/arch.md#normalized-code-model
    # frob:tests tests/unit/test_arch.py::TestTypeScriptAdapter.test_adapt_stays_sane_on_realistic_snippet  # noqa: E501
    def adapt(self, tree: object, source: bytes, rel: str) -> NormalizedModule:
        """Build the `NormalizedModule` for one parsed TypeScript file
        (`tree`, `rel`) -- `source` is unused since tree-sitter `Node.text`
        already carries its own byte slice from the buffer it was parsed
        with (same contract as `PythonAdapter.adapt`)."""
        del source
        return _ts_build_module(tree, rel)
