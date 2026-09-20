"""TypeScript/JS import-table and scope-binding construction (T-1420
LARGE001 split, T-1459 design step 3, phase split of the former single-file
_capability_typescript.py): the scope-shadowing walk and the import/require/
dynamic-import binding table that `_capability_typescript.py`'s expression
resolver consumes. Split by pipeline phase (binding-table construction here,
reference resolution in the sibling module) rather than further by
language -- this file and its sibling are one TypeScript/JS resolver whose
two halves (build the binding table; resolve expressions against it) are
independently readable pieces of the same T-0377 pipeline."""

# frob:ticket T-1420

# frob:ticket T-1420
from __future__ import annotations

from frob.lang import node_text

# Import/binding-aware resolution for TypeScript/JS: import/require/
# dynamic-import/alias table + scope-shadowing over the tree-sitter
# parse, mirroring the python resolver. Resolves computed/bracket
# member access (`obj['fn']`, a no-interpolation template literal) the
# same as `obj.fn`.
#
# A COMPUTED subscript with a non-literal key, or an interpolated
# template literal, resolves ONLY when the key is bound to exactly ONE
# string literal file-wide (`_ts_bound_subscript_text`) -- a name
# reassigned to two different values stays unresolved: an honest,
# tested limitation, not a silent gap (a fail-open "flag any bracket
# access" heuristic was considered and REJECTED for its false-positive cost).
_TS_SCOPE_TYPES = (
    "function_declaration",
    "generator_function_declaration",
    "function_expression",
    "generator_function",
    "arrow_function",
    "method_definition",
    "class_declaration",
    "class_expression",
    "program",
)


def _collect_ts_target_names(node, bound: set[str]) -> None:  # noqa: ANN001
    """Add every name a TS/JS destructuring TARGET pattern binds to `bound`
    (T-0377) -- mirrors `_collect_target_names`'s python job. Recurses
    through `object_pattern`/`array_pattern`/`pair_pattern` (its `value`
    field only, never its `key`) but never through `member_expression`/
    `subscript_expression` targets (`obj.attr = x` mutates an existing
    object; it binds no new name)."""
    node_type = node.type
    if node_type in ("identifier", "shorthand_property_identifier_pattern"):
        bound.add(node_text(node))
        return
    if node_type == "pair_pattern":
        value = node.child_by_field_name("value")
        if value is not None:
            _collect_ts_target_names(value, bound)
        return
    if node_type in ("member_expression", "subscript_expression"):
        return
    for child in node.children:
        _collect_ts_target_names(child, bound)


def _collect_ts_param_name(node, bound: set[str]) -> None:  # noqa: ANN001
    """Add one `formal_parameters`-node child's bound name(s) to `bound`
    (T-0377): a plain `identifier`, or the `pattern` field of a `required_
    parameter`/`optional_parameter` (its sibling `value` field, the default
    expression, is deliberately never walked -- `{b,c:d}=obj` must bind
    `b`/`d`, never the unrelated identifier `obj`)."""
    node_type = node.type
    if node_type == "identifier":
        bound.add(node_text(node))
        return
    if node_type in ("required_parameter", "optional_parameter"):
        pattern = node.child_by_field_name("pattern")
        if pattern is not None:
            _collect_ts_target_names(pattern, bound)


# node types that open a nested TS/JS scope boundary and bind their OWN
# name (if any) into the PARENT scope, never their body -- the "return
# False" cases `_scope_bind_ts_step` dispatches to `_bind_ts_scope_boundary`
# (T-0377).
_TS_NAMED_SCOPE_BOUNDARIES = (
    "function_declaration",
    "generator_function_declaration",
    "function_expression",
    "generator_function",
    "method_definition",
    "class_declaration",
    "class_expression",
)


