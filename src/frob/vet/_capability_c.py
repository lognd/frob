"""C/C++ import/binding-aware capability resolution (T-1420 LARGE001 split,
T-1459 design step 5): macro-alias-table construction, scope-binding, and
resolved-candidate collection for the c-cpp `_DangerousOperation` needle
family, split verbatim out of `frob.vet._capability` (T-0379 lineage).
`_c_binding_capabilities`/`_c_binding_operations`/`_extra_c_binding_
operations` are moved here from their original out-of-order position
(after the kotlin block, T-1459's design note) to keep the C family
cohesive in one file. Every name here is re-exported (or imported back)
by `_capability` so the module's public surface is unchanged."""

# frob:waive INV006 preset="split-carried-prose"
# frob:ticket T-1420
from __future__ import annotations

import re
from pathlib import Path

from frob.lang import node_text, raw_tree

from ._capability_core import ByteSpan, _fully_in_any_span, _needle_matches_resolved
from ._capability_registry import DANGEROUS_OPERATIONS, _DangerousOperation
from ._capability_rust import _record_rust_binding

# T-0379: import/binding-aware resolution for C/C++, the fourth binding
# resolver alongside T-0328 (python) / T-0377 (TS) / T-0378 (rust). C/C++'s
# dominant renaming idiom is the preprocessor, not an import system: `#define
# SYS system` makes `SYS("sh")` a call to `system` with no `"system("`
# substring anywhere in the file's own text, evading the raw-text needle
# scan the same way an aliased python `import`/rust `use` does. Only a
# SIMPLE object-like macro whose value is a single bare identifier is
# resolved (`#define SYS system`) -- a function-like macro (`#define SYS(x)
# system(x)`) is a `preproc_function_def` node, a structurally different
# shape, and is a documented, deliberately out-of-scope limitation here
# (mirrors the T-0378 grouped-`use` limitation note above): a function-like
# macro already re-expands to literal "system(" text at its call site in
# common usage, so the raw-text lexical scan still has a real (if weaker)
# chance at it, unlike the pure-rename case this resolver targets.
#
# A `using NAMESPACE::NAME;` declaration or namespace-qualified call site
# (`fs::system(...)` after `namespace fs = std;`) needs NO special
# resolution here: the registry's own needles are bare substrings
# (`"system("`), which still occur verbatim inside a qualified call --
# `_needle_hits_outside_comments` already catches those lexically. Type-only
# aliases (`typedef`/C++11 `using X = Y;` alias-declarations) do not rename
# a CALLABLE and are out of scope for the same reason.
#
# Shadow-awareness mirrors `_rust_shadowing_scope`'s POSITION-aware
# discipline (T-0378 round 2, T-0339 fail-closed): a local variable or
# function parameter sharing a macro alias's name must not have a call site
# textually BEFORE its own declaration wrongly treated as shadowed. Block
# scoping (nested `compound_statement` scopes each shadowing independently)
# is over-approximated to "the whole enclosing function" -- matching the
# python/rust resolvers' function-granularity, not per-block C scoping;
# documented, not a silent gap.
_C_SCOPE_TYPES = ("function_definition", "translation_unit")

#: sentinel `bound` position meaning "shadows from the very start of the
#: scope" -- used for function PARAMETERS (in scope for the whole body).
#: Mirrors `_RUST_ALWAYS_SHADOWS`.
_C_ALWAYS_SHADOWS = -1

#: macro name -> single bare-identifier alias target regex (T-0379): only
#: matches an object-like macro's fully-stripped value when it is itself a
#: valid identifier -- a function-like macro body, an expression, or a
#: multi-token replacement never matches and is left unresolved (documented
#: limitation, see the T-0379 block comment above).
_C_BARE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _c_macro_alias_table(root_node) -> dict[str, str]:  # noqa: ANN001
    """The file-wide macro-name -> resolved-target binding table (T-0379),
    built from every `preproc_def` (object-like `#define NAME VALUE`) whose
    stripped value is itself a bare identifier -- transitively chased
    (`#define A B` + `#define B system` resolves `A` to `system`) so a
    multi-hop rename still resolves, mirroring `_rust_use_table`'s file-wide
    over-approximation (a function-local `#define` still contributes a
    file-wide binding, since the C preprocessor has no block scope)."""
    raw: dict[str, str] = {}

    def visit(node) -> None:  # noqa: ANN001
        if node.type == "preproc_def":
            name_node = node.child_by_field_name("name")
            value_node = node.child_by_field_name("value")
            if name_node is not None and value_node is not None:
                value = node_text(value_node).strip()
                if _C_BARE_IDENTIFIER_RE.match(value):
                    raw[node_text(name_node)] = value
        for child in node.children:
            visit(child)

    visit(root_node)

    resolved: dict[str, str] = {}
    for name in raw:
        seen: set[str] = set()
        cur = name
        while cur in raw and cur not in seen:
            seen.add(cur)
            cur = raw[cur]
        resolved[name] = cur
    return resolved


