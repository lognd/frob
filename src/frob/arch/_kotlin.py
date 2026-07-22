"""Kotlin architectural adapter: maps a `tree-sitter-kotlin` parse (via
`tree-sitter-language-pack`, wired by T-0613's `frob.lang._walk_kotlin`)
onto the T-0609 `NormalizedModule` shape (T-0614), mirroring
`frob.arch._typescript.TypeScriptAdapter`/`frob.arch._rust.RustAdapter`'s
node-walk structure one-for-one -- mirroring, not reusing, since kotlin's
grammar vocabulary differs throughout. Kept as its OWN module (never
folded into `frob.arch._normalized`, which stays a pure, tree_sitter-free
model module per T-0609's design, and NEVER into `frob.lang._walk_kotlin`,
which is the raw tree-sitter escape hatch T-0613 added, not this
architectural model) -- exactly mirroring `_rust.py`'s placement relative
to `_normalized.py` (the T-0611 review correction every sibling adapter
since has followed).

GRAMMAR QUIRK THAT SHAPES THIS ENTIRE MODULE: unlike
`tree-sitter-typescript`/`tree-sitter-rust`, `tree-sitter-kotlin`'s grammar
(as bundled by `tree-sitter-language-pack`) exposes almost NO named fields
-- `node.child_by_field_name(...)` (`frob.lang.child_by_field`, the
`_child` helper `_typescript.py`/`_rust.py` both lean on throughout)
returns `None` for essentially every node type here, verified
interactively against real parses before writing a line of this module.
Every lookup below is therefore POSITIONAL/type-based (scan `node.
children`/`named_children` for a specific `node.type`, e.g. `_kt_child_of_
type`), not field-based -- a structural difference from every sibling
adapter, not a stylistic one.

Constructs mapped: `class_declaration` (kotlin's grammar uses this SAME
node type for both `class` and `interface` declarations, so both map to
`NormalizedClass` for free; `open`/`data`/`sealed`/`abstract` modifiers are
read but carry no separate `NormalizedClass` field -- matching
`NormalizedClass`'s "as written structure only, no visibility/modifier"
contract every adapter keeps): `delegation_specifier` supertypes/
interfaces (whether wrapping a `constructor_invocation` supertype call or
a bare `user_type` interface reference) -> `bases`; `primary_constructor`
`class_parameter`s that carry a `val`/`var` `binding_pattern_kind` (a
plain, non-`val`/`var` constructor parameter is NOT a property and is
NOT mapped, matching kotlin's own property-vs-parameter distinction) plus
`class_body` `property_declaration`s -> `fields`; `class_body`
`function_declaration`s -> `methods`; `member_modifier` `override` ->
`NormalizedFunction.overrides` (set to the method's own name, the same
"explicit ... language's own override keyword" case `_typescript.py`'s
`override_modifier` handling documents); top-level `function_declaration`s
outside any class; branches (`if_expression`, `conjunction_expression`
(`&&`)/`disjunction_expression` (`||`) as their own boolean-short-circuit
node types -- kotlin's grammar, unlike TS/rust, does not fold these into
a single `binary_expression` with an `operator` field -- and, per this
ticket's explicit "when as branches, each when-entry as a branch arm"
instruction, EVERY `when_entry` counts as its own branch, mirroring
`_rust.py`'s documented `match_arm`-per-branch divergence from
`_python.py`'s deliberate match/case exclusion); loops (`for_statement`,
`while_statement`, `do_while_statement`); calls (`call_expression`, both
bare and `obj.method(...)` dotted forms via a `navigation_expression`
callee); `this.x` field accesses (`navigation_expression` reads,
`directly_assignable_expression` assignment targets for writes -- kotlin's
grammar uses two DIFFERENT node types for the read vs. write shape of the
same `this.x` syntax, unlike TS's single `member_expression` for both);
returns and throws (`jump_expression` with a leading `return`/`throw`
keyword child); `catch_block` -> `NormalizedCatch`; and `import_header` ->
`NormalizedImport` (plain, `as`-aliased, and `*` wildcard forms -- kotlin
has no `{...}` grouped-import syntax, unlike rust's `use a::{b, c};`, so
there is no grouped-import case to map).

NOT mapped (no `NormalizedModule` entity exists for these, or the
construct is out of this ticket's own "open/data/sealed" class scope --
follow-up tickets filed, not folded into this ticket's own scope, matching
the `_typescript.py`/`_rust.py` precedent for the same class of gap):
`enum class`'s `enum_class_body`/`enum_entry` (a DIFFERENT node type from
a regular class's `class_body`, so an enum class comes back with empty
`fields`/`methods` today -- the same "no `NormalizedVariant` entity"
limitation `_rust.py`'s `enum_item` note documents); `object_declaration`
(kotlin's singleton-object syntax -- a distinct node type from
`class_declaration`, not visited by `_kt_build_module`'s top-level walk at
all); a `secondary_constructor` (a class's OWN non-primary `constructor(...)
{ ... }` block, a real function body kotlin's grammar gives its own node
type -- not mapped to `NormalizedFunction`, matching kotlin's own
constructor-vs-method distinction); coroutine `suspend` modifiers and
kotlin-specific null-safety operators (`?.`, `!!`) are read via their
enclosing node's own raw text where relevant (never decomposed further).
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
)
from frob.lang import node_text as _node_text

_KT_LOOP_KINDS = {
    "for_statement": "for",
    "while_statement": "while",
    "do_while_statement": "do-while",
}
_KT_BOOLEAN_TYPES = frozenset({"conjunction_expression", "disjunction_expression"})

#: Node types stopping `_kt_collect_body_events`'s recursion -- a nested
#: function/class becomes its own `NormalizedFunction`/`NormalizedClass`
#: (`_kt_build_function`/`_kt_build_class`), not events folded into the
#: parent, mirroring `_rust_collect_body_events`/`_ts_collect_body_events`.
_KT_BOUNDARY_TYPES = frozenset({"function_declaration", "class_declaration"})


def _kt_child_of_type(node: Node, type_name: str) -> Node | None:
    """The first DIRECT child of `node` with tree-sitter type `type_name`
    -- the positional stand-in every lookup in this module uses instead of
    `frob.lang.child_by_field`, since `tree-sitter-kotlin`'s grammar
    exposes essentially no named fields (see this module's docstring)."""
    for c in node.children:
        if c.type == type_name:
            return c
    return None


def _kt_type_text(node: Node | None) -> str | None:
    """The raw source text of a `user_type` node (a parameter's, return
    type's, or field's type annotation), or `None` if absent -- kotlin
    type syntax (including generics, `List<String>`) is used as-written,
    never further decomposed, matching `_rust_type_text`'s "raw text"
    contract."""
    if node is None:
        return None
    return _node_text(node)


def _kt_if_condition_text(node: Node) -> str:
    """Source text of an `if_expression`'s own test condition: the first
    child immediately following its `(` token (kotlin's grammar has no
    named `condition` field to read directly -- see this module's
    docstring)."""
    seen_paren = False
    for c in node.children:
        if c.type == "(":
            seen_paren = True
            continue
        if seen_paren and c.type != ")":
            return _node_text(c)
    return _node_text(node)


def _kt_when_entry_condition_text(node: Node) -> str:
    """Source text standing for one `when_entry` arm's own test: its
    `when_condition` child's text, or the literal `"else"` for the
    catch-all arm (which carries no `when_condition` child at all)."""
    condition = _kt_child_of_type(node, "when_condition")
    if condition is not None:
        return _node_text(condition)
    if any(c.type == "else" for c in node.children):
        return "else"
    return _node_text(node)


def _kt_call_callee_text(node: Node) -> str:
    """The callee text of a `call_expression`: a bare identifier
    (`f(...)`) or the dotted `obj.method`/`this.method` form
    (`obj.method(...)`, via a `navigation_expression` callee target) --
    always the node's own first child, kotlin's grammar puts the callee
    immediately before its `call_suffix`."""
    if node.children:
        return _node_text(node.children[0])
    return _node_text(node)


def _kt_is_call_target(node: Node) -> bool:
    """Whether `node` (a `navigation_expression`) is itself the leading
    callee child of its parent `call_expression` (`this.compute()` --
    `this.compute` is a method-dispatch target, not a data field read) --
    excluded from `NormalizedFieldAccess` so a call like `this.compute()`
    does not falsely register `compute` as a field read; the call itself
    is still captured via `NormalizedCall` (`_kt_call_callee_text`).
    Mirrors `_rust_is_call_target`'s exact same method-chain false-
    positive fix, ported to kotlin's grammar shape."""
    parent = node.parent
    if parent is None or parent.type != "call_expression":
        return False
    return bool(parent.children) and parent.children[0].id == node.id


def _kt_this_field_name(node: Node) -> str | None:
    """The field name of a `this.x`-shaped node (either a `navigation_
    expression` read or a `directly_assignable_expression` write target),
    or `None` if `node`'s own receiver is not the `this` keyword --
    kotlin's grammar gives the read and write shapes of `this.x` two
    DIFFERENT node types (see this module's docstring), but both share
    the same internal shape: a leading `this_expression` child plus a
    `navigation_suffix` child whose own `simple_identifier` names the
    field."""
    if not node.children or node.children[0].type != "this_expression":
        return None
    suffix = _kt_child_of_type(node, "navigation_suffix")
    if suffix is None:
        return None
    name_node = _kt_child_of_type(suffix, "simple_identifier")
    return _node_text(name_node) if name_node is not None else None


def _kt_jump_keyword(node: Node) -> str | None:
    """The leading keyword (`"return"`/`"throw"`/`"break"`/`"continue"`)
    of a `jump_expression`, or `None` -- kotlin's grammar folds all four
    into one node type, distinguished only by their first child's own
    type."""
    if not node.children:
        return None
    kind = node.children[0].type
    return kind if kind in ("return", "throw", "break", "continue") else None


def _kt_jump_value(node: Node) -> Node | None:
    """The value expression of a `return`/`throw` `jump_expression` (its
    second child), or `None` for a bare `return`/`break`/`continue` with
    no value."""
    return node.children[1] if len(node.children) > 1 else None


def _kt_throw_exception_type(value: Node | None) -> str | None:
    """The exception type name of a `throw` `jump_expression`'s value
    where staticaly determinable (`throw RuntimeException(...)` ->
    `"RuntimeException"`; a bare `throw err` re-throw of an identifier ->
    that identifier's own text), else `None`."""
    if value is None:
        return None
    if value.type == "call_expression":
        target = value.children[0] if value.children else None
        return _node_text(target) if target is not None else None
    if value.type == "simple_identifier":
        return _node_text(value)
    return None


def _kt_catch_exception_type(node: Node) -> str | None:
    """The caught exception type name of a `catch_block`, or `None` if it
    carries no `user_type` (kotlin requires a typed catch parameter, so
    this is defensive, not a real bare-catch case the grammar allows)."""
    user_type = _kt_child_of_type(node, "user_type")
    if user_type is None:
        return None
    type_id = _kt_child_of_type(user_type, "type_identifier")
    return _node_text(type_id) if type_id is not None else _node_text(user_type)


def _kt_collect_body_events(
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
    subtree, stopping at a nested `function_declaration`/`class_
    declaration` boundary -- those become their own `NormalizedFunction`/
    `NormalizedClass` (`_kt_build_function`/`_kt_build_class`), not events
    folded into the parent. Mirrors `_rust_collect_body_events`/
    `_ts_collect_body_events`'s exact walk shape for kotlin's grammar."""
    for c in node.children:
        if c.type in _KT_BOUNDARY_TYPES:
            continue
        if c.type == "if_expression":
            branches.append(
                NormalizedBranch(
                    line=c.start_point[0] + 1, condition_text=_kt_if_condition_text(c)
                )
            )
        elif c.type in _KT_BOOLEAN_TYPES:
            branches.append(
                NormalizedBranch(
                    line=c.start_point[0] + 1, condition_text=_node_text(c)
                )
            )
        elif c.type == "when_entry":
            branches.append(
                NormalizedBranch(
                    line=c.start_point[0] + 1,
                    condition_text=_kt_when_entry_condition_text(c),
                )
            )
        if c.type in _KT_LOOP_KINDS:
            loops.append(
                NormalizedLoop(line=c.start_point[0] + 1, kind=_KT_LOOP_KINDS[c.type])
            )
        if c.type == "call_expression":
            calls.append(
                NormalizedCall(
                    callee=_kt_call_callee_text(c), line=c.start_point[0] + 1
                )
            )
        if c.type == "navigation_expression" and not _kt_is_call_target(c):
            name = _kt_this_field_name(c)
            if name is not None:
                field_accesses.append(
                    NormalizedFieldAccess(
                        name=name, line=c.start_point[0] + 1, is_write=False
                    )
                )
        if c.type == "directly_assignable_expression":
            name = _kt_this_field_name(c)
            if name is not None:
                field_accesses.append(
                    NormalizedFieldAccess(
                        name=name, line=c.start_point[0] + 1, is_write=True
                    )
                )
        if c.type == "jump_expression":
            kind = _kt_jump_keyword(c)
            value = _kt_jump_value(c)
            if kind == "return":
                returns.append(
                    NormalizedReturn(
                        line=c.start_point[0] + 1,
                        value_text=_node_text(value) if value is not None else None,
                    )
                )
            elif kind == "throw":
                raises.append(
                    NormalizedRaise(
                        line=c.start_point[0] + 1,
                        exception_type=_kt_throw_exception_type(value),
                    )
                )
        if c.type == "catch_block":
            catches.append(
                NormalizedCatch(
                    line=c.start_point[0] + 1,
                    exception_type=_kt_catch_exception_type(c),
                )
            )
        _kt_collect_body_events(
            c, branches, loops, calls, field_accesses, returns, raises, catches
        )


_KT_NESTING_TYPES = frozenset(
    {
        "if_expression",
        "for_statement",
        "while_statement",
        "do_while_statement",
        "when_expression",
        "try_expression",
    }
)
_KT_CYCLOMATIC_TYPES = frozenset(
    {
        "if_expression",
        "for_statement",
        "while_statement",
        "do_while_statement",
        "when_entry",
        "catch_block",
    }
)


def _kt_max_nesting(body_node: Node) -> int:
    """Deepest control-flow nesting depth inside a function/method body,
    matching `frob.arch._python._py_max_nesting`'s semantics for kotlin's
    grammar's own nesting node types."""

    def depth(node: Node, current: int) -> int:
        best = current
        for c in node.children:
            nxt = current + 1 if c.type in _KT_NESTING_TYPES else current
            best = max(best, depth(c, nxt))
        return best

    return depth(body_node, 0)


def _kt_cyclomatic(node: Node) -> int:
    """Cheap cyclomatic-complexity proxy over kotlin's grammar, matching
    `frob.arch._python._py_cyclomatic`'s semantics: a decision-point node
    (`if`/`for`/`while`/`do-while`/each `when_entry`/`catch`) plus one
    boolean `&&`/`||` short-circuit (`conjunction_expression`/
    `disjunction_expression`). Counts each `when_entry` individually, the
    same deliberate divergence from `_python.py`'s match/case exclusion
    that `_rust.py`'s `match_arm` counting documents, per this ticket's
    "each when-entry as a branch arm" instruction."""
    count = 0
    if node.type in _KT_CYCLOMATIC_TYPES:
        count += 1
    elif node.type in _KT_BOOLEAN_TYPES:
        count += 1
    for c in node.children:
        count += _kt_cyclomatic(c)
    return count


def _kt_normalize_params(params_node: Node) -> list[NormalizedParam]:
    """`NormalizedParam`s for a kotlin `function_value_parameters` node, in
    source order: each `parameter`'s own `simple_identifier` name and
    `user_type` type text. `has_default=True` when a default value is
    present -- kotlin's grammar attaches a default value's `=` token and
    value node as siblings of the `parameter` node itself INSIDE
    `function_value_parameters` (`(b: Int = 5)`'s `=`/`5` are NOT children
    of `parameter`, unlike TS's `optional_parameter`), so this reads the
    immediately-following sibling rather than `parameter`'s own
    children."""
    out: list[NormalizedParam] = []
    children = params_node.children
    for idx, p in enumerate(children):
        if p.type != "parameter":
            continue
        name_node = _kt_child_of_type(p, "simple_identifier")
        name = _node_text(name_node) if name_node is not None else "?"
        type_node = _kt_child_of_type(p, "user_type")
        has_default = idx + 1 < len(children) and children[idx + 1].type == "="
        out.append(
            NormalizedParam(
                name=name, type=_kt_type_text(type_node), has_default=has_default
            )
        )
    return out


def _kt_function_line_count(body: Node | None) -> int:
    """Line span of a function/method's `function_body` node (0 when it
    has none, as for an interface's bodyless abstract method)."""
    if body is None:
        return 0
    return body.end_point[0] - body.start_point[0] + 1


def _kt_has_override_modifier(node: Node) -> bool:
    """Whether a `function_declaration` carries kotlin's `override`
    keyword -- an explicit, language-native override signal (the same
    "explicit ... override" case `_typescript.py`'s `override_modifier`
    handling documents) that lets `NormalizedFunction.overrides` be set
    with certainty rather than left `None`."""
    modifiers = _kt_child_of_type(node, "modifiers")
    if modifiers is None:
        return False
    return any(
        c.type == "member_modifier" and _node_text(c) == "override"
        for c in modifiers.children
    )


def _kt_build_function(
    node: Node, name: str, is_method: bool, overrides: str | None = None
) -> NormalizedFunction:
    """One `function_declaration` as a `NormalizedFunction` -- events
    flattened via `_kt_collect_body_events`, `max_nesting_depth`/
    `cyclomatic` computed via `_kt_max_nesting`/`_kt_cyclomatic` over the
    body (kept as SEPARATE fields, not derived from the flattened event
    lists -- see `NormalizedFunction.max_nesting_depth`'s docstring),
    mirroring `_rust_build_function`'s shape for kotlin's grammar. The
    return-type `user_type`, if present, is always a DIRECT child of the
    `function_declaration` node itself -- a parameter's own `user_type` is
    nested one level deeper inside `function_value_parameters`, so
    `_kt_child_of_type`'s direct-children-only scan finds the return type
    without confusing the two."""
    params_node = _kt_child_of_type(node, "function_value_parameters")
    ret_node = _kt_child_of_type(node, "user_type")
    body = _kt_child_of_type(node, "function_body")
    branches: list[NormalizedBranch] = []
    loops: list[NormalizedLoop] = []
    calls: list[NormalizedCall] = []
    field_accesses: list[NormalizedFieldAccess] = []
    returns: list[NormalizedReturn] = []
    raises: list[NormalizedRaise] = []
    catches: list[NormalizedCatch] = []
    if body is not None:
        _kt_collect_body_events(
            body, branches, loops, calls, field_accesses, returns, raises, catches
        )
    return NormalizedFunction(
        name=name,
        line=node.start_point[0] + 1,
        body_line_count=_kt_function_line_count(body),
        params=_kt_normalize_params(params_node) if params_node is not None else [],
        return_type=_kt_type_text(ret_node),
        is_method=is_method,
        overrides=overrides,
        max_nesting_depth=_kt_max_nesting(body) if body is not None else 0,
        cyclomatic=_kt_cyclomatic(body) if body is not None else 0,
        branches=branches,
        loops=loops,
        calls=calls,
        field_accesses=field_accesses,
        returns=returns,
        raises=raises,
        catches=catches,
    )


def _kt_property_field(node: Node) -> NormalizedField | None:
    """One `class_body` `property_declaration` as a `NormalizedField`:
    its `variable_declaration`'s own `simple_identifier` name and
    `user_type` type text, or `None` if the name is unreadable."""
    var_decl = _kt_child_of_type(node, "variable_declaration")
    if var_decl is None:
        return None
    name_node = _kt_child_of_type(var_decl, "simple_identifier")
    if name_node is None:
        return None
    type_node = _kt_child_of_type(var_decl, "user_type")
    return NormalizedField(
        name=_node_text(name_node),
        line=node.start_point[0] + 1,
        type=_kt_type_text(type_node),
    )


def _kt_constructor_param_fields(primary_ctor: Node | None) -> list[NormalizedField]:
    """`NormalizedField`s for a `primary_constructor`'s `val`/`var`
    `class_parameter`s -- the "properties -> fields" mapping this ticket
    asks for. A `class_parameter` with NO `binding_pattern_kind` child (no
    `val`/`var` keyword) is a plain constructor parameter, not a property,
    and is deliberately excluded -- kotlin's own property-vs-parameter
    distinction, not an adapter gap."""
    out: list[NormalizedField] = []
    if primary_ctor is None:
        return out
    for c in primary_ctor.named_children:
        if c.type != "class_parameter":
            continue
        if _kt_child_of_type(c, "binding_pattern_kind") is None:
            continue
        name_node = _kt_child_of_type(c, "simple_identifier")
        if name_node is None:
            continue
        type_node = _kt_child_of_type(c, "user_type")
        out.append(
            NormalizedField(
                name=_node_text(name_node),
                line=c.start_point[0] + 1,
                type=_kt_type_text(type_node),
            )
        )
    return out


def _kt_class_fields(body: Node) -> list[NormalizedField]:
    """`NormalizedField`s for every `property_declaration` directly inside
    a `class_body`."""
    out: list[NormalizedField] = []
    for c in body.named_children:
        if c.type != "property_declaration":
            continue
        field = _kt_property_field(c)
        if field is not None:
            out.append(field)
    return out


def _kt_class_methods(body: Node) -> list[NormalizedFunction]:
    """`NormalizedFunction`s for every `function_declaration` directly
    inside a `class_body` (covers both a regular class's and an
    interface's methods, since kotlin's grammar uses `class_body` for
    both -- an interface method with no default implementation simply has
    no `function_body` child, `body_line_count`/metrics all zero)."""
    out: list[NormalizedFunction] = []
    for c in body.named_children:
        if c.type != "function_declaration":
            continue
        name_node = _kt_child_of_type(c, "simple_identifier")
        name = _node_text(name_node) if name_node is not None else "?"
        overrides = name if _kt_has_override_modifier(c) else None
        out.append(_kt_build_function(c, name, is_method=True, overrides=overrides))
    return out


def _kt_delegation_base_name(node: Node) -> str:
    """The base/interface name of one `delegation_specifier` child of a
    `class_declaration`: either a `constructor_invocation`-wrapped
    supertype call (`Animal(name)` -> `"Animal"`) or a bare `user_type`
    interface reference (`Serializable` -> `"Serializable"`) -- both
    map onto `NormalizedClass.bases` as written, matching every sibling
    adapter's "as written, not resolved" contract."""
    target = node.children[0] if node.children else None
    if target is not None and target.type == "constructor_invocation":
        user_type = _kt_child_of_type(target, "user_type")
    elif target is not None and target.type == "user_type":
        user_type = target
    else:
        user_type = _kt_child_of_type(node, "user_type")
    if user_type is None:
        return _node_text(node)
    type_id = _kt_child_of_type(user_type, "type_identifier")
    return _node_text(type_id) if type_id is not None else _node_text(user_type)


def _kt_class_bases(class_node: Node) -> list[str]:
    """Every `delegation_specifier` base/interface name of a
    `class_declaration`, in source order."""
    return [
        _kt_delegation_base_name(c)
        for c in class_node.children
        if c.type == "delegation_specifier"
    ]


def _kt_build_class(node: Node) -> NormalizedClass:
    """One `class_declaration` (regular class OR interface -- kotlin's
    grammar uses one node type for both) as a `NormalizedClass`: bases
    (`_kt_class_bases`), fields (`primary_constructor`'s `val`/`var`
    parameters via `_kt_constructor_param_fields`, plus `class_body`'s own
    `property_declaration`s via `_kt_class_fields`), and methods
    (`_kt_class_methods`)."""
    name_node = _kt_child_of_type(node, "type_identifier")
    name = _node_text(name_node) if name_node is not None else "?"
    primary_ctor = _kt_child_of_type(node, "primary_constructor")
    body = _kt_child_of_type(node, "class_body")
    fields = _kt_constructor_param_fields(primary_ctor)
    methods: list[NormalizedFunction] = []
    if body is not None:
        fields = fields + _kt_class_fields(body)
        methods = _kt_class_methods(body)
    return NormalizedClass(
        name=name,
        line=node.start_point[0] + 1,
        bases=_kt_class_bases(node),
        fields=fields,
        methods=methods,
    )


def _kt_build_import(node: Node) -> NormalizedImport:
    """One `import_header` as a `NormalizedImport`: a plain import (`import
    a.b.C;` -> `module="a.b.C"`, `names=[]`, matching a bare `import mod`'s
    "no individually-named symbol" contract -- kotlin imports exactly one
    symbol per statement, unlike rust's `{...}` grouped form), an
    `as`-aliased import (`import a.b.C as D` -> `module="a.b.C"`,
    `names=["D"]`), or a `*` wildcard (`import a.b.*` -> `module="a.b"`,
    `names=[]`)."""
    line = node.start_point[0] + 1
    ident = _kt_child_of_type(node, "identifier")
    path_text = _node_text(ident) if ident is not None else ""
    alias = _kt_child_of_type(node, "import_alias")
    if alias is not None:
        type_id = _kt_child_of_type(alias, "type_identifier")
        alias_name = _node_text(type_id) if type_id is not None else None
        return NormalizedImport(
            module=path_text, line=line, names=[alias_name] if alias_name else []
        )
    return NormalizedImport(module=path_text, line=line, names=[])


def _kt_build_module(tree: object, rel: str) -> NormalizedModule:
    """The whole-file `NormalizedModule` for a parsed kotlin file: top-
    level `import_header`s (inside the file's single `import_list`),
    top-level `class_declaration`s (classes and interfaces alike), and
    top-level free `function_declaration`s (`KotlinAdapter.adapt`)."""
    t: Tree = cast("Tree", tree)
    classes: list[NormalizedClass] = []
    functions: list[NormalizedFunction] = []
    imports: list[NormalizedImport] = []
    for c in t.root_node.children:
        if c.type == "class_declaration":
            classes.append(_kt_build_class(c))
        elif c.type == "function_declaration":
            name_node = _kt_child_of_type(c, "simple_identifier")
            name = _node_text(name_node) if name_node is not None else "?"
            functions.append(_kt_build_function(c, name, is_method=False))
        elif c.type == "import_list":
            for header in c.named_children:
                if header.type != "import_header":
                    continue
                imports.append(_kt_build_import(header))
    return NormalizedModule(
        path=rel,
        language="kotlin",
        imports=imports,
        classes=classes,
        functions=functions,
    )


# frob:doc docs/modules/arch.md#normalized-code-model
# frob:tests tests/unit/test_arch.py::TestKotlinAdapter.test_adapt_stays_sane_on_realistic_snippet  # noqa: E501
class KotlinAdapter:
    """`LanguageAdapter` (T-0609) for Kotlin (T-0614): maps a `raw_tree`-
    parsed `.kt`/`.kts` file's tree-sitter `Tree` onto a `NormalizedModule`
    by walking `tree-sitter-kotlin`'s own node shapes -- mirroring
    `frob.arch._rust.RustAdapter`'s structure, not its node-type
    vocabulary (see this module's docstring for the exact construct-to-
    field mapping, including the grammar's no-named-fields quirk this
    entire module works around)."""

    language = "kotlin"

    # frob:doc docs/modules/arch.md#normalized-code-model
    # frob:tests tests/unit/test_arch.py::TestKotlinAdapter.test_adapt_stays_sane_on_realistic_snippet  # noqa: E501
    def adapt(self, tree: object, source: bytes, rel: str) -> NormalizedModule:
        """Build the `NormalizedModule` for one parsed kotlin file (`tree`,
        `rel`) -- `source` is unused since tree-sitter `Node.text` already
        carries its own byte slice from the buffer it was parsed with
        (same contract as `RustAdapter.adapt`/`TypeScriptAdapter.adapt`)."""
        del source
        return _kt_build_module(tree, rel)