def _bind_ts_variable_declarator(node, bound: set[str]) -> None:  # noqa: ANN001
    """`variable_declarator` case of `_scope_bind_ts_step` (T-0377): binds
    its target pattern's names UNLESS the declarator is itself an IMPORT
    SITE -- a `require(...)` call (`_bind_ts_require_declarator` records
    that case in the import table instead) OR a dynamic `import(...)` call,
    optionally `await`-ed (`_bind_ts_dynamic_import_declarator`, T-0377
    reviewer round 2) -- a `const x = require('mod')`/`const x = await
    import('mod')` declarator must NOT also be added to this scope's
    bound-names set, or the shadow check would see the import's own target
    name as "locally bound" and treat every such binding as self-shadowing
    its own import (a genuine bug hit while writing this resolver, caught
    by `test_require_bare_detected`/`test_require_destructure_rename_
    detected`; the dynamic-import case is the identical bug in a second
    syntactic guise, caught by `test_await_dynamic_import_detected`)."""
    name_node = node.child_by_field_name("name")
    value_node = node.child_by_field_name("value")
    if name_node is not None and (
        value_node is None or _ts_module_call_target(value_node) is None
    ):
        _collect_ts_target_names(name_node, bound)


def _scope_bind_ts_step(node, is_top: bool, bound: set[str]) -> bool:  # noqa: ANN001
    """Handle ONE node during `_ts_scope_bound_names`'s walk (T-0377): add
    whatever name(s) `node` binds directly to `bound`, and report whether
    the walk should recurse into `node`'s children (False at a nested scope
    boundary -- only its own name binds in the parent scope, never its
    body; True otherwise). Mirrors `_scope_bind_step`'s python job."""
    node_type = node.type
    if not is_top and node_type in _TS_NAMED_SCOPE_BOUNDARIES:
        name_node = node.child_by_field_name("name")
        if name_node is not None:
            bound.add(node_text(name_node))
        return False
    if not is_top and node_type == "arrow_function":
        return False
    if node_type == "formal_parameters":
        for child in node.children:
            _collect_ts_param_name(child, bound)
        return False
    if node_type == "variable_declarator":
        _bind_ts_variable_declarator(node, bound)
    elif node_type == "catch_clause":
        param = node.child_by_field_name("parameter")
        if param is not None:
            _collect_ts_target_names(param, bound)
    elif node_type in ("for_in_statement", "for_statement"):
        for child in node.children:
            if child.type == "identifier":
                bound.add(node_text(child))
    return True


def _ts_scope_bound_names(scope_node) -> set[str]:  # noqa: ANN001
    """Every name bound DIRECTLY within `scope_node` (T-0377) -- parameters,
    `const`/`let`/`var` destructuring targets, `catch`/`for` bindings, and
    nested function/class names -- WITHOUT recursing into a nested scope's
    own body. Mirrors `_py_scope_bound_names`'s python job; the per-scope
    shadow table every call/member-access site is checked against before
    ever consulting the import binding table."""
    bound: set[str] = set()

    def walk(node, is_top: bool) -> None:  # noqa: ANN001
        if _scope_bind_ts_step(node, is_top, bound):
            for child in node.children:
                walk(child, False)

    walk(scope_node, True)
    return bound


def _shadowing_ts_scope(name: str, site, scope_cache: dict[int, frozenset[str]]):  # noqa: ANN001, ANN201
    """The nearest LOCAL scope node enclosing `site` (site's own function ->
    class -> ... -> program, per `_ts_scope_bound_names`, cached per scope
    node in `scope_cache`) that binds `name` directly, or `None` if no
    enclosing scope binds it at all (T-0377) -- mirrors `_shadowing_scope`'s
    python job."""
    cur = site.parent
    while cur is not None:
        if cur.type in _TS_SCOPE_TYPES:
            key = cur.id
            cached = scope_cache.get(key)
            if cached is None:
                cached = frozenset(_ts_scope_bound_names(cur))
                scope_cache[key] = cached
            if name in cached:
                return cur
            if cur.type == "program":
                break
        cur = cur.parent
    return None