def _c_declared_name(node) -> str | None:  # noqa: ANN001
    """The identifier a C/C++ declarator node ultimately names, following
    its `declarator` field through any `pointer_declarator`/`array_
    declarator`/`init_declarator`/reference wrapper down to the innermost
    plain `identifier` leaf -- e.g. `int *system3 = 0` (`init_declarator` ->
    `pointer_declarator` -> `identifier`) resolves to `"system3"`. `None`
    for a declarator shape with no reachable identifier (e.g. an abstract
    declarator).

    T-0662: also descends through a `parenthesized_declarator` (the `(*f)`
    wrapper every function-pointer declarator carries, e.g. `void (*f)
    (const char*)`) -- this node has NO `declarator` FIELD at all (its
    inner content is a single unlabeled named child), so the plain
    field-walk loop below would otherwise stop here and return `None` for
    every function-pointer variable/parameter/struct-field name, silently
    breaking function-pointer alias resolution."""
    # PERF006: rewritten from tail recursion to an explicit loop -- Python
    # has no TCO, and the walk depth tracks a declarator chain's nesting
    # (pointer/array/init/reference wrappers), which is not statically
    # bounded, so a loop removes the stack-overflow hazard outright rather
    # than merely proving a depth bound.
    while node is not None:
        if node.type == "identifier":
            return node_text(node)
        next_node = node.child_by_field_name("declarator")
        if next_node is None and node.type == "parenthesized_declarator":
            named = [c for c in node.children if c.is_named]
            next_node = named[0] if named else None
        node = next_node
    return None


#: `declaration` node direct-child types `_c_collect_declaration_names`
#: treats as a declarator worth resolving through `_c_declared_name` (T-
#: 0662 extends T-0379's original `identifier`/`init_declarator`-only pair
#: with the bare, uninitialized declarator shapes an ordinary variable
#: declaration wraps its name in when there is no `= value` at all --
#: `void (*f)(const char*);` parses its declared name directly under a
#: `function_declarator` -> `parenthesized_declarator` -> `pointer_
#: declarator` chain, never an `init_declarator`, since tree-sitter-c only
#: wraps a declarator in `init_declarator` when an initializer is present).
#: Without this, a forward-declared function-pointer variable's later
#: `f = &do_exec;` assignment could never resolve: `_c_shadowing_scope`
#: would never find `f` bound anywhere, so `_record_c_assignment_alias`'s
#: scope lookup (keyed off THAT SAME shadow check) always misses.
_C_DECLARATOR_CHILD_TYPES = (
    "identifier",
    "init_declarator",
    "function_declarator",
    "pointer_declarator",
    "array_declarator",
    "parenthesized_declarator",
)


def _c_collect_declaration_names(node, position: int, bound: dict[str, int]) -> None:  # noqa: ANN001
    """Add every name a `declaration` node binds to `bound` at `position`
    (T-0379, mirrors `_collect_rust_let_target`'s job at C's coarser
    grammar grain) -- a plain `declaration` node's direct children are a
    bare `identifier` (`int x, y;`), an `init_declarator` (`int x = 5;`),
    or (T-0662) an uninitialized declarator wrapper chain (`void (*f)
    (const char*);` -- see `_C_DECLARATOR_CHILD_TYPES`), so all three
    shapes are scanned at the top level without needing to recurse past
    them.

    T-0663: a C++ structured-binding `init_declarator` (`auto [a, b] =
    ...;`) is a FOURTH shape -- its `declarator` field is a `structured_
    binding_declarator` wrapping MULTIPLE names, not the single name every
    other declarator chain resolves to via `_c_declared_name`, so it needs
    its own multi-name branch here rather than fitting the single-name
    loop below."""
    for child in node.children:
        if child.type == "init_declarator":
            inner = child.child_by_field_name("declarator")
            if inner is not None and inner.type == "structured_binding_declarator":
                for name_node in inner.children:
                    if name_node.type == "identifier":
                        _record_rust_binding(bound, node_text(name_node), position)
                continue
        if child.type in _C_DECLARATOR_CHILD_TYPES:
            name = _c_declared_name(child)
            if name:
                _record_rust_binding(bound, name, position)


