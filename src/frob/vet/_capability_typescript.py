"""TypeScript/JS reference resolution and capability-scan entry points
(T-1420 LARGE001 split, T-1459 design step 3, phase split of the former
single-file _capability_typescript.py): subscript/member/identifier
expression resolution, the local alias table, and the public
_ts_binding_capabilities/_ts_binding_operations/_ts_resolved_candidates
entry points consumed by `frob.vet._capability`. Consumes the binding
table built by the sibling `_capability_typescript_bindtable` module --
see that module's docstring for why the split is by pipeline phase, not
by language."""

# frob:ticket T-1420
from __future__ import annotations

from pathlib import Path

from frob.lang import node_text, raw_tree

from ._capability_core import ByteSpan, _fully_in_any_span, _needle_matches_resolved
from ._capability_registry import DANGEROUS_OPERATIONS, _DangerousOperation
from ._capability_typescript_bindtable import (
    _TS_SCOPE_TYPES,
    _shadowing_ts_scope,
    _ts_import_table,
    _ts_module_call_target,
    _ts_string_text,
)


def _ts_static_template_text(node) -> str | None:  # noqa: ANN001
    """The static text of a `template_string` node with NO interpolation
    (`` `get` ``), or `None` if it contains at least one `template_
    substitution` child (`` `${dynamicKey}` ``/`` `pre${x}post` ``) -- a
    no-interpolation template literal carries IDENTICAL static text to an
    equivalent single/double-quoted string literal and is exactly as
    statically resolvable (T-0377 reviewer round 3: template literals are
    an everyday idiom many lint configs PREFER over quotes, not an
    obfuscation trick -- `ax[`get`](url)` must resolve the same as
    `ax['get'](url)`). An INTERPOLATED template literal stays under the
    genuinely-computed-subscript exclusion (`_resolve_ts_subscript`'s
    `None` branch, documented in the module's Known-limitations block)."""
    if node.type != "template_string":
        return None
    parts: list[str] = []
    for child in node.children:
        if child.type == "template_substitution":
            return None
        if child.type == "string_fragment":
            parts.append(node_text(child))
    return "".join(parts)


def _ts_static_subscript_text(index) -> str | None:  # noqa: ANN001
    """The static text of a subscript `index` node if it is a plain string
    literal OR a no-interpolation template literal (T-0377 reviewer round
    3), or `None` for any other shape (a genuinely computed key) --
    `_resolve_ts_subscript`'s single dispatch point for "is this subscript
    statically resolvable at all"."""
    if index.type == "string":
        return _ts_string_text(index)
    if index.type == "template_string":
        return _ts_static_template_text(index)
    return None


# T-0432: a single-substitution template literal (`` `${key}` ``) whose
# ENTIRE content is that one substitution, no surrounding text -- the
# shape `_ts_single_substitution_identifier` extracts a candidate
# identifier name from, for `_ts_bound_subscript_text`'s local-constant
# lookup to then try resolving.
def _ts_single_substitution_identifier(node) -> str | None:  # noqa: ANN001
    """If `node` is a `template_string` whose ONLY content is one
    `template_substitution` wrapping a bare `identifier` (`` `${key}` ``,
    no other text) -- that identifier's name; `None` for any other shape
    (surrounding text, more than one substitution, or a non-identifier
    substitution expression, e.g. `` `${a}${b}` ``/`` `pre${x}` ``/
    `` `${obj.prop}` ``)."""
    if node.type != "template_string":
        return None
    substitutions = [c for c in node.children if c.type == "template_substitution"]
    fragments = [c for c in node.children if c.type == "string_fragment"]
    if len(substitutions) != 1 or fragments:
        return None
    sub = substitutions[0]
    inner = [c for c in sub.children if c.type not in ("${", "}")]
    if len(inner) != 1 or inner[0].type != "identifier":
        return None
    return node_text(inner[0])