def _ts_string_text(string_node) -> str:  # noqa: ANN001
    """The literal text of a TS/JS `string` node, joined across its
    `string_fragment` children (T-0377) -- excludes the quote tokens
    tree-sitter keeps as siblings; mirrors `_string_content_bytes`'s python
    counterpart, text rather than bytes since import module specifiers are
    always used as plain strings here."""
    return "".join(
        node_text(child)
        for child in string_node.children
        if child.type == "string_fragment"
    )


def _ts_require_call_module(node) -> str | None:  # noqa: ANN001
    """If `node` is a `call_expression` calling the bare `require` builtin
    with a single string-literal argument, its module specifier text;
    `None` for any other shape (a non-`require` call, a computed/dynamic
    argument, ...) -- (T-0377) the CommonJS sibling of the ES `import`
    forms `_bind_ts_import_statement` handles."""
    if node.type != "call_expression":
        return None
    func = node.child_by_field_name("function")
    if func is None or func.type != "identifier" or node_text(func) != "require":
        return None
    arguments = node.child_by_field_name("arguments")
    if arguments is None:
        return None
    string_node = next(
        (child for child in arguments.children if child.type == "string"), None
    )
    if string_node is None:
        return None
    return _ts_string_text(string_node)


def _ts_dynamic_import_module(node) -> str | None:  # noqa: ANN001
    """If `node` is a `call_expression` calling the dynamic `import(...)`
    keyword-form with a single string-literal argument, its module
    specifier text; `None` for any other shape -- (T-0377 reviewer round 2)
    the ES-module-standard sibling of `_ts_require_call_module`: `import(
    'axios')` is the STANDARD way to conditionally load a module at
    runtime, and its `function` field is a bare `import` node (not an
    `identifier`, unlike `require`), so it needs its own recognizer rather
    than reusing `_ts_require_call_module`'s identifier check."""
    if node.type != "call_expression":
        return None
    func = node.child_by_field_name("function")
    if func is None or func.type != "import":
        return None
    arguments = node.child_by_field_name("arguments")
    if arguments is None:
        return None
    string_node = next(
        (child for child in arguments.children if child.type == "string"), None
    )
    if string_node is None:
        return None
    return _ts_string_text(string_node)


def _unwrap_ts_await(node):  # noqa: ANN001, ANN201
    """`node`'s inner expression if `node` is an `await_expression`
    (`await import('x')` -> the `import('x')` call node), else `node`
    itself unchanged -- (T-0377 reviewer round 2) `await_expression` has no
    named field for its operand in this grammar, so this walks past the
    literal `await` token child."""
    if node.type != "await_expression":
        return node
    for child in node.children:
        if child.type != "await":
            return child
    return node


def _ts_module_call_target(node) -> str | None:  # noqa: ANN001
    """`node` (after unwrapping a leading `await`) resolved as a bare
    `require('x')` or dynamic `import('x')` call to its module specifier
    text, or `None` if it is neither -- (T-0377 reviewer round 2) the
    shared "is this expression itself an import site" check used by both
    the scope-binder (so an import-site declarator does not self-shadow
    its own import, T-0377 round 1's `_bind_ts_variable_declarator` fix)
    and the declarator import-table binder below."""
    unwrapped = _unwrap_ts_await(node)
    return _ts_require_call_module(unwrapped) or _ts_dynamic_import_module(unwrapped)


def _bind_ts_import_clause(node, module: str, table: dict[str, str]) -> None:  # noqa: ANN001
    """One `import_clause` node's contribution to `_ts_import_table`
    (T-0377): a bare `identifier` child is a DEFAULT import (`import dflt
    from 'x'` -> `{dflt: x}`, module root -- the default export itself is
    not further named); `namespace_import` (`import * as cp from 'x'`) ->
    `{cp: x}`; each `named_imports` -> `import_specifier` (`import {run as
    r} from 'x'` -> `{r: x.run}`, `import {exec} from 'x'` -> `{exec:
    x.exec}` when there is no `alias` field)."""
    for child in node.children:
        if child.type == "identifier":
            table.setdefault(node_text(child), module)
        elif child.type == "namespace_import":
            name_node = next(
                (c for c in child.children if c.type == "identifier"), None
            )
            if name_node is not None:
                table.setdefault(node_text(name_node), module)
        elif child.type == "named_imports":
            for spec in child.children:
                if spec.type != "import_specifier":
                    continue
                name_node = spec.child_by_field_name("name")
                alias_node = spec.child_by_field_name("alias")
                if name_node is None:
                    continue
                imported = node_text(name_node)
                local = node_text(alias_node) if alias_node is not None else imported
                table.setdefault(local, f"{module}.{imported}")