def _c_scope_bind_step(node, is_top: bool, bound: dict[str, int]) -> bool:  # noqa: ANN001
    """Handle ONE node during `_c_scope_bound_names`'s walk: add whatever
    name(s) `node` binds directly to `bound` (`_C_ALWAYS_SHADOWS` for a
    function parameter, the enclosing `declaration`'s own `start_byte` for
    a local variable, T-0379 mirrors T-0378 round 2's position-aware
    discipline), and report whether the walk should recurse into `node`'s
    children (False at a nested function boundary or once a binding node
    has been fully handled -- mirrors `_rust_scope_bind_step`'s job)."""
    node_type = node.type
    if not is_top and node_type == "function_definition":
        return False
    if node_type in ("parameter_declaration", "optional_parameter_declaration"):
        # T-0663: `optional_parameter_declaration` (C++'s default-valued
        # parameter, e.g. `void call(void(*cb)(const char*) = system)`) is
        # a DIFFERENT node type from plain `parameter_declaration` -- both
        # bind their name for the whole function body the same way.
        name = _c_declared_name(node.child_by_field_name("declarator"))
        if name:
            _record_rust_binding(bound, name, _C_ALWAYS_SHADOWS)
        return False
    if node_type == "declaration":
        _c_collect_declaration_names(node, node.start_byte, bound)
        return False
    return True


def _c_scope_bound_names(scope_node) -> dict[str, int]:  # noqa: ANN001
    """Every name bound within `scope_node` (a `function_definition`/
    `translation_unit` node, T-0379), mapped to the byte position from
    which it starts shadowing an enclosing macro alias -- function
    parameters and local variable declarations -- WITHOUT recursing into a
    nested function's own body. Mirrors `_rust_scope_bound_names`'s
    position-aware (`name -> start_byte`) shape, over-approximated to
    function granularity rather than per-`compound_statement` C block
    scoping (documented, see the T-0379 block comment above)."""
    bound: dict[str, int] = {}

    def walk(node, is_top: bool) -> None:  # noqa: ANN001
        if _c_scope_bind_step(node, is_top, bound):
            for child in node.children:
                walk(child, False)

    walk(scope_node, True)
    return bound


def _c_shadowing_scope(name: str, site, scope_cache: dict[int, dict[str, int]]):  # noqa: ANN001, ANN201
    """The nearest enclosing `_C_SCOPE_TYPES` node that binds `name` at or
    before `site`'s own `start_byte` (per `_c_scope_bound_names`, cached per
    scope node), or `None` if no enclosing scope shadows the macro alias at
    this position -- the T-0379 shadow check every resolution goes through,
    mirroring `_rust_shadowing_scope`'s walk/cache shape and position-aware
    (fail-closed, T-0339) semantics."""
    cur = site.parent
    while cur is not None:
        if cur.type in _C_SCOPE_TYPES:
            key = cur.id
            cached = scope_cache.get(key)
            if cached is None:
                cached = _c_scope_bound_names(cur)
                scope_cache[key] = cached
            position = cached.get(name)
            if position is not None and site.start_byte >= position:
                return cur
            if cur.type == "translation_unit":
                break
        cur = cur.parent
    return None


# frob:ticket T-0662
def _resolve_c_identifier(
    node,
    alias_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    var_alias_table: dict[int, dict[str, str]] | None = None,
) -> str | None:  # noqa: ANN001
    """Resolve a bare `identifier` call-target node to its macro-aliased
    target (T-0379), or (T-0662) a scope-local `var_alias_table` entry when
    it IS locally shadowed AT THIS POSITION -- mirrors `_resolve_rust_
    identifier`'s shadowed/unshadowed split exactly: a name bound by an
    enclosing scope (a local function-pointer variable) can ONLY resolve
    through the alias table (never the file-wide macro table, which would
    wrongly let a same-named macro leak through a local variable); an
    unshadowed name resolves through the macro table as before."""
    name = node_text(node)
    scope = _c_shadowing_scope(name, node, scope_cache)
    if scope is not None:
        if var_alias_table is None:
            return None
        return var_alias_table.get(scope.id, {}).get(name)
    return alias_table.get(name)