def _ts_bound_subscript_text(index, string_bindings: dict[str, str]) -> str | None:  # noqa: ANN001
    """T-0432: light dataflow closing the TRIVIAL computed-subscript
    indirection the audit found (`const key = 'exec'; ax[key](url)`,
    `` ax[`${key}`](url) ``) -- when `index` is a bare identifier, or a
    template literal whose entire content is one identifier substitution,
    look its name up in `string_bindings` (built by
    `_ts_local_string_bindings`: every name in the file bound to exactly
    ONE, non-conflicting string-literal/no-interpolation-template-literal
    value). Deliberately conservative: a name reassigned to a non-literal
    anywhere, or bound to two different literals, is EXCLUDED from
    `string_bindings` entirely (never guesses which binding is live at the
    subscript site) -- this is dataflow-lite, not real reaching-definitions
    analysis, so it stays silent (returns `None`, same as an unresolved
    computed subscript) on anything past this one shape: a function-call
    result, string concatenation, a member-access key, or a name assigned
    more than one distinct literal value anywhere in the file."""
    if index.type == "identifier":
        return string_bindings.get(node_text(index))
    ident = _ts_single_substitution_identifier(index)
    if ident is not None:
        return string_bindings.get(ident)
    return None


def _resolve_ts_subscript(
    node,
    import_table: dict[str, str],
    scope_cache: dict[int, frozenset[str]],
    string_bindings: dict[str, str],
    alias_table: dict[int, dict[str, str]] | None = None,
) -> str | None:  # noqa: ANN001
    """`subscript_expression` case of `_resolve_ts_expr` (T-0377 reviewer
    round 2, bracket-access evasion fix; extended round 3 for static
    template-literal subscripts; extended T-0432 for the trivial local-
    constant indirection case): `obj['fn']`/`` obj[`fn`] `` resolves the
    same as `obj.fn` when the subscript is a STRING LITERAL or a NO-
    INTERPOLATION TEMPLATE LITERAL (`require('axios')['get']`,
    `` ax[`get`] ``) -- a plain bracket-access RCE evasion the round-1
    resolver missed entirely (it only ever inspected `identifier`/
    `member_expression` nodes). T-0432 additionally resolves `obj[key]`/
    `` obj[`${key}`] `` when `key` is a local name bound to exactly one
    string literal in the file (`_ts_bound_subscript_text`) -- the trivial
    `const key = 'exec'; ax[key]()` indirection the audit called out. A
    GENUINELY computed subscript -- a function call, string concatenation,
    a member-access key, an interpolated template with surrounding text,
    or a name with no single resolvable literal binding -- still resolves
    to `None`, a documented limitation (module docstring below): giving up
    precision entirely for "any bracket access on a dangerous object is
    worth flagging" was considered and rejected as too high a false-
    positive cost (docs/audits/vet.md T-0432 candidates), so a real
    dangerous call reached only through genuine runtime-computed
    indirection is still NOT caught. Filed as a follow-up (T-draft-
    e7c8b53c) rather than silently accepted."""
    obj = node.child_by_field_name("object")
    index = node.child_by_field_name("index")
    if obj is None or index is None:
        return None
    # frob:invariant terminates reason="obj is node's own 'object' field child, a proper descendant of node in the finite tree-sitter parse tree; mutually recurses with _resolve_ts_expr, which only descends into the subscript/member branches by calling back here" measure="node's subtree depth strictly decreases"  # noqa: E501
    resolved_obj = _resolve_ts_expr(
        obj, import_table, scope_cache, string_bindings, alias_table
    )
    if resolved_obj is None:
        return None
    static_text = _ts_static_subscript_text(index)
    if static_text is None:
        static_text = _ts_bound_subscript_text(index, string_bindings)
    if static_text is None:
        return None
    return f"{resolved_obj}.{static_text}"