def _bind_ts_import_statement(node, table: dict[str, str]) -> None:  # noqa: ANN001
    """One `import_statement` node's contribution to `_ts_import_table`
    (T-0377): dispatches to `_bind_ts_import_clause` for the ES `source`-
    bearing form (`import ... from 'x'`), or handles the TS-only
    `import_require_clause` form directly (`import cp = require('x')` ->
    `{cp: x}`) -- that form has no `source` field of its own; its module
    specifier lives inside the clause's own `require(...)` call."""
    source_node = node.child_by_field_name("source")
    module = _ts_string_text(source_node) if source_node is not None else None
    for child in node.children:
        if child.type == "import_require_clause":
            name_node = next(
                (c for c in child.children if c.type == "identifier"), None
            )
            string_node = next((c for c in child.children if c.type == "string"), None)
            if name_node is not None and string_node is not None:
                table.setdefault(node_text(name_node), _ts_string_text(string_node))
            return
        if child.type == "import_clause" and module is not None:
            _bind_ts_import_clause(child, module, table)


def _bind_ts_require_object_pattern(
    pattern_node, module: str, table: dict[str, str]
) -> None:  # noqa: ANN001
    """The `object_pattern` target branch of `_bind_ts_require_declarator`
    (T-0377): `const {exec} = require('x')` -> `{exec: x.exec}` for each
    `shorthand_property_identifier_pattern` property, `const {exec: e} =
    require('x')` -> `{e: x.exec}` for each renamed `pair_pattern`
    property."""
    for child in pattern_node.children:
        if child.type == "shorthand_property_identifier_pattern":
            imported = node_text(child)
            table.setdefault(imported, f"{module}.{imported}")
        elif child.type == "pair_pattern":
            key_node = child.child_by_field_name("key")
            value_node = child.child_by_field_name("value")
            if (
                key_node is not None
                and value_node is not None
                and value_node.type == "identifier"
            ):
                table.setdefault(
                    node_text(value_node), f"{module}.{node_text(key_node)}"
                )


def _bind_ts_require_declarator(node, table: dict[str, str]) -> None:  # noqa: ANN001
    """One `variable_declarator` node's contribution to `_ts_import_table`
    (T-0377, extended by the reviewer-round-2 dynamic-import fix) when its
    `value` (after unwrapping a leading `await`, via `_ts_module_call_
    target`) is a `require(...)` call OR a dynamic `import(...)` call: a
    plain identifier target (`const cp = require('x')`, `const cp = await
    import('x')`) -> `{cp: x}`; an `object_pattern` target dispatches to
    `_bind_ts_require_object_pattern`. A `value` that is neither contributes
    nothing (a plain `const y = 5` is not an import site)."""
    name_node = node.child_by_field_name("name")
    value_node = node.child_by_field_name("value")
    if name_node is None or value_node is None:
        return
    module = _ts_module_call_target(value_node)
    if module is None:
        return
    if name_node.type == "identifier":
        table.setdefault(node_text(name_node), module)
    elif name_node.type == "object_pattern":
        _bind_ts_require_object_pattern(name_node, module, table)


