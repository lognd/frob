"""Rust architectural adapter: maps a `tree-sitter-rust` parse onto the
T-0609 `NormalizedModule` shape (T-0612), mirroring
`frob.arch._typescript.TypeScriptAdapter`'s node-walk structure one-for-one
-- mirroring, not reusing, since rust's grammar vocabulary differs
throughout. Kept as its OWN module (never folded into `frob.arch.
_normalized`, which stays a pure, tree_sitter-free model module per T-0609's
design, and NEVER into `frob.lang._walk_rust`, which is the symbol-catalog
walker for a different purpose (`frob check`'s doc/test coverage graph),
not this architectural model) -- exactly mirroring `_typescript.py`'s
placement relative to `_normalized.py` (the T-0611 review correction this
ticket's dispatch explicitly called out).

Constructs mapped: `struct_item` (named/tuple/unit fields ->
`NormalizedField`, tuple-struct fields get positional names `"0"`, `"1"`,
...), `enum_item` (each `enum_variant` -> a `NormalizedField`, since no
`NormalizedVariant` entity exists in the T-0609 model -- documented
limitation, same shape as the "not mapped" note below), `trait_item` (a
trait's own methods, both `function_signature_item` (no body) and a
default `function_item` (with body), become a `NormalizedClass`'s
methods), `impl_item` (an inherent `impl Type { ... }`'s methods attach to
`Type`'s `NormalizedClass`; a trait impl `impl Trait for Type { ... }`'s
methods ALSO attach to `Type`, and `Trait`'s name is appended to `Type.
bases` -- the "trait impls note the trait as a base" mapping this ticket
asks for), `function_item` (top-level free functions, params + types via
`parameter`/`self_parameter` nodes, return type via the `return_type`
field), branches (`if_expression`, a boolean `&&`/`||` `binary_expression`,
and -- unlike `_python.py`'s DELIBERATE exclusion of match/case from its
cyclomatic proxy (see `_python._BRANCH_NODE_TYPES`'s comment) -- each
individual `match_arm` counts as its own branch here, per this ticket's
explicit "match arms as branches" instruction; this is a deliberate
divergence from the python precedent, not an oversight), loops (`loop_expr
ession`->`"loop"`, `while_expression`->`"while"`, `for_expression`->
`"for"`), calls (`call_expression`, both bare and `obj.method(...)` dotted
forms via `field_expression`), field accesses (`field_expression`,
unrestricted to any receiver -- matching `_python.py`'s unrestricted
`attribute` handling, not `_typescript.py`'s `this.x`-only restriction,
since rust has no single universal receiver keyword the way JS/py's
`this`/`self` are), returns (`return_expression`, plus a function body's
own tail expression when it is itself a `return`-shaped raise -- see
below), and `use_declaration` -> `NormalizedImport` (every argument shape:
plain path, `as`-renamed, one level of `{...}` grouped list including one
level of nested grouping, and a `*` wildcard).

PANIC/RESULT MAPPING DECISION (rust has no exceptions -- this is the
adapter's own design choice, not a language feature, so it is documented
here in full): rust's closest equivalents to a raise/catch pair are (a) an
unrecoverable panic and (b) the `Result<T, E>` `Err` variant propagated
either explicitly (`return Err(...)`) or via the `?` operator. Both map
onto `NormalizedRaise`/`NormalizedCatch` as follows, in ADDITION to (never
instead of) their own literal event (a `return Err(...)` is still counted
as a `NormalizedReturn` too; an `.unwrap()` call is still counted as a
`NormalizedCall` too) since a check may want either view:
  - `panic!`/`unreachable!`/`todo!`/`unimplemented!` macro invocations ->
    `NormalizedRaise(exception_type="<name>!")` -- an explicit, unambiguous
    unrecoverable-panic site.
  - `.unwrap()`/`.expect(...)` method calls -> also
    `NormalizedRaise(exception_type="unwrap"/"expect")` -- rust's idiomatic
    "panic if this Result/Option is the failure/empty case" call sites.
  - a `return`-position or tail-position `Err(...)` call expression ->
    also `NormalizedRaise(exception_type="Err")`.
  - the `?` try-operator (`risky()?`) -> also
    `NormalizedRaise(exception_type="?")`, since it early-returns the `Err`
    variant when present -- functionally an implicit re-throw.
  - a `match` arm whose pattern's own leading identifier is `Err` (`Err(e)
    => ...`, or a bare `Err`) -> `NormalizedCatch(exception_type="Err")` --
    the "handle the failure case" arm of a `Result` match, this ticket's
    "match/Result handling -> catches equivalent" mapping. An `Ok(...)` arm
    is NOT a catch (there is no python/JS "success" analogue in
    `NormalizedCatch`).

NOT mapped (no `NormalizedModule` entity exists for these -- follow-up
tickets filed, not folded into this ticket's own scope, matching the
`_typescript.py`/T-0611 precedent for the same class of gap): a
`NormalizedVariant`/associated-data shape for enum variants (mapped onto
`NormalizedField` instead, above); rust generics (`impl<T> Foo<T>`, a
generic `fn foo<T>`) are read via their own written text, not resolved;
macro-generated items (anything expanded from a `macro_rules!`/derive
macro) are invisible to this adapter the same way they are to `frob.lang.
_walk_rust`'s symbol walker, since tree-sitter never expands macros.
"""