def _resolve_ts_member(
    node,
    import_table: dict[str, str],
    scope_cache: dict[int, frozenset[str]],
    string_bindings: dict[str, str],
    alias_table: dict[int, dict[str, str]] | None = None,
) -> str | None:  # noqa: ANN001
    """`member_expression` case of `_resolve_ts_expr` -- split out to keep
    that function under the arch length ceiling (T-0377 reviewer round 2).

    T-0660: when `obj` does not itself resolve through the import table (it
    is an ordinary local name, never imported or aliased to one), its OWN
    `.prop` may have been directly REBOUND to a dangerous target (`obj.run =
    cp.exec; obj.run(x)`, taxonomy "member rebinding") -- `_ts_attr_rebind_
    lookup` checks for that best-effort, by-name binding recorded in
    `alias_table` by `_record_ts_alias`'s member-target branch (not a real
    points-to alias -- `obj` is identified only by its local name, same
    tradeoff as the python resolver's `_attr_rebind_lookup`)."""
    obj = node.child_by_field_name("object")
    prop = node.child_by_field_name("property")
    if obj is None or prop is None:
        return None
    # frob:invariant terminates reason="obj is node's own 'object' field child, a proper descendant of node in the finite tree-sitter parse tree; mutually recurses with _resolve_ts_expr, which only descends into the subscript/member branches by calling back here" measure="node's subtree depth strictly decreases"  # noqa: E501
    resolved_obj = _resolve_ts_expr(
        obj, import_table, scope_cache, string_bindings, alias_table
    )
    if resolved_obj is not None:
        return f"{resolved_obj}.{node_text(prop)}"
    if obj.type == "identifier" and alias_table is not None:
        return _ts_attr_rebind_lookup(
            node_text(obj), node_text(prop), node, alias_table
        )
    return None


def _ts_attr_rebind_lookup(
    obj_name: str,
    attr_name: str,
    site,  # noqa: ANN001
    alias_table: dict[int, dict[str, str]],
) -> str | None:
    """Best-effort lookup for a TS/JS member-expression target REBIND
    (T-0660, `_record_ts_alias`'s member-target branch): walks `site`'s
    enclosing scope chain (mirrors `_shadowing_ts_scope`'s walk, but keys
    directly on the synthesized `"{obj_name}.{attr_name}"` string -- never a
    legal JS identifier by itself, so it cannot collide with a real
    identifier alias key in the same `alias_table`) looking for a scope that
    recorded `obj.attr = <dangerous target>`. `None` if no enclosing scope
    ever recorded such a rebind -- mirrors the python resolver's `_attr_
    rebind_lookup`."""
    key = f"{obj_name}.{attr_name}"
    cur = site.parent
    while cur is not None:
        if cur.type in _TS_SCOPE_TYPES:
            found = alias_table.get(cur.id, {}).get(key)
            if found is not None:
                return found
            if cur.type == "program":
                break
        cur = cur.parent
    return None