def _c_enclosing_scope(node):  # noqa: ANN001, ANN201
    """The nearest `_C_SCOPE_TYPES` ancestor of `node` (T-0662), mirroring
    `_enclosing_rust_scope` -- used by `_record_c_declaration_alias`/
    `_record_c_assignment_alias` to find which scope a function-pointer
    variable's name binds into."""
    cur = node.parent
    while cur is not None:
        if cur.type in _C_SCOPE_TYPES:
            return cur
        cur = cur.parent
    return None


def _resolve_c_alias_source(
    node,
    macro_alias_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    var_alias_table: dict[int, dict[str, str]],
):  # noqa: ANN001, ANN201
    """Resolve the RHS of a C function-pointer BINDING (an `init_declarator`
    value, an `assignment_expression`'s `right`, or a struct/array
    initializer element) to the ultimate target name (T-0662): unwraps a
    single `&identifier` address-of expression (the `f = &do_exec;`
    assignment-of-a-function-pointer taxonomy row), then, if the identifier
    is itself locally shadowed, chases through `var_alias_table` (so `Handler
    h = f;` where `f` already aliases `do_exec` resolves transitively, same
    document-order soundness argument as `_build_rust_alias_table`); if NOT
    locally shadowed, the identifier names a global/library function
    DIRECTLY (`f = system;`) -- resolved through the macro table if aliased,
    else the bare identifier text itself is the target (unlike `_resolve_c_
    identifier`'s call-site contract, an unaliased, unshadowed RHS name IS
    the answer here, not `None`: it is what `f` now points to). Returns
    `None` for any other RHS shape (not a bare-identifier-or-&identifier
    binding), the "not itself a static-resolvable function reference"
    fail-closed default (T-0339)."""
    if node.type == "pointer_expression":
        inner = node.child_by_field_name("argument")
        if inner is None or inner.type != "identifier":
            return None
        node = inner
    if node.type != "identifier":
        return None
    name = node_text(node)
    scope = _c_shadowing_scope(name, node, scope_cache)
    if scope is not None:
        return var_alias_table.get(scope.id, {}).get(name)
    return macro_alias_table.get(name, name)


def _record_c_field_alias(
    initializer_list,  # noqa: ANN001 -- tree_sitter.Node
    macro_alias_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    var_alias_table: dict[int, dict[str, str]],
    field_alias_table: dict[str, str],
) -> None:
    """Bind every `.field = target` designated initializer inside
    `initializer_list` to `field_alias_table` (T-0662, taxonomy "struct
    field holding a function pointer, statically initialized" row:
    `struct Ops ops = { .run = system }; ops.run(x);`) -- keyed by FIELD
    NAME only (best-effort, object-identity-BY-NAME, matching T-0659's
    disclosed attribute-rebind posture: two different struct variables with
    a same-named function-pointer field are not distinguished).

    `field_designator`'s own `field_identifier` child carries NO tree-
    sitter FIELD NAME at all (verified interactively -- `.field_designator.
    child_by_field_name("field")` returns `None` unconditionally, unlike
    `initializer_pair`'s own `designator`/`value` fields, which ARE
    labeled), so it is plucked positionally (its one named child) rather
    than via `child_by_field_name`, mirroring `frob.arch._kotlin`'s
    documented "this grammar exposes almost no named fields" posture for
    the specific nodes that lack one."""
    for element in initializer_list.children:
        if element.type != "initializer_pair":
            continue
        designator = element.child_by_field_name("designator")
        value = element.child_by_field_name("value")
        if designator is None or value is None or designator.type != "field_designator":
            continue
        named = [c for c in designator.children if c.is_named]
        if not named or named[0].type != "field_identifier":
            continue
        field_id = named[0]
        resolved = _resolve_c_alias_source(
            value, macro_alias_table, scope_cache, var_alias_table
        )
        if resolved is not None:
            field_alias_table.setdefault(node_text(field_id), resolved)