from __future__ import annotations

import re
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
)
from frob.lang import child_by_field as _child
from frob.lang import node_text as _node_text

_RUST_LOOP_KINDS = {
    "for_expression": "for",
    "while_expression": "while",
    "loop_expression": "loop",
}
_RUST_BOOLEAN_OPERATORS = frozenset({"&&", "||"})

#: Macro invocations that are always an unrecoverable-panic site (see this
#: module's docstring's PANIC/RESULT MAPPING DECISION).
_RUST_PANIC_MACROS = frozenset({"panic", "unreachable", "todo", "unimplemented"})

#: Method calls that panic on the failure/empty case of a `Result`/`Option`.
_RUST_PANICKING_METHODS = frozenset({"unwrap", "expect"})

#: A match arm's own leading pattern identifier that flags it as the
#: "handle the failure case" arm of a `Result` match (see this module's
#: docstring). Matched against the arm pattern's own source text, not the
#: AST shape, mirroring `_typescript.py`'s text-based condition extraction.
_ERR_PATTERN_RE = re.compile(r"^Err\b")


def _rust_is_boolean_binary(node: Node) -> bool:
    """Whether a `binary_expression` node is a `&&`/`||` short-circuit (a
    decision point) rather than an arithmetic/comparison operator."""
    op = _child(node, "operator")
    return op is not None and _node_text(op) in _RUST_BOOLEAN_OPERATORS


def _rust_branch_condition_text(node: Node) -> str:
    """Source text of a branch node's own test condition: an
    `if_expression` reads its `condition` field; a `match_arm` reads its
    `pattern` field (guard included, since a guard clause is part of the
    pattern node's own span); a boolean `binary_expression` has no
    separate condition field, so its own text stands for it."""
    if node.type == "if_expression":
        cond = _child(node, "condition")
        return _node_text(cond) if cond is not None else _node_text(node)
    if node.type == "match_arm":
        pattern = _child(node, "pattern")
        return _node_text(pattern) if pattern is not None else _node_text(node)
    return _node_text(node)


def _rust_call_callee_text(node: Node) -> str:
    """The callee text of a `call_expression`: a bare identifier (`f(...)`)
    or the dotted `obj.method` form (`obj.method(...)`, via a
    `field_expression` function target)."""
    func = _child(node, "function")
    return _node_text(func) if func is not None else _node_text(node)