def _resolve_ts_expr(
    node,
    import_table: dict[str, str],
    scope_cache: dict[int, frozenset[str]],
    string_bindings: dict[str, str],
    alias_table: dict[int, dict[str, str]] | None = None,
) -> str | None:  # noqa: ANN001
    """Resolve one TS/JS expression node (a bare `identifier`, a
    `member_expression`/string-literal-`subscript_expression` chain, an
    inline `require(...)`/dynamic `import(...)` call, or -- T-0660 -- a
    nested `assignment_expression`, chasing a chained assignment's RHS) to
    its fully-qualified import-bound target, or `None` if it is locally
    shadowed, unresolved, or not a resolvable chain at all (T-0377, extended
    by the reviewer-round-2 bracket-access/dynamic-import fixes, T-0432's
    local-constant subscript dataflow, and T-0660's scope-local alias-copy-
    propagation layer -- `alias_table`, mirrors the python resolver's T-0337
    layer, closing the "no alias-copy-propagation" limitation this module's
    docstring previously documented) -- mirrors `_resolve_py_expr`'s python
    job. Any other expression (a `new_expression`, a non-import ordinary
    call, ...) is not a resolvable "object" for chain purposes -- e.g. `new
    Job()` in `new Job().run()` stops resolution here, so `.run` never
    reaches the import table (the no-false-positive case)."""
    if node.type == "identifier":
        return _resolve_ts_identifier(node, import_table, scope_cache, alias_table)
    if node.type == "member_expression":
        # frob:invariant terminates reason="mutually recurses with _resolve_ts_member, which only calls back here with node.child_by_field_name('object'), a proper descendant of node in the finite tree-sitter parse tree" measure="node's subtree depth strictly decreases"  # noqa: E501
        return _resolve_ts_member(
            node, import_table, scope_cache, string_bindings, alias_table
        )
    if node.type == "subscript_expression":
        # frob:invariant terminates reason="mutually recurses with _resolve_ts_subscript, which only calls back here with node.child_by_field_name('object'), a proper descendant of node in the finite tree-sitter parse tree" measure="node's subtree depth strictly decreases"  # noqa: E501
        return _resolve_ts_subscript(
            node, import_table, scope_cache, string_bindings, alias_table
        )
    if node.type == "call_expression":
        # T-0377 reviewer round 2: an INLINE `require('x')['fn']`/
        # `import('x')` used directly as the object of a member/subscript
        # chain, never bound to a name at all -- resolves the call itself
        # to its bare module text so the chain above it can keep going.
        return _ts_module_call_target(node)
    if node.type == "assignment_expression":
        # T-0660: chained assignment (`a = b = cp.exec; b(x);`) -- the outer
        # assignment's RHS is itself an assignment_expression; peel through
        # to its own `right` so the OUTER target's alias entry resolves the
        # same dangerous target as the inner one.
        right = node.child_by_field_name("right")
        if right is None:
            return None
        # frob:invariant terminates reason="right is node's own 'right' field child, a proper descendant of node in the finite tree-sitter parse tree; the recursion only ever descends into a strictly smaller subtree" measure="node's subtree depth strictly decreases"  # noqa: E501
        return _resolve_ts_expr(
            right, import_table, scope_cache, string_bindings, alias_table
        )
    return None


def _resolve_ts_identifier(
    node,
    import_table: dict[str, str],
    scope_cache: dict[int, frozenset[str]],
    alias_table: dict[int, dict[str, str]] | None,
) -> str | None:  # noqa: ANN001
    """Resolve a bare `identifier` node to its import-bound target,
    consulting `alias_table` for locally-shadowed names (T-0660, mirrors
    the python resolver's `_resolve_py_identifier`) -- split out of
    `_resolve_ts_expr`'s identifier branch."""
    name = node_text(node)
    scope = _shadowing_ts_scope(name, node, scope_cache)
    if scope is not None:
        if alias_table is None:
            return None
        return alias_table.get(scope.id, {}).get(name)
    return import_table.get(name)


def _collect_ts_candidates(
    node,
    import_table: dict[str, str],
    scope_cache: dict[int, frozenset[str]],
    string_bindings: dict[str, str],
    candidates: list[tuple[str, int, int]],
    alias_table: dict[int, dict[str, str]] | None = None,
) -> None:  # noqa: ANN001
    """Recursively walk `node`, appending `(resolved, start_byte, end_byte)`
    to `candidates` for every call/member/subscript-access site that
    resolves through `import_table` (T-0377, extended by the reviewer-
    round-2 bracket-access fix, T-0432's local-constant subscript dataflow,
    and T-0660's `alias_table` copy-propagation layer) -- mirrors `_collect_
    py_candidates`'s python job."""
    if node.type == "call_expression":
        func = node.child_by_field_name("function")
        if func is not None and func.type in (
            "identifier",
            "member_expression",
            "subscript_expression",
        ):
            resolved = _resolve_ts_expr(
                func, import_table, scope_cache, string_bindings, alias_table
            )
            if resolved is not None:
                candidates.append((resolved, node.start_byte, node.end_byte))
    elif node.type in ("member_expression", "subscript_expression"):
        resolved = _resolve_ts_expr(
            node, import_table, scope_cache, string_bindings, alias_table
        )
        if resolved is not None:
            candidates.append((resolved, node.start_byte, node.end_byte))
    for child in node.children:
        _collect_ts_candidates(
            child, import_table, scope_cache, string_bindings, candidates, alias_table
        )