def _record_c_array_alias(
    initializer_list,  # noqa: ANN001 -- tree_sitter.Node
    array_name: str,
    macro_alias_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    var_alias_table: dict[int, dict[str, str]],
    array_alias_table: dict[tuple[str, int], str],
) -> None:
    """Bind every positional element of `initializer_list` to `array_alias_
    table` keyed by `(array_name, 0-based index)` (T-0662, taxonomy "array
    of function pointers, constant index" row: `void (*tbl[])(const char*)
    = { system }; tbl[0](x);`)."""
    index = 0
    for element in initializer_list.children:
        if not element.is_named:
            continue
        resolved = _resolve_c_alias_source(
            element, macro_alias_table, scope_cache, var_alias_table
        )
        if resolved is not None:
            array_alias_table.setdefault((array_name, index), resolved)
        index += 1


def _record_c_structured_binding_alias(
    declarator,  # noqa: ANN001 -- tree_sitter.Node (structured_binding_declarator)
    value,  # noqa: ANN001 -- tree_sitter.Node
    macro_alias_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    var_alias_table: dict[int, dict[str, str]],
) -> None:
    """Bind each plain-identifier element of a C++17 structured-binding
    declarator (T-0663, taxonomy "structured bindings" row: `auto [a, b] =
    std::pair{system, 0}; a(x);`) to its POSITIONALLY corresponding element
    of `value`'s own initializer-list elements -- mirrors T-0661's rust
    tuple-destructure/T-0659's python tuple-unpack pattern. `value` is
    typically a `compound_literal_expression` (`std::pair{...}`) wrapping
    an `initializer_list`; any other RHS shape (a plain variable, a
    function call) has no positional element list to walk and is skipped,
    same fail-closed posture as the array/field alias tables."""
    source = value
    if source.type == "compound_literal_expression":
        source = source.child_by_field_name("value") or source
    if source.type != "initializer_list":
        return
    scope = _c_enclosing_scope(declarator)
    if scope is None:
        return
    left_elements = [c for c in declarator.children if c.is_named]
    right_elements = [c for c in source.children if c.is_named]
    scope_aliases = var_alias_table.setdefault(scope.id, {})
    for left_el, right_el in zip(left_elements, right_elements, strict=False):
        if left_el.type != "identifier":
            continue
        resolved = _resolve_c_alias_source(
            right_el, macro_alias_table, scope_cache, var_alias_table
        )
        if resolved is not None:
            scope_aliases.setdefault(node_text(left_el), resolved)


def _record_c_default_param_alias(
    node,  # noqa: ANN001 -- tree_sitter.Node (optional_parameter_declaration)
    macro_alias_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    var_alias_table: dict[int, dict[str, str]],
) -> None:
    """If `node` (a C++ `optional_parameter_declaration`, a default-valued
    function parameter) has a resolvable default value, record it into
    `var_alias_table` keyed by the parameter's OWN enclosing function scope
    (T-0663, taxonomy "default argument forwarding a callable" row: `void
    call(void(*cb)(const char*) = system) { cb(x); }`) -- `_c_scope_bind_
    step` (T-0663) already binds this parameter's name for the WHOLE
    function body via `_C_ALWAYS_SHADOWS`, so keying the alias entry at the
    SAME enclosing-function scope (via `_c_enclosing_scope`, not `_c_
    shadowing_scope` -- unlike `_record_c_assignment_alias`, a parameter's
    binding scope and its declaration's immediately-enclosing scope are
    ALWAYS the same node) guarantees the later call-site lookup agrees."""
    declarator = node.child_by_field_name("declarator")
    default_value = node.child_by_field_name("default_value")
    if declarator is None or default_value is None:
        return
    name = _c_declared_name(declarator)
    if name is None:
        return
    scope = _c_enclosing_scope(node)
    if scope is None:
        return
    resolved = _resolve_c_alias_source(
        default_value, macro_alias_table, scope_cache, var_alias_table
    )
    if resolved is not None:
        var_alias_table.setdefault(scope.id, {}).setdefault(name, resolved)