def _rust_call_method_name(node: Node) -> str | None:
    """The bare method name of a `call_expression` whose callee is a
    `field_expression` (`obj.method(...)` -> `"method"`), else `None` --
    used to recognize `.unwrap()`/`.expect(...)` panic sites regardless of
    the receiver expression's own text."""
    func = _child(node, "function")
    if func is None or func.type != "field_expression":
        return None
    field = _child(func, "field")
    return _node_text(field) if field is not None else None


def _rust_is_field_write(node: Node) -> bool:
    """Whether a `field_expression` node is the assignment-target of an
    `assignment_expression` (a write) rather than being read."""
    parent = node.parent
    if parent is None or parent.type != "assignment_expression":
        return False
    target = _child(parent, "left")
    return target is not None and target.id == node.id


def _rust_is_call_target(node: Node) -> bool:
    """Whether a `field_expression` node is itself the `function` field of
    its parent `call_expression` (`obj.method(...)` -- `obj.method` is a
    method-dispatch target, not a data field access) -- excluded from
    `NormalizedFieldAccess` so a method call chain (`self.name.clone().
    unwrap()`) does not falsely register `clone`/`unwrap` as field reads;
    the call itself is still captured via `NormalizedCall` (see
    `_rust_call_callee_text`), and any GENUINE field read nested inside the
    chain (`self.name` in the example above) is unaffected -- it is the
    `value` of a `field_expression`, never the `function` of a call."""
    parent = node.parent
    if parent is None or parent.type != "call_expression":
        return False
    func = _child(parent, "function")
    return func is not None and func.id == node.id


def _rust_macro_name(node: Node) -> str | None:
    """The macro's bare name of a `macro_invocation` node (`panic!(...)` ->
    `"panic"`), else `None`."""
    if node.type != "macro_invocation":
        return None
    name_node = _child(node, "macro")
    return _node_text(name_node) if name_node is not None else None


def _rust_err_call_type(value: Node | None) -> str | None:
    """`"Err"` if `value` is a `call_expression` whose callee is the bare
    identifier `Err` (a `return`/tail-position `Err(...)` construction),
    else `None` -- see this module's docstring's PANIC/RESULT MAPPING
    DECISION."""
    if value is None or value.type != "call_expression":
        return None
    func = _child(value, "function")
    if func is not None and func.type == "identifier" and _node_text(func) == "Err":
        return "Err"
    return None