def _ts_local_string_bindings(program_node) -> dict[str, str]:  # noqa: ANN001
    """T-0432: file-wide name -> literal-string-value table for every
    `const`/`let`/`var name = <value>` declarator whose value is a plain
    string literal or a no-interpolation template literal, when `name` has
    EXACTLY ONE such literal value across the whole file. A name assigned a
    non-literal value anywhere (a function call, another variable, string
    concatenation, ...), or assigned two DIFFERENT literal values (reused
    across unrelated scopes/branches), is deliberately EXCLUDED entirely --
    this is a conservative, no-false-claim approximation (never picks a
    "most likely" value), not real reaching-definitions dataflow; it only
    ever ADDS a resolution for the unambiguous single-literal-binding case
    `_ts_bound_subscript_text` needs, never removes or overrides a
    lexical-scan finding."""
    bindings: dict[str, str | None] = {}

    def record(name: str, value_node) -> None:  # noqa: ANN001
        """Fold one `name = value_node` binding site (declarator OR plain
        reassignment) into `bindings`, marking `name` permanently
        ambiguous (`None`) the instant it sees a non-literal value or a
        second, DIFFERENT literal value -- `let key = 'get'; key =
        'post';` must not resolve to either, since a real reassignment
        (T-0432 review: a bare declarator-only scan missed this) means the
        live value at any given subscript site is genuinely ambiguous to
        this file-wide, non-flow-sensitive pass."""
        if name in bindings and bindings[name] is None:
            return
        text = _ts_static_subscript_text(value_node)
        if text is None:
            bindings[name] = None
        elif name not in bindings:
            bindings[name] = text
        elif bindings[name] != text:
            bindings[name] = None

    def visit(node) -> None:  # noqa: ANN001
        if node.type == "variable_declarator":
            name_node = node.child_by_field_name("name")
            value_node = node.child_by_field_name("value")
            if (
                name_node is not None
                and name_node.type == "identifier"
                and value_node is not None
            ):
                record(node_text(name_node), value_node)
        elif node.type == "assignment_expression":
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
            if left is not None and left.type == "identifier" and right is not None:
                record(node_text(left), right)
        for child in node.children:
            visit(child)

    visit(program_node)
    return {name: text for name, text in bindings.items() if text is not None}


def _enclosing_ts_scope(node):  # noqa: ANN001, ANN201
    """The nearest `_TS_SCOPE_TYPES` ancestor of `node` (its own function ->
    class -> ... -> program), or `None` if `node` has no scope ancestor at
    all -- (T-0660) used by `_build_ts_alias_table` to find which scope an
    assignment's target name binds into; mirrors `_enclosing_py_scope`."""
    cur = node.parent
    while cur is not None:
        if cur.type in _TS_SCOPE_TYPES:
            return cur
        cur = cur.parent
    return None


#: TS/JS function-like node types whose OWN default-parameter values get an
#: alias-table entry keyed to the function's own scope id (T-0660, taxonomy
#: "default parameter forwarding" row: `function f(cb = cp.exec) { cb(x); }`)
#: -- excludes `class_declaration`/`class_expression`/`program` (no
#: parameter list of their own).
_TS_FUNCTION_LIKE_SCOPES = (
    "function_declaration",
    "generator_function_declaration",
    "function_expression",
    "generator_function",
    "method_definition",
    "arrow_function",
)