def _record_c_declaration_alias(
    node,  # noqa: ANN001 -- tree_sitter.Node (init_declarator)
    macro_alias_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    var_alias_table: dict[int, dict[str, str]],
    field_alias_table: dict[str, str],
    array_alias_table: dict[tuple[str, int], str],
) -> None:
    """If `node` (an `init_declarator`) binds a function-pointer variable
    (T-0662, taxonomy "function-pointer variable init from named function"
    and "`typedef`'d function-pointer type" rows -- both reduce to this
    SAME declaration shape; a `typedef` only renames the declared TYPE, not
    the binding grammar, so no separate typedef-specific branch is needed,
    mirroring T-0661's identical finding for rust's `type`/`let` overlap),
    a struct designated initializer (delegates to `_record_c_field_alias`),
    an array-of-function-pointers initializer (delegates to `_record_c_
    array_alias`), or (T-0663) a C++ structured-binding declaration
    (delegates to `_record_c_structured_binding_alias`) -- record it into
    the matching table."""
    value = node.child_by_field_name("value")
    declarator = node.child_by_field_name("declarator")
    if value is None or declarator is None:
        return
    if declarator.type == "structured_binding_declarator":
        _record_c_structured_binding_alias(
            declarator, value, macro_alias_table, scope_cache, var_alias_table
        )
        return
    name = _c_declared_name(declarator)
    if name is None:
        return
    if value.type == "initializer_list":
        elements = [c for c in value.children if c.is_named]
        if elements and elements[0].type == "initializer_pair":
            _record_c_field_alias(
                value,
                macro_alias_table,
                scope_cache,
                var_alias_table,
                field_alias_table,
            )
        else:
            _record_c_array_alias(
                value,
                name,
                macro_alias_table,
                scope_cache,
                var_alias_table,
                array_alias_table,
            )
        return
    scope = _c_enclosing_scope(node)
    if scope is None:
        return
    resolved = _resolve_c_alias_source(
        value, macro_alias_table, scope_cache, var_alias_table
    )
    if resolved is not None:
        var_alias_table.setdefault(scope.id, {}).setdefault(name, resolved)


def _record_c_assignment_alias(
    node,  # noqa: ANN001 -- tree_sitter.Node (assignment_expression)
    macro_alias_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    var_alias_table: dict[int, dict[str, str]],
) -> None:
    """If `node` (an `assignment_expression`) rebinds a plain identifier to
    a resolvable function reference, record it into `var_alias_table` (T-
    0662, taxonomy "assignment of a function pointer" row: `f = &do_exec;
    f(x);` -- distinct from `_record_c_declaration_alias`'s `init_
    declarator` shape since a bare assignment has no `declarator` field at
    all, just `left`/`right`).

    KEYED BY `_c_shadowing_scope`, NOT `_c_enclosing_scope`: an assignment
    can rebind a variable declared in an OUTER scope (the common shape --
    `void (*f)(const char*);` at file scope, `f = &do_exec;` inside some
    function body). Recording under the assignment's own immediately-
    enclosing scope (as `_record_c_declaration_alias` does for a fresh
    declaration) would key the alias under the WRONG scope id here --
    `_resolve_c_identifier`'s later call-site lookup walks `_c_shadowing_
    scope` to find where `f`'s NAME is actually bound (the file-scope
    declaration), not where this particular assignment happens to sit.
    Using the SAME `_c_shadowing_scope` call here guarantees the recording
    and lookup scopes always agree; an identifier with no reachable
    declaration at all is not recorded, fail-closed."""
    left = node.child_by_field_name("left")
    right = node.child_by_field_name("right")
    if left is None or right is None or left.type != "identifier":
        return
    name = node_text(left)
    scope = _c_shadowing_scope(name, left, scope_cache)
    if scope is None:
        return
    resolved = _resolve_c_alias_source(
        right, macro_alias_table, scope_cache, var_alias_table
    )
    if resolved is not None:
        var_alias_table.setdefault(scope.id, {}).setdefault(name, resolved)