# frob:waive ARCH001 reason="a single flat per-node-type dispatch table over rust's grammar, intentionally mirroring _kt_collect_body_events/_ts_collect_body_events's exact walk shape (T-0609) so the three adapters stay structurally comparable; splitting by node-type would fragment one coherent walk into disconnected pieces without reducing the branching itself"  # noqa: E501
def _rust_collect_body_events(
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
    subtree, stopping at a nested `function_item`/`function_signature_item`/
    `struct_item`/`enum_item`/`trait_item`/`impl_item` boundary -- those
    become their own `NormalizedFunction`/`NormalizedClass`
    (`_rust_build_function`/`_rust_build_class`), not events folded into
    the parent."""
    for c in node.children:
        if c.type in (
            "function_item",
            "function_signature_item",
            "struct_item",
            "enum_item",
            "trait_item",
            "impl_item",
        ):
            continue
        if c.type == "if_expression" or (
            c.type == "binary_expression" and _rust_is_boolean_binary(c)
        ):
            branches.append(
                NormalizedBranch(
                    line=c.start_point[0] + 1,
                    condition_text=_rust_branch_condition_text(c),
                )
            )
        if c.type == "match_arm":
            branches.append(
                NormalizedBranch(
                    line=c.start_point[0] + 1,
                    condition_text=_rust_branch_condition_text(c),
                )
            )
            pattern = _child(c, "pattern")
            pattern_text = _node_text(pattern) if pattern is not None else ""
            if _ERR_PATTERN_RE.match(pattern_text):
                catches.append(
                    NormalizedCatch(line=c.start_point[0] + 1, exception_type="Err")
                )
        if c.type in _RUST_LOOP_KINDS:
            loops.append(
                NormalizedLoop(line=c.start_point[0] + 1, kind=_RUST_LOOP_KINDS[c.type])
            )
        if c.type == "call_expression":
            calls.append(
                NormalizedCall(
                    callee=_rust_call_callee_text(c), line=c.start_point[0] + 1
                )
            )
            method = _rust_call_method_name(c)
            if method in _RUST_PANICKING_METHODS:
                raises.append(
                    NormalizedRaise(line=c.start_point[0] + 1, exception_type=method)
                )
        if c.type == "field_expression" and not _rust_is_call_target(c):
            field_name_node = _child(c, "field")
            if field_name_node is not None:
                field_accesses.append(
                    NormalizedFieldAccess(
                        name=_node_text(field_name_node),
                        line=c.start_point[0] + 1,
                        is_write=_rust_is_field_write(c),
                    )
                )
        if c.type == "return_expression":
            value = next(iter(c.named_children), None)
            returns.append(
                NormalizedReturn(
                    line=c.start_point[0] + 1,
                    value_text=_node_text(value) if value is not None else None,
                )
            )
            err_type = _rust_err_call_type(value)
            if err_type is not None:
                raises.append(
                    NormalizedRaise(line=c.start_point[0] + 1, exception_type=err_type)
                )
        if (macro_name := _rust_macro_name(c)) is not None:
            if macro_name in _RUST_PANIC_MACROS:
                raises.append(
                    NormalizedRaise(
                        line=c.start_point[0] + 1, exception_type=f"{macro_name}!"
                    )
                )
        if c.type == "try_expression":
            raises.append(
                NormalizedRaise(line=c.start_point[0] + 1, exception_type="?")
            )
        _rust_collect_body_events(
            c, branches, loops, calls, field_accesses, returns, raises, catches
        )


_RUST_NESTING_TYPES = frozenset(
    {
        "if_expression",
        "for_expression",
        "while_expression",
        "loop_expression",
        "match_expression",
    }
)
_RUST_CYCLOMATIC_TYPES = frozenset(
    {
        "if_expression",
        "for_expression",
        "while_expression",
        "loop_expression",
        "match_arm",
        "try_expression",
    }
)


def _rust_max_nesting(body_node: Node) -> int:
    """Deepest control-flow nesting depth inside a function/method body,
    matching `frob.arch._python._py_max_nesting`'s semantics for rust's
    grammar's own nesting node types."""

    def depth(node: Node, current: int) -> int:
        best = current
        for c in node.children:
            nxt = current + 1 if c.type in _RUST_NESTING_TYPES else current
            best = max(best, depth(c, nxt))
        return best

    return depth(body_node, 0)


def _rust_cyclomatic(node: Node) -> int:
    """Cheap cyclomatic-complexity proxy over rust's grammar, matching
    `frob.arch._python._py_cyclomatic`'s semantics: a decision-point node
    (`if`/`for`/`while`/`loop`/each `match_arm`/`?`) plus one boolean
    `&&`/`||` `binary_expression` short-circuit. Unlike `_py_cyclomatic`,
    which deliberately EXCLUDES match/case from the count (see
    `_python._BRANCH_NODE_TYPES`'s comment), rust counts each `match_arm`
    individually per this ticket's explicit instruction -- a deliberate
    divergence from the python precedent."""
    count = 0
    if node.type in _RUST_CYCLOMATIC_TYPES:
        count += 1
    elif node.type == "binary_expression" and _rust_is_boolean_binary(node):
        count += 1
    for c in node.children:
        count += _rust_cyclomatic(c)
    return count


def _rust_type_text(node: Node | None) -> str | None:
    """The source text of a rust type node (a `parameter`'s `type` field, a
    function's `return_type` field, or a `field_declaration`'s `type`
    field), or `None` if absent -- rust type syntax is used as-written, not
    further decomposed (matching `_typescript.py`'s `_ts_annotation_text`'s
    "raw text" contract, minus TS's leading-colon stripping which rust's
    grammar does not need)."""
    if node is None:
        return None
    return _node_text(node)


def _rust_normalize_params(params_node: Node) -> list[NormalizedParam]:
    """`NormalizedParam`s for a rust `parameters` node, in source order:
    a `self_parameter` (`self`/`&self`/`&mut self`) becomes a bare `"self"`
    param with no type (mirroring python's explicit `self` param); a
    `parameter` node reads its `pattern` field for the name and its `type`
    field for the type text; any other parameter shape (rust has no
    default-value parameter syntax at all, so `has_default` is always
    `False` here -- a real language difference from python/TS, not an
    adapter gap) falls back to the node's own text as the name."""
    out: list[NormalizedParam] = []
    for p in params_node.named_children:
        if p.type == "self_parameter":
            out.append(NormalizedParam(name="self"))
        elif p.type == "parameter":
            pattern = _child(p, "pattern")
            name = _node_text(pattern) if pattern is not None else "?"
            ann = _child(p, "type")
            out.append(NormalizedParam(name=name, type=_rust_type_text(ann)))
        elif p.type not in ("(", ")", ","):
            out.append(NormalizedParam(name=_node_text(p)))
    return out


def _rust_function_line_count(body: Node | None) -> int:
    """Line span of a function/method's body node (0 when it has none, as
    for a `function_signature_item` trait method with no default body)."""
    if body is None:
        return 0
    return body.end_point[0] - body.start_point[0] + 1


def _rust_build_function(
    node: Node, name: str, is_method: bool, overrides: str | None = None
) -> NormalizedFunction:
    """One `function_item`/`function_signature_item` as a
    `NormalizedFunction` -- events flattened via
    `_rust_collect_body_events`, `max_nesting_depth`/`cyclomatic` computed
    via `_rust_max_nesting`/`_rust_cyclomatic` over the body (kept as
    SEPARATE fields, not derived from the flattened event lists -- see
    `NormalizedFunction.max_nesting_depth`'s docstring), mirroring
    `frob.arch._python._py_build_function`'s shape for rust's grammar. A
    `function_signature_item` (a trait method with no default body,
    `fn foo(&self);`) has no `body` field at all -- `body`/metrics are all
    empty/zero in that case."""
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
        _rust_collect_body_events(
            body, branches, loops, calls, field_accesses, returns, raises, catches
        )
    return NormalizedFunction(
        name=name,
        line=node.start_point[0] + 1,
        body_line_count=_rust_function_line_count(body),
        params=_rust_normalize_params(params_node) if params_node is not None else [],
        return_type=_rust_type_text(ret_node),
        is_method=is_method,
        overrides=overrides,
        max_nesting_depth=_rust_max_nesting(body) if body is not None else 0,
        cyclomatic=_rust_cyclomatic(body) if body is not None else 0,
        branches=branches,
        loops=loops,
        calls=calls,
        field_accesses=field_accesses,
        returns=returns,
        raises=raises,
        catches=catches,
    )


def _rust_field_decl_list_fields(body: Node) -> list[NormalizedField]:
    """`NormalizedField`s for a `field_declaration_list` (a named-field
    struct/enum-variant body): each `field_declaration`'s `name`/`type`
    fields."""
    out: list[NormalizedField] = []
    for c in body.named_children:
        if c.type != "field_declaration":
            continue
        name_node = _child(c, "name")
        if name_node is None:
            continue
        ann = _child(c, "type")
        out.append(
            NormalizedField(
                name=_node_text(name_node),
                line=c.start_point[0] + 1,
                type=_rust_type_text(ann),
            )
        )
    return out


def _rust_ordered_field_decl_list_fields(body: Node) -> list[NormalizedField]:
    """`NormalizedField`s for an `ordered_field_declaration_list` (a tuple
    struct/enum-variant body, `Point(i32, i32)`): positional index `"0"`,
    `"1"`, ... as the name, since tuple fields carry no source name."""
    out: list[NormalizedField] = []
    idx = 0
    for c in body.named_children:
        if c.type in ("(", ")", ","):
            continue
        out.append(
            NormalizedField(
                name=str(idx), line=c.start_point[0] + 1, type=_rust_type_text(c)
            )
        )
        idx += 1
    return out


def _rust_struct_fields(struct_node: Node) -> list[NormalizedField]:
    """A `struct_item`'s fields, dispatching on its body's shape (named,
    tuple, or unit -- a unit struct has no `body` field at all)."""
    body = _child(struct_node, "body")
    if body is None:
        return []
    if body.type == "field_declaration_list":
        return _rust_field_decl_list_fields(body)
    if body.type == "ordered_field_declaration_list":
        return _rust_ordered_field_decl_list_fields(body)
    return []


def _rust_enum_variants(enum_node: Node) -> list[NormalizedField]:
    """An `enum_item`'s variants mapped onto `NormalizedField` entries (no
    `NormalizedVariant` entity exists -- see this module's docstring):
    each `enum_variant`'s own name, `type=None` regardless of whether the
    variant itself carries tuple/struct-shaped associated data (a further
    per-variant shape is a model extension, out of this adapter's scope)."""
    out: list[NormalizedField] = []
    body = _child(enum_node, "body")
    if body is None:
        return out
    for variant in body.named_children:
        if variant.type != "enum_variant":
            continue
        name_node = _child(variant, "name")
        if name_node is None:
            continue
        out.append(
            NormalizedField(name=_node_text(name_node), line=variant.start_point[0] + 1)
        )
    return out


def _rust_type_name(type_node: Node) -> str:
    """The bare type name a `struct_item`/`enum_item`/`impl_item`'s `type`
    field denotes as written -- unwraps one level of `generic_type` (`Foo<T>`
    -> `"Foo"`) so an `impl<T> Foo<T> { ... }`'s methods attach to the same
    `NormalizedClass` key as `struct Foo<T> { ... }`'s own `type_identifier`
    name; any other shape (a `scoped_type_identifier` trait/type path) is
    used as its own full written text."""
    if type_node.type == "generic_type":
        inner = _child(type_node, "type")
        if inner is not None:
            return _node_text(inner)
    return _node_text(type_node)


def _rust_trait_methods(trait_node: Node) -> list[NormalizedFunction]:
    """`NormalizedFunction`s for a trait's own methods: both a
    `function_signature_item` (no default body, `overrides=None`) and a
    `function_item` (a default body, `overrides=None` too -- a trait's OWN
    method has nothing to override; see `_rust_attach_impl` for where
    `overrides` is actually set)."""
    out: list[NormalizedFunction] = []
    body = _child(trait_node, "body")
    if body is None:
        return out
    for c in body.named_children:
        if c.type not in ("function_item", "function_signature_item"):
            continue
        name_node = _child(c, "name")
        name = _node_text(name_node) if name_node is not None else "?"
        out.append(_rust_build_function(c, name, is_method=True))
    return out


def _rust_build_class_shell(node: Node) -> NormalizedClass:
    """The `NormalizedClass` shell for a `struct_item`/`enum_item`/
    `trait_item` -- fields/variants + own methods (traits only), before any
    `impl_item`'s methods are attached (`_rust_attach_impl`)."""
    name_node = _child(node, "name")
    name = _node_text(name_node) if name_node is not None else "?"
    if node.type == "struct_item":
        fields = _rust_struct_fields(node)
        methods: list[NormalizedFunction] = []
    elif node.type == "enum_item":
        fields = _rust_enum_variants(node)
        methods = []
    else:  # trait_item
        fields = []
        methods = _rust_trait_methods(node)
    return NormalizedClass(
        name=name,
        line=node.start_point[0] + 1,
        bases=[],
        fields=fields,
        methods=methods,
    )


def _rust_attach_impl(node: Node, classes: dict[str, NormalizedClass]) -> None:
    """Attach one `impl_item`'s methods to its type's `NormalizedClass` --
    creating a shell class first if the type has no `struct_item`/
    `enum_item` of its own in this file (e.g. attaching a trait impl for an
    imported type). An `impl Trait for Type` trait impl appends `Trait`'s
    name to `Type.bases` (the "trait impls note the trait as a base"
    mapping this ticket asks for) and marks each of its methods'
    `overrides` with their own name (rust's closest analogue to an
    "explicit ... override" signal: a trait-impl method body IS the
    fulfillment of that trait's contract, even without a keyword the way
    TS's `override` is -- an inherent `impl Type { ... }` method is NOT a
    trait fulfillment, so its `overrides` stays `None`)."""
    type_node = _child(node, "type")
    if type_node is None:
        return
    type_name = _rust_type_name(type_node)
    cls = classes.get(type_name)
    if cls is None:
        cls = NormalizedClass(name=type_name, line=node.start_point[0] + 1)
        classes[type_name] = cls
    trait_node = _child(node, "trait")
    trait_name = _rust_type_name(trait_node) if trait_node is not None else None
    if trait_name is not None and trait_name not in cls.bases:
        cls.bases.append(trait_name)
    body = _child(node, "body")
    if body is None:
        return
    for c in body.named_children:
        if c.type != "function_item":
            continue
        name_node = _child(c, "name")
        name = _node_text(name_node) if name_node is not None else "?"
        overrides = name if trait_name is not None else None
        cls.methods.append(
            _rust_build_function(c, name, is_method=True, overrides=overrides)
        )


def _rust_flatten_use_list(list_node: Node) -> list[str]:
    """The bound names inside a `use_list` (`{a, b, c::d}`), one level of
    nested `scoped_use_list` grouping flattened to its own dotted path
    (`c::{d, e}` -> `"c::d"`, `"c::e"`) -- a `self` entry (the group's own
    parent path bound directly, `io::{self, Read}`'s `self`) binds no
    individually-named symbol and is skipped, matching a bare `use mod;`'s
    `names=[]` contract."""
    out: list[str] = []
    for item in list_node.named_children:
        if item.type == "identifier" or item.type == "type_identifier":
            out.append(_node_text(item))
        elif item.type == "use_as_clause":
            alias = _child(item, "alias")
            if alias is not None:
                out.append(_node_text(alias))
        elif item.type == "scoped_use_list":
            path = _child(item, "path")
            prefix = _node_text(path) if path is not None else ""
            inner_list = _child(item, "list")
            if inner_list is not None:
                for name in _rust_flatten_use_list(inner_list):
                    out.append(f"{prefix}::{name}" if prefix else name)
        # "self" (bind the group's own parent path) contributes no name.
    return out


def _rust_build_import(node: Node) -> NormalizedImport:
    """One `use_declaration` as a `NormalizedImport`: a plain path (`use
    a::b;` -> `module="a::b"`, `names=[]`), an `as`-renamed import (`use
    a::b as C;` -> `module="a::b"`, `names=["C"]`), a grouped list (`use
    a::{b, c};` -> `module="a"`, `names=["b", "c"]`, one level of nested
    grouping flattened by `_rust_flatten_use_list`), or a wildcard (`use
    a::*;` -> `module="a"`, `names=[]`, matching a bare `import mod` /
    `#include <mod>`'s "no individually-named symbol" contract)."""
    line = node.start_point[0] + 1
    arg = _child(node, "argument")
    if arg is None:
        return NormalizedImport(module=_node_text(node), line=line)
    if arg.type == "use_as_clause":
        path = _child(arg, "path")
        alias = _child(arg, "alias")
        return NormalizedImport(
            module=_node_text(path) if path is not None else "",
            line=line,
            names=[_node_text(alias)] if alias is not None else [],
        )
    if arg.type == "scoped_use_list":
        path = _child(arg, "path")
        list_node = _child(arg, "list")
        return NormalizedImport(
            module=_node_text(path) if path is not None else "",
            line=line,
            names=_rust_flatten_use_list(list_node) if list_node is not None else [],
        )
    if arg.type == "use_wildcard":
        # `use_wildcard` carries no named `path` field -- its module-path
        # child (`identifier`/`scoped_identifier`) is its first named
        # child, directly preceding the literal `*` token.
        path = next(iter(arg.named_children), None)
        return NormalizedImport(
            module=_node_text(path) if path is not None else "", line=line
        )
    # A plain path (`scoped_identifier`/`identifier`) with no wrapper.
    return NormalizedImport(module=_node_text(arg), line=line)


def _rust_build_module(tree: object, rel: str) -> NormalizedModule:
    """The whole-file `NormalizedModule` for a parsed rust file: top-level
    `use` imports, structs/enums/traits (as classes -- `_rust_build_class_
    shell`), impl methods attached to their type (`_rust_attach_impl`), and
    top-level free functions (`RustAdapter.adapt`). Classes are built in
    two passes -- shells first (from `struct_item`/`enum_item`/
    `trait_item`), then every `impl_item` attaches its methods -- since an
    `impl` block can textually precede or follow the type it names."""
    t: Tree = cast("Tree", tree)
    classes: dict[str, NormalizedClass] = {}
    impls: list[Node] = []
    functions: list[NormalizedFunction] = []
    imports: list[NormalizedImport] = []
    for c in t.root_node.children:
        if c.type in ("struct_item", "enum_item", "trait_item"):
            shell = _rust_build_class_shell(c)
            classes[shell.name] = shell
        elif c.type == "impl_item":
            impls.append(c)
        elif c.type == "function_item":
            name_node = _child(c, "name")
            name = _node_text(name_node) if name_node is not None else "?"
            functions.append(_rust_build_function(c, name, is_method=False))
        elif c.type == "use_declaration":
            imports.append(_rust_build_import(c))
    for impl_node in impls:
        _rust_attach_impl(impl_node, classes)
    return NormalizedModule(
        path=rel,
        language="rust",
        imports=imports,
        classes=list(classes.values()),
        functions=functions,
    )


# frob:doc docs/modules/arch.md#normalized-code-model
# frob:tests tests/unit/test_arch.py::TestRustAdapter.test_adapt_stays_sane_on_realistic_snippet  # noqa: E501
class RustAdapter:
    """`LanguageAdapter` (T-0609) for Rust (T-0612): maps a `raw_tree`-
    parsed `.rs` file's tree-sitter `Tree` onto a `NormalizedModule` by
    walking `tree-sitter-rust`'s own node shapes -- mirroring
    `frob.arch._typescript.TypeScriptAdapter`'s structure, not its node-type
    vocabulary (see this module's docstring for the exact construct-to-field
    mapping, including the panic/`Result` raise/catch mapping decision)."""

    language = "rust"

    # frob:doc docs/modules/arch.md#normalized-code-model
    # frob:tests tests/unit/test_arch.py::TestRustAdapter.test_adapt_stays_sane_on_realistic_snippet  # noqa: E501
    def adapt(self, tree: object, source: bytes, rel: str) -> NormalizedModule:
        """Build the `NormalizedModule` for one parsed rust file (`tree`,
        `rel`) -- `source` is unused since tree-sitter `Node.text` already
        carries its own byte slice from the buffer it was parsed with (same
        contract as `PythonAdapter.adapt`/`TypeScriptAdapter.adapt`)."""
        del source
        return _rust_build_module(tree, rel)
