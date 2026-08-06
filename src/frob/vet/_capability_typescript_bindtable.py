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
# frob:waive INV006 reason="the bare 'only' occurrences in this module header are \
# HISTORICAL NARRATIVE describing bugs that were already fixed ('_resolve_ts_expr \
# only ever inspected identifier/member_expression' -- past tense, describing round \
# 1's gap before round 2 closed it), not normative claims about current behavior. \
# The module's real recursion invariants live on the functions themselves in the \
# sibling _capability_typescript.py as frob:invariant terminates edges. Rewording \
# the history to dodge the word would make the narrative worse, not the code safer; \
# whether INV006 should read explanatory prose at all is T-1640."

# frob:ticket T-1420
from __future__ import annotations

from frob.lang import node_text

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