def _record_ts_default_param_aliases(
    func_node,
    import_table: dict[str, str],
    scope_cache: dict[int, frozenset[str]],
    string_bindings: dict[str, str],
    alias_table: dict[int, dict[str, str]],
) -> None:  # noqa: ANN001
    """Record an alias entry for every `required_parameter`/`optional_
    parameter` of `func_node` whose default `value` resolves to a dangerous
    target (T-0660: default-arg forwarding, taxonomy row `function f(cb =
    cp.exec) { cb(x); }`), keyed to `func_node`'s OWN scope id -- the same
    scope `_shadowing_ts_scope` returns for a call site inside the function
    body, since the parameter is already recorded in `_ts_scope_bound_names`
    as always bound. Mirrors the python resolver's `_record_py_default_
    param_aliases`."""
    params = func_node.child_by_field_name("parameters")
    if params is None:
        return
    scope_aliases = alias_table.setdefault(func_node.id, {})
    for param in params.children:
        if param.type not in ("required_parameter", "optional_parameter"):
            continue
        pattern = param.child_by_field_name("pattern")
        value = param.child_by_field_name("value")
        if pattern is None or value is None or pattern.type != "identifier":
            continue
        resolved = _resolve_ts_expr(
            value, import_table, scope_cache, string_bindings, alias_table
        )
        if resolved is not None:
            scope_aliases.setdefault(node_text(pattern), resolved)


def _record_ts_destructure_alias(
    left_pattern,  # noqa: ANN001 -- tree_sitter.Node (array_pattern)
    right_array,  # noqa: ANN001 -- tree_sitter.Node (array literal)
    import_table: dict[str, str],
    scope_cache: dict[int, frozenset[str]],
    string_bindings: dict[str, str],
    alias_table: dict[int, dict[str, str]],
    scope_aliases: dict[str, str],
) -> None:
    """Bind each plain-identifier element of `left_pattern` (an
    `array_pattern` destructuring target) to its POSITIONALLY corresponding
    element of `right_array`'s named children (T-0660, taxonomy
    "destructuring bind (array)" row: `const [f] = [cp.exec]; f(x)`). A
    non-identifier element (a nested pattern, a `...rest` spread) is simply
    skipped -- a narrow, documented limitation, same posture as the python
    resolver's nested-pattern gap."""
    left_elements = [c for c in left_pattern.children if c.is_named]
    right_elements = [c for c in right_array.children if c.is_named]
    for left_el, right_el in zip(left_elements, right_elements, strict=False):
        if left_el.type != "identifier":
            continue
        resolved = _resolve_ts_expr(
            right_el, import_table, scope_cache, string_bindings, alias_table
        )
        if resolved is not None:
            scope_aliases.setdefault(node_text(left_el), resolved)


def _record_ts_declarator_alias(
    node,  # noqa: ANN001 -- tree_sitter.Node (variable_declarator)
    import_table: dict[str, str],
    scope_cache: dict[int, frozenset[str]],
    string_bindings: dict[str, str],
    alias_table: dict[int, dict[str, str]],
) -> None:
    """One `variable_declarator` node's contribution to `alias_table`
    (T-0660): a plain identifier target whose `value` resolves to a
    dangerous target (taxonomy "simple assignment" row: `const f =
    require("child_process").exec; f(x)`) or an `array_pattern` target with
    an array-literal `value` (delegates to `_record_ts_destructure_alias`).
    Skips a declarator already handled as an IMPORT SITE by `_ts_import_
    table` (`_ts_module_call_target` non-`None`) -- same self-shadow
    avoidance `_bind_ts_variable_declarator` already applies for the scope
    binder."""
    name_node = node.child_by_field_name("name")
    value_node = node.child_by_field_name("value")
    if name_node is None or value_node is None:
        return
    if _ts_module_call_target(value_node) is not None:
        return
    scope = _enclosing_ts_scope(node)
    if scope is None:
        return
    scope_aliases = alias_table.setdefault(scope.id, {})
    if name_node.type == "array_pattern" and value_node.type == "array":
        _record_ts_destructure_alias(
            name_node,
            value_node,
            import_table,
            scope_cache,
            string_bindings,
            alias_table,
            scope_aliases,
        )
        return
    if name_node.type != "identifier":
        return
    resolved = _resolve_ts_expr(
        value_node, import_table, scope_cache, string_bindings, alias_table
    )
    if resolved is not None:
        scope_aliases.setdefault(node_text(name_node), resolved)


