"""TypeScript/JS import/binding-aware capability resolution (T-1420 LARGE001
split, T-1459 design step 3): scope-binding, alias-table construction, and
resolved-candidate collection for the typescript `_DangerousOperation`
needle family, split verbatim out of `frob.vet._capability` (T-0377
lineage). Every name here is re-exported (or imported back) by
`_capability` so the module's public surface is unchanged."""

# frob:ticket T-1420
from __future__ import annotations

from pathlib import Path

from frob.lang import node_text, raw_tree

from ._capability_core import ByteSpan, _fully_in_any_span, _needle_matches_resolved
from ._capability_registry import DANGEROUS_OPERATIONS, _DangerousOperation

# T-0377: import/binding-aware resolution for TypeScript/JS, mirroring the
# T-0328/T-0337 Python discipline above -- same shape (import/require/alias
# table + scope-shadowing over the same tree-sitter parse), different
# grammar. Before this, TS/JS capability scanning was pure lexical needle-
# matching over raw text, so any renamed/destructured/namespaced import to a
# dangerous module evaded it entirely: `import {run as r} from
# 'child_process'; r(cmd)` never contains the literal text "child_process"
# or "exec("/"run(" the needle table looks for at the call site; neither
# does `const {exec} = require('child_process'); exec(cmd)` or `import cp =
# require('child_process'); cp.exec(cmd)`.
#
# Import/require forms resolved into the binding table (`_ts_import_table`):
#   import {run as r} from 'child_process'   -> {"r": "child_process.run"}
#   import * as cp from 'child_process'      -> {"cp": "child_process"}
#   import dflt from 'child_process'         -> {"dflt": "child_process"}
#   import cp = require('child_process')     -> {"cp": "child_process"}
#   const {exec} = require('child_process')  -> {"exec": "child_process.exec"}
#   const cp = require('child_process')      -> {"cp": "child_process"}
#
# Scope-awareness (mandatory to avoid FALSE POSITIVES, mirrors T-0328): a
# function/method PARAMETER, or a local `const`/`let`/`var` binding, of the
# same name as an imported binding SHADOWS it in every enclosing scope from
# the site up to the module (`program`) root -- `function g(run){ run(x); }`
# must not resolve `run` to a dangerous import. A property access on an
# unrelated object (`class Job { run(){} }` then `new Job().run()`) never
# even reaches the import table: the object side of that member expression
# is a `new_expression`/`call_expression`, not a resolvable identifier/
# member chain, so resolution stops there by construction -- same posture
# as `Job().run()` in the Python resolver.
#
# T-0377 REVIEWER ROUND 2 (two live evasion classes the round-1 pass above
# missed -- both ORDINARY JS/TS idioms, not obfuscation, confirmed against
# axios/"net" to isolate the resolver from the pre-existing lexical layer):
#
#   1. COMPUTED/BRACKET MEMBER ACCESS: `require('axios')['get'](url)` and
#      `const ax = require('axios'); ax['get'](url)` evaded round 1 --
#      `_resolve_ts_expr`/`_collect_ts_candidates` only ever inspected
#      `identifier`/`member_expression` nodes, never `subscript_expression`.
#      Fixed: `_resolve_ts_subscript` resolves `obj['fn']` the same as
#      `obj.fn` whenever the subscript is STATICALLY resolvable -- a
#      string literal, or (round 3) a NO-INTERPOLATION TEMPLATE LITERAL
#      (`` ax[`get`](url) `` -- template literals are an everyday idiom
#      many lint configs PREFER over quotes, not an obfuscation trick, and
#      `` `get` `` carries identical static text to `'get'`). A genuinely
#      COMPUTED subscript -- a non-literal key OR an INTERPOLATED template
#      literal (`ax[dynamicKey](url)`, `` ax[`${dynamicKey}`](url) ``) --
#      still resolves to `None`: the property name is a runtime value this
#      static resolver cannot evaluate. This is an intentional, tested,
#      documented gap (`test_computed_subscript_not_detected`,
#      `test_interpolated_template_subscript_not_detected`), not a silent
#      one -- filed as follow-up T-draft-e7c8b53c (dynamic-key resolution
#      is a fundamentally different problem: it needs either taint-style
#      "any string-keyed access on a dangerous object is worth flagging"
#      heuristics, or giving up precision entirely for that one case).
#   2. DYNAMIC `import()`: `import('axios').then(ax => ax.get(url))` and
#      `const ax = await import('axios'); ax.get(url)` evaded round 1 --
#      `_ts_import_table`'s walk only ever dispatched on `import_statement`/
#      `variable_declarator`, never an `import(...)` CALL expression (the
#      dynamic form is syntactically a call, not a statement). Fixed:
#      `_bind_ts_dynamic_import_then` binds a `.then(cb)` callback's first
#      parameter to the imported module; `_ts_module_call_target` (shared
#      with the `require()` path via `_unwrap_ts_await`) resolves an
#      `await`-ed dynamic import assignment the same way `require()`
#      already was. Both are STANDARD ways to consume a dynamic import
#      (the standard way to conditionally load a module in TS/JS at all,
#      and a natural place to hide a dangerous one) -- both now resolve
#      identically to a namespace `import * as`.
#
# T-0432 (computed/non-literal bracket-subscript resolution, light
# dataflow): a COMPUTED subscript that is a bare identifier or a single-
# substitution template literal (`ax[key](url)`, `` ax[`${key}`](url) ``)
# now resolves when `key` is bound to exactly ONE string literal anywhere
# in the file (`_ts_local_string_bindings`/`_ts_bound_subscript_text`) --
# closes the trivial `const key = 'exec'; ax[key](url)` indirection the
# T-0377 audit flagged as accepted-but-checkable. Deliberately NOT real
# reaching-definitions dataflow: a name reassigned to two DIFFERENT
# literal values anywhere in the file (including a plain `key = 'x'`
# reassignment, not just a second declarator) is excluded from the table
# entirely (stays unresolved, never guesses which value is live at the
# subscript site); a name assigned a non-literal value (a function call, a
# concatenation, a member-access key) is excluded the same way; a template
# literal with MORE than one substitution or any surrounding literal text
# still resolves to `None`. Considered and REJECTED: a fail-open heuristic
# ("any bracket access on an object resolved to a known-dangerous import
# is worth flagging regardless of subscript shape") -- the false-positive
# cost against ordinary dynamic-dispatch idioms (a lookup table, a plugin
# registry) was judged too high without a concrete finding to weigh it
# against; the light single-literal-binding dataflow above is the
# genuinely-closed subset, everything else stays an honest, tested
# limitation (`test_non_literal_bound_subscript_not_detected`,
# `test_multi_substitution_template_subscript_not_detected`,
# `test_reassigned_const_string_subscript_not_detected`).
#
# Known limitations, documented rather than silently eaten (mirrors this
# module's "Honest limits" posture): `export {x as y}` / re-export forms
# add no binding (not import sites -- a cross-FILE resolution, and this
# resolver, like the whole capability scanner, works one file at a time; no
# `export ... from`/`export * from`/`export default` cross-module linking is
# attempted, matching the taxonomy's own "needs source-module enumerability"
# caveat for the `export * from` row); a function-scoped `const`/`require`
# is folded into the same file-wide binding table as a module-level one when
# it is a plain `require()` destructure (a narrow, safe-direction over-
# approximation, same as Python's function-scoped `import`); a COMPUTED
# bracket subscript -- a NON-LITERAL key OR an INTERPOLATED template literal
# (a static, no-interpolation template literal DOES resolve, round 3 above)
# -- resolves only through the T-0432 single-literal-binding case above,
# else stays unresolved (T-draft-e7c8b53c tracks the fully-general case, see
# above); a `.then(cb)` callback's module binding is added to the FILE-WIDE
# table rather than scoped to the callback body (the same over-
# approximation as every other binding here -- can only ADD a resolution,
# never suppress a real one). A `class` FIELD holding a bound reference
# (taxonomy "class field/method holding a bound reference" row, `class C {
# run = cp.exec; }`) is NOT resolved through a later `new C().run(x)` call
# site -- that needs points-to tracking through CONSTRUCTED instances, a
# strictly harder problem than the by-local-name object-identity best effort
# `_ts_attr_rebind_lookup` gives ordinary object rebinding (T-0660); a
# `macro`-free language has no analog to Rust's `macro_rules!` row, so no
# gap exists here for it.
#
# T-0660: closes the previously-documented "no scope-local alias copy-
# propagation" gap (the T-0337 Python enhancement's TS/JS sibling) --
# `_build_ts_alias_table`/`_record_ts_alias`/`_record_ts_declarator_alias`/
# `_record_ts_default_param_aliases` now chase a local reassignment
# (`f = cp.exec`), a chained assignment (`a = b = cp.exec`), an array-
# destructuring bind (`const [f] = [cp.exec]`), default-parameter
# forwarding (`function f(cb = cp.exec)`), and a by-name member-target
# rebind (`obj.run = cp.exec`) the same way the python resolver's alias
# table does.
# C-C++/Kotlin remain OUT of scope for this pass; Rust gets its own binding-
# aware pass, T-0378 below.
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