def _build_c_alias_tables(
    root_node,  # noqa: ANN001 -- tree_sitter.Node
    macro_alias_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
) -> tuple[dict[int, dict[str, str]], dict[str, str], dict[tuple[str, int], str]]:
    """(var_alias_table, field_alias_table, array_alias_table) -- T-0662,
    the C sibling of `_build_rust_alias_table`/`_build_py_alias_table`/
    `_build_ts_alias_table`, covering the taxonomy's remaining static-
    resolvable C rows beyond T-0379's macro table: function-pointer
    variable init (`init_declarator`), typedef'd function-pointer type
    (same shape, no separate branch), assignment of a function pointer
    (`assignment_expression`), struct field static init, and array-of-
    function-pointers constant-index init. Extended (T-0663) with two
    C++-only `init_declarator`-ADJACENT node types that need their own
    dispatch branch: `optional_parameter_declaration` (a default-valued
    function parameter, which has no `init_declarator` wrapper at all --
    `declarator`/`default_value` are fields directly on the parameter node
    itself) and structured bindings (delegated from `_record_c_declaration_
    alias`'s own `init_declarator` branch once it sees a `structured_
    binding_declarator`, since that shape IS still an `init_declarator`,
    just with a different declarator kind). `std::function<...>`-typed and
    C++11 `using X = ...;` type-aliased function-pointer variables need NO
    separate branch either -- both still reduce to a plain `init_
    declarator` (verified interactively: the TYPE annotation differs, the
    binding grammar does not), same "the T-0609 typedef finding also holds
    for C++'s two extra spellings" logic as `_record_c_declaration_alias`'s
    own typedef case. The walk visits declarations/assignments/parameters
    in source (document) order, so a chained alias (`f = system; g = f;`)
    resolves transitively the same way the rust/py/TS tables do."""
    var_alias_table: dict[int, dict[str, str]] = {}
    field_alias_table: dict[str, str] = {}
    array_alias_table: dict[tuple[str, int], str] = {}

    def visit(node) -> None:  # noqa: ANN001
        if node.type == "init_declarator":
            _record_c_declaration_alias(
                node,
                macro_alias_table,
                scope_cache,
                var_alias_table,
                field_alias_table,
                array_alias_table,
            )
        elif node.type == "assignment_expression":
            _record_c_assignment_alias(
                node, macro_alias_table, scope_cache, var_alias_table
            )
        elif node.type == "optional_parameter_declaration":
            _record_c_default_param_alias(
                node, macro_alias_table, scope_cache, var_alias_table
            )
        for child in node.children:
            visit(child)

    visit(root_node)
    return var_alias_table, field_alias_table, array_alias_table


def _c_call_target_resolved(
    func,  # noqa: ANN001 -- tree_sitter.Node
    alias_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    var_alias_table: dict[int, dict[str, str]],
    field_alias_table: dict[str, str],
    array_alias_table: dict[tuple[str, int], str],
) -> str | None:
    """Resolve one `call_expression`'s `function` node through whichever
    C/C++ shape it is (T-0662): a bare identifier (macro/variable alias,
    T-0379/T-0662), a `field_expression` (`ops.run(x)`, struct field alias),
    or a `subscript_expression` with a CONSTANT integer index
    (`tbl[0](x)`, array alias) -- a non-constant index is the taxonomy's
    own documented `runtime-opaque` row and is correctly left unresolved."""
    if func.type == "identifier":
        return _resolve_c_identifier(func, alias_table, scope_cache, var_alias_table)
    if func.type == "field_expression":
        field = func.child_by_field_name("field")
        if field is not None and field.type == "field_identifier":
            return field_alias_table.get(node_text(field))
        return None
    if func.type == "subscript_expression":
        base = func.child_by_field_name("argument")
        index = func.child_by_field_name("index")
        if base is None or base.type != "identifier":
            return None
        if index is None or index.type != "number_literal":
            return None
        try:
            index_value = int(node_text(index))
        except ValueError:
            return None
        except (KeyError, TypeError):
            # A `number_literal` node's text failing to resolve to a
            # plain int is the same "cannot resolve this array-alias
            # index" outcome as the ValueError branch, not a crash of the
            # whole C/C++ call-target resolver (EXHAUST001/EXHAUST002,
            # T-1371).
            return None
        except Exception:
            return None
        return array_alias_table.get((node_text(base), index_value))
    return None