def _ts_dynamic_import_then_param_name(callback) -> str | None:  # noqa: ANN001
    """The bound parameter name of an `arrow_function`/`function_expression`
    `.then(...)` callback (T-0377 reviewer round 2) -- handles both the
    unparenthesized single-arrow-param form (`ax => ...`, field
    `"parameter"`) and the parenthesized `formal_parameters` form (`(ax) =>
    ...`/`function(ax) {...}`, taking the first plain-identifier or
    `required_parameter`/`optional_parameter` pattern). `None` for a
    zero-arg callback or a destructuring param (the module then binds to
    no single name, a documented limitation -- same posture as an
    unresolvable destructure elsewhere in this resolver)."""
    single = callback.child_by_field_name("parameter")
    if single is not None and single.type == "identifier":
        return node_text(single)
    params = callback.child_by_field_name("parameters")
    if params is None:
        return None
    for child in params.children:
        if child.type == "identifier":
            return node_text(child)
        if child.type in ("required_parameter", "optional_parameter"):
            pattern = child.child_by_field_name("pattern")
            if pattern is not None and pattern.type == "identifier":
                return node_text(pattern)
    return None


def _ts_dynamic_import_then_module(node) -> str | None:  # noqa: ANN001
    """If `node` (a `call_expression`'s `function` field) is `import('mod')
    .then` -- a `member_expression` whose `property` is literally `then`
    and whose `object` is a dynamic `import(...)` call -- its module
    specifier text; `None` for any other shape. Split out of
    `_bind_ts_dynamic_import_then` to keep that function under the arch
    length ceiling (T-0377 reviewer round 2)."""
    if node is None or node.type != "member_expression":
        return None
    obj = node.child_by_field_name("object")
    prop = node.child_by_field_name("property")
    if obj is None or prop is None or node_text(prop) != "then":
        return None
    return _ts_dynamic_import_module(obj)


def _ts_dynamic_import_then_callback(node):  # noqa: ANN001, ANN201
    """The first `arrow_function`/`function_expression` argument of a
    `call_expression`'s `arguments` field, or `None` if there is none --
    the callback `.then(cb)` is invoked with (T-0377 reviewer round 2),
    split out of `_bind_ts_dynamic_import_then` to keep it under the arch
    length ceiling."""
    arguments = node.child_by_field_name("arguments")
    if arguments is None:
        return None
    return next(
        (
            child
            for child in arguments.children
            if child.type in ("arrow_function", "function_expression")
        ),
        None,
    )


def _bind_ts_dynamic_import_then(node, table: dict[str, str]) -> None:  # noqa: ANN001
    """One `call_expression` node's contribution to `_ts_import_table`
    (T-0377 reviewer round 2) when it is `import('mod').then(cb)`: binds
    `cb`'s first parameter name to `mod` in the table, the `.then(...)`
    sibling of `_bind_ts_require_declarator`'s `await import(...)`
    assignment form -- both are standard ways to consume a dynamic
    `import()`, and both must resolve the same as a namespace import."""
    module = _ts_dynamic_import_then_module(node.child_by_field_name("function"))
    if module is None:
        return
    callback = _ts_dynamic_import_then_callback(node)
    if callback is None:
        return
    param_name = _ts_dynamic_import_then_param_name(callback)
    if param_name is not None:
        table.setdefault(param_name, module)


def _ts_import_table(program_node) -> dict[str, str]:  # noqa: ANN001
    """The file-wide local-name -> resolved-dotted-target binding table
    (T-0377, extended by the reviewer-round-2 dynamic-import fix), built
    from `_bind_ts_import_statement` (ES `import`/TS `import X =
    require(...)`), `_bind_ts_require_declarator` (CommonJS `const {..} =
    require(...)`/`const x = await import(...)`), and `_bind_ts_dynamic_
    import_then` (`import(...).then(cb => ...)`). Walks the WHOLE tree (not
    just top-level statements), same function-scoped-import over-
    approximation as the python table."""
    table: dict[str, str] = {}

    def visit(node) -> None:  # noqa: ANN001
        if node.type == "import_statement":
            _bind_ts_import_statement(node, table)
        elif node.type == "variable_declarator":
            _bind_ts_require_declarator(node, table)
        elif node.type == "call_expression":
            _bind_ts_dynamic_import_then(node, table)
        for child in node.children:
            visit(child)

    visit(program_node)
    return table