def _record_ts_alias(
    node,  # noqa: ANN001 -- tree_sitter.Node (assignment_expression)
    import_table: dict[str, str],
    scope_cache: dict[int, frozenset[str]],
    string_bindings: dict[str, str],
    alias_table: dict[int, dict[str, str]],
) -> None:
    """If `node` (an `assignment_expression`) binds a plain identifier or a
    member-expression target to a resolvable RHS, record it in `alias_table`
    (first resolution wins, mirrors the python resolver's `_record_py_
    alias`) -- covers plain reassignment (`f = cp.exec`), CHAINED assignment
    (`a = b = cp.exec`, via `_resolve_ts_expr`'s `assignment_expression`
    peel-through: this function is called once per nested `assignment_
    expression` node the tree walk visits, so both `a` and `b` get their own
    entry), and member-target REBINDING (`obj.run = cp.exec`, taxonomy
    "member rebinding" row) -- best-effort, by-NAME object identity only
    (`_ts_attr_rebind_lookup`'s tradeoff)."""
    left = node.child_by_field_name("left")
    right = node.child_by_field_name("right")
    if left is None or right is None:
        return
    scope = _enclosing_ts_scope(node)
    if scope is None:
        return
    scope_aliases = alias_table.setdefault(scope.id, {})
    if left.type == "member_expression":
        obj = left.child_by_field_name("object")
        prop = left.child_by_field_name("property")
        if obj is None or prop is None or obj.type != "identifier":
            return
        resolved = _resolve_ts_expr(
            right, import_table, scope_cache, string_bindings, alias_table
        )
        if resolved is not None:
            scope_aliases.setdefault(f"{node_text(obj)}.{node_text(prop)}", resolved)
        return
    if left.type != "identifier":
        return
    resolved = _resolve_ts_expr(
        right, import_table, scope_cache, string_bindings, alias_table
    )
    if resolved is not None:
        scope_aliases.setdefault(node_text(left), resolved)


def _build_ts_alias_table(
    program_node,  # noqa: ANN001 -- tree_sitter.Node
    import_table: dict[str, str],
    scope_cache: dict[int, frozenset[str]],
    string_bindings: dict[str, str],
) -> dict[int, dict[str, str]]:
    """Scope-local copy-propagation table (T-0660, closes this module's
    previously-documented "no alias-copy-propagation" limitation, the TS/JS
    sibling of the python resolver's T-0337/T-0659 `_build_py_alias_table`):
    `id(scope_node) -> {name: resolved_dangerous_target}` for every plain-
    identifier/member-target assignment (`_record_ts_alias`), destructuring/
    simple `const`/`let`/`var` declarator (`_record_ts_declarator_alias`),
    and default-parameter forwarding (`_record_ts_default_param_aliases`)
    whose RHS resolves (via `_resolve_ts_expr`, which itself consults this
    same table as it is built) to an import-table entry, a dangerous member
    chain, or another local name already known to alias one. The tree walk
    visits assignments/declarators in source (document) order, so an
    earlier alias is already recorded by the time a later statement copies
    it -- same document-order soundness argument as the python table."""
    alias_table: dict[int, dict[str, str]] = {}

    def visit(node) -> None:  # noqa: ANN001
        if node.type == "assignment_expression":
            _record_ts_alias(
                node, import_table, scope_cache, string_bindings, alias_table
            )
        elif node.type == "variable_declarator":
            _record_ts_declarator_alias(
                node, import_table, scope_cache, string_bindings, alias_table
            )
        elif node.type in _TS_FUNCTION_LIKE_SCOPES:
            _record_ts_default_param_aliases(
                node, import_table, scope_cache, string_bindings, alias_table
            )
        for child in node.children:
            visit(child)

    visit(program_node)
    return alias_table