def _collect_c_candidates(
    node,
    alias_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    candidates: list[tuple[str, int, int]],
    var_alias_table: dict[int, dict[str, str]] | None = None,
    field_alias_table: dict[str, str] | None = None,
    array_alias_table: dict[tuple[str, int], str] | None = None,
) -> None:  # noqa: ANN001
    """Recursively walk `node`, appending `(resolved, start_byte, end_byte)`
    to `candidates` for every `call_expression` whose `function` resolves
    through `alias_table` (T-0379 macro aliasing), `var_alias_table` (T-0662
    function-pointer variable/assignment aliasing), `field_alias_table`
    (T-0662 struct field), or `array_alias_table` (T-0662 constant-index
    array element) -- mirrors `_collect_rust_candidates`'s job."""
    if node.type == "call_expression":
        func = node.child_by_field_name("function")
        if func is not None:
            resolved = _c_call_target_resolved(
                func,
                alias_table,
                scope_cache,
                var_alias_table or {},
                field_alias_table or {},
                array_alias_table or {},
            )
            if resolved is not None:
                candidates.append((resolved, node.start_byte, node.end_byte))
    for child in node.children:
        _collect_c_candidates(
            child,
            alias_table,
            scope_cache,
            candidates,
            var_alias_table,
            field_alias_table,
            array_alias_table,
        )


def _c_resolved_candidates(path: Path) -> tuple[tuple[str, int, int], ...]:
    """Every `(resolved_name, start_byte, end_byte)` this C/C++ file's call
    sites resolve to through its macro alias table (T-0379), POSITION-aware
    enclosing-scope shadow check, and (T-0662) function-pointer variable/
    assignment/struct-field/array alias tables. Empty for a non-c/cpp file,
    an unparseable file, or one `frob.lang` has no grammar for -- degrades
    to the pre-existing lexical-only scan, never raises."""
    parsed = raw_tree(path)
    if parsed.is_err:
        return ()
    tree, _source, language_label = parsed.danger_ok
    if language_label not in ("c", "cpp"):
        return ()

    alias_table = _c_macro_alias_table(tree.root_node)
    scope_cache: dict[int, dict[str, int]] = {}
    var_alias_table, field_alias_table, array_alias_table = _build_c_alias_tables(
        tree.root_node, alias_table, scope_cache
    )
    candidates: list[tuple[str, int, int]] = []
    _collect_c_candidates(
        tree.root_node,
        alias_table,
        scope_cache,
        candidates,
        var_alias_table,
        field_alias_table,
        array_alias_table,
    )
    return tuple(candidates)


def _c_binding_capabilities(
    path: Path,
    table: dict[str, tuple[str, ...]],
    comment_spans: tuple[ByteSpan, ...],
) -> set[str]:
    """Capability kinds observed via C/C++ macro-alias-aware resolution only
    (T-0379) -- the union of every registry needle that matches a resolved
    call target, for sites outside a comment span. Merged into `scan_file_
    capabilities`'s lexical result; adds recall (macro-renamed dangerous
    calls) without touching the existing raw-text path at all. Mirrors
    `_rust_binding_capabilities`."""
    found: set[str] = set()
    for resolved, start, end in _c_resolved_candidates(path):
        if _fully_in_any_span(start, end, comment_spans):
            continue
        for capability, needles in table.items():
            if capability in found:
                continue
            if any(_needle_matches_resolved(needle, resolved) for needle in needles):
                found.add(capability)
    return found


def _c_binding_operations(
    path: Path, comment_spans: tuple[ByteSpan, ...]
) -> tuple[_DangerousOperation, ...]:
    """`DANGEROUS_OPERATIONS` c-cpp entries observed via macro-alias-aware
    resolution only (T-0379) -- `_scan_file_operations`'s resolver-backed
    sibling to `_c_binding_capabilities`. Mirrors `_rust_binding_
    operations`."""
    candidates = _c_resolved_candidates(path)
    if not candidates:
        return ()
    matched: list[_DangerousOperation] = []
    for entry in DANGEROUS_OPERATIONS:
        if entry.language != "c-cpp" or not entry.needles:
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


def _extra_c_binding_operations(
    path: Path,
    comment_spans: tuple[ByteSpan, ...],
    already_matched: list[_DangerousOperation],
) -> list[_DangerousOperation]:
    """`_c_binding_operations` entries not already present in
    `already_matched` (T-0379) -- C/C++ sibling of `_extra_rust_binding_
    operations`, same set-based dedupe."""
    seen = set(already_matched)
    extra: list[_DangerousOperation] = []
    for entry in _c_binding_operations(path, comment_spans):
        if entry not in seen:
            extra.append(entry)
            seen.add(entry)
    return extra