def _ts_resolved_candidates(path: Path) -> tuple[tuple[str, int, int], ...]:
    """Every `(resolved_dotted_target, start_byte, end_byte)` this TS/JS
    file's call/member-access sites resolve to through its import/require
    binding table, enclosing-scope shadow check, (T-0432) single-literal
    local-constant subscript table, and (T-0660) scope-local alias-copy-
    propagation table (T-0377). Empty for a non-typescript-bucket file, an
    unparseable file, or one `frob.lang` has no grammar for -- degrades to
    the pre-existing lexical-only scan, never raises."""
    parsed = raw_tree(path)
    if parsed.is_err:
        return ()
    tree, _source, language_label = parsed.danger_ok
    if language_label != "typescript":
        return ()

    import_table = _ts_import_table(tree.root_node)
    string_bindings = _ts_local_string_bindings(tree.root_node)
    scope_cache: dict[int, frozenset[str]] = {}
    alias_table = _build_ts_alias_table(
        tree.root_node, import_table, scope_cache, string_bindings
    )
    candidates: list[tuple[str, int, int]] = []
    _collect_ts_candidates(
        tree.root_node,
        import_table,
        scope_cache,
        string_bindings,
        candidates,
        alias_table,
    )
    return tuple(candidates)


def _ts_binding_capabilities(
    path: Path,
    table: dict[str, tuple[str, ...]],
    comment_spans: tuple[ByteSpan, ...],
) -> set[str]:
    """Capability kinds observed via TS/JS import/binding-aware resolution
    only (T-0377) -- the union of every registry needle that matches a
    resolved call/member target, for sites outside a comment span. Merged
    into `scan_file_capabilities`'s lexical result; adds recall (aliased/
    destructured/namespaced import evasions) without touching the existing
    raw-text path at all. Mirrors `_python_binding_capabilities`."""
    found: set[str] = set()
    for resolved, start, end in _ts_resolved_candidates(path):
        if _fully_in_any_span(start, end, comment_spans):
            continue
        for capability, needles in table.items():
            if capability in found:
                continue
            if any(_needle_matches_resolved(needle, resolved) for needle in needles):
                found.add(capability)
    return found


def _ts_binding_operations(
    path: Path, comment_spans: tuple[ByteSpan, ...]
) -> tuple[_DangerousOperation, ...]:
    """`DANGEROUS_OPERATIONS` typescript entries observed via TS/JS import/
    binding-aware resolution only (T-0377) -- `_scan_file_operations`'s
    resolver-backed sibling to `_ts_binding_capabilities`. Mirrors
    `_python_binding_operations`."""
    candidates = _ts_resolved_candidates(path)
    if not candidates:
        return ()
    matched: list[_DangerousOperation] = []
    for entry in DANGEROUS_OPERATIONS:
        if entry.language != "typescript" or not entry.needles:
            continue
        for resolved, start, end in candidates:
            if _fully_in_any_span(start, end, comment_spans):
                continue
            if any(
                _needle_matches_resolved(needle, resolved) for needle in entry.needles
            ):
                matched.append(entry)
                break
    return tuple(matched)


def _extra_ts_binding_operations(
    path: Path,
    comment_spans: tuple[ByteSpan, ...],
    already_matched: list[_DangerousOperation],
) -> list[_DangerousOperation]:
    """`_ts_binding_operations` entries not already present in
    `already_matched` (T-0377) -- TS/JS sibling of `_extra_binding_
    operations`, same set-based dedupe."""
    seen = set(already_matched)
    extra: list[_DangerousOperation] = []
    for entry in _ts_binding_operations(path, comment_spans):
        if entry not in seen:
            extra.append(entry)
            seen.add(entry)
    return extra
