"""Kotlin import/binding-aware capability resolution (T-1420 LARGE001
split, T-1459 design step 6): import table, callable-reference resolution,
alias-table construction, and resolved-candidate collection for the kotlin
`_DangerousOperation` needle family, split verbatim out of
`frob.vet._capability` (T-0664 lineage). Every name here is re-exported
(or imported back) by `_capability` so the module's public surface is
unchanged."""

# frob:ticket T-1420
from __future__ import annotations

from pathlib import Path

from frob.lang import node_text, raw_tree

from ._capability_core import ByteSpan, _fully_in_any_span, _needle_matches_resolved
from ._capability_registry import DANGEROUS_OPERATIONS, _DangerousOperation

# --------------------------------------------------------------- kotlin (T-0664)
#
# Kotlin static-binding resolution (docs/design/capability-evasion-
# taxonomy.md's Kotlin table, T-0664 -- the fourth per-language resolver
# after T-0328/T-0377/T-0378/T-0379/T-0662/T-0663's python/TS/rust/C/C++
# ones). `frob.lang.raw_tree`'s `"kotlin"` label reaches `frob.lang._walk_
# kotlin`'s grammar via T-0723's central-dispatch wiring.
#
# SCOPE, disclosed up front rather than silently narrowed: this resolver
# uses a FLAT, FILE-WIDE alias table (no per-scope/position shadow
# discipline the way `_c_shadowing_scope`/`_rust_shadowing_scope` give the
# C/rust resolvers) -- a local variable that happens to share a name with
# an imported/aliased binding is NOT distinguished from the import here.
# This is a REDUCED-FIDELITY model versus the other four resolvers (a
# genuine over-approximation risk, not a silent gap: a shadowing local
# could theoretically cause a spurious "detected" on a name that is
# locally rebound to something harmless), accepted for this pass given
# kotlin's own grammar has no separate compilation-unit-vs-function-body
# scope split as clean as C's `_C_SCOPE_TYPES`/rust's `_RUST_SCOPE_TYPES`
# to hang position-aware bookkeeping off of without materially more
# machinery than this ticket's own time budget allows. A future pass
# tightening this to per-function scoping (mirroring `_c_scope_bound_
# names`'s shape against kotlin's `function_declaration`/`class_body`
# nodes) is a natural follow-up, not attempted here.
_KT_WILDCARD_DANGEROUS_MODULES = frozenset({"java.lang"})


def _kt_cap_child_of_type(node, type_name: str):  # noqa: ANN001, ANN201
    """The first DIRECT child of `node` with tree-sitter type `type_name`
    -- kotlin's grammar exposes almost no named fields (T-0614/T-0723's own
    finding for this same grammar), so every lookup here is positional.
    Kept as its own copy rather than importing `frob.lang._walk_kotlin`'s
    private `_kt_child_of_type` -- `frob.vet` and `frob.lang` are
    deliberately independent walk layers over the same grammar, matching
    how `_c_declared_name`/`frob.arch._kotlin`'s own node-walk code is each
    kept local to its own module."""
    for c in node.children:
        if c.type == type_name:
            return c
    return None


def _kt_import_table(root) -> tuple[dict[str, str], frozenset[str]]:  # noqa: ANN001
    """(name -> fully-dotted-path import table, wildcard-import module
    prefixes) built from every `import_header` (T-0664, taxonomy "import"/
    "import ... as"/"wildcard import" rows): a plain `import a.b.C` binds
    its LAST dotted segment (`"C"`) to the full path (so an unqualified
    `C(...)` call site also resolves, matching real kotlin/java import
    semantics -- redundant with the raw lexical scan when `C` is already
    the needle's own literal text, harmless, matching T-0379's "declared +
    direct call needs no special resolution" precedent for the identical
    case); `import a.b.C as D` binds `D` instead; `import a.b.*` records
    `a.b` as a wildcard prefix ONLY when it is in the tiny, curated `_KT_
    WILDCARD_DANGEROUS_MODULES` set (mirrors `_RUST_WILDCARD_DANGEROUS_
    MODULES`'s same fail-closed-by-curation posture -- a wildcard import of
    an untracked package resolves nothing)."""
    table: dict[str, str] = {}
    wildcard: set[str] = set()

    def visit(node) -> None:  # noqa: ANN001
        if node.type == "import_header":
            ident = _kt_cap_child_of_type(node, "identifier")
            alias_node = _kt_cap_child_of_type(node, "import_alias")
            is_wildcard = _kt_cap_child_of_type(node, "wildcard_import") is not None
            if ident is not None:
                dotted = node_text(ident)
                if is_wildcard:
                    if dotted in _KT_WILDCARD_DANGEROUS_MODULES:
                        wildcard.add(dotted)
                elif alias_node is not None:
                    alias_id = _kt_cap_child_of_type(alias_node, "type_identifier")
                    if alias_id is not None:
                        table[node_text(alias_id)] = dotted
                else:
                    table.setdefault(dotted.rsplit(".", 1)[-1], dotted)
        for child in node.children:
            visit(child)

    visit(root)
    return table, frozenset(wildcard)


# frob:ticket T-0664
def _kt_resolve_callable_reference(node, import_table: dict[str, str]) -> str | None:  # noqa: ANN001
    """Resolve a `callable_reference` node (T-0664, taxonomy "::
    callable/function reference" row) -- a bare `::runCmd` resolves its one
    named child through `import_table` (falling back to the bare name
    itself, a plain top-level function reference); a receiver-typed
    `Runtime::exec` resolves its receiver through `import_table` (falling
    back to the receiver's own literal text) and appends `.exec`."""
    named = [c for c in node.children if c.type != "::"]
    if len(named) == 1:
        member = named[0]
        if member.type != "simple_identifier":
            return None
        name = node_text(member)
        return import_table.get(name, name)
    if len(named) == 2:
        receiver, member = named
        if member.type != "simple_identifier":
            return None
        receiver_text = node_text(receiver)
        resolved_receiver = import_table.get(receiver_text, receiver_text)
        return f"{resolved_receiver}.{node_text(member)}"
    return None


def _kt_property_name_and_value(node):  # noqa: ANN001, ANN201
    """(name node, value node) for a `property_declaration` (`val`/`var`),
    or `(None, None)` if either is absent -- kotlin's grammar has no
    labeled `name`/`value` fields on this node (T-0664), so both are
    plucked positionally: the name is `variable_declaration`'s own
    `simple_identifier`; the value is whatever child directly follows the
    `=` token."""
    var_decl = _kt_cap_child_of_type(node, "variable_declaration")
    name_node = (
        _kt_cap_child_of_type(var_decl, "simple_identifier")
        if var_decl is not None
        else None
    )
    if name_node is None:
        return None, None
    seen_eq = False
    value = None
    for c in node.children:
        if c.type == "=":
            seen_eq = True
            continue
        if seen_eq:
            value = c
            break
    return name_node, value


# frob:ticket T-0664
# frob:waive ARCH001 reason="one recursive dispatch over kotlin's three resolvable expression shapes (simple_identifier/navigation_expression/call_expression); each branch is a single named case, splitting further would multiply indirection without shrinking real complexity" ceiling="65"  # noqa: E501
# frob:tests tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates.test_resolve_expr_text_returns_none_for_unbound_identifier  # noqa: E501
# frob:invariant terminates reason="the navigation_expression branch recurses only \
# into node.children[0] (its own base), and the call_expression branch recurses only \
# into _kt_call_callee(node)'s result -- both a proper descendant of node one or more \
# tree-sitter edges below it, in the finite parse tree; a lexical prover cannot see \
# either descent is structurally smaller without dataflow" measure="tree-sitter AST \
# depth under node, finite per parse"
def _kt_resolve_expr_text(
    node,  # noqa: ANN001
    import_table: dict[str, str],
    var_alias_table: dict[str, str],
    wildcard_prefixes: frozenset[str] = frozenset(),
) -> str | None:
    """Resolve one kotlin expression node to a fully-dotted target text
    (T-0664) -- a `simple_identifier` through `var_alias_table` then
    `import_table` then (last resort) the curated wildcard-import fallback;
    a `navigation_expression` (`Rt.getRuntime`) by resolving its base
    (recursively -- the base MAY itself be a nested `call_expression`, see
    below) and appending `.member`; a `call_expression` (`Rt.getRuntime()`,
    itself acting as the BASE of an outer `.exec` navigation) by resolving
    its own callee and appending a literal `"()"` marker -- this last step
    is why `docs/design/capability-evasion-taxonomy.md`'s own kotlin exec
    needle (`"Runtime.getRuntime().exec("`) can match a resolved chain
    text at all: the registry needle itself embeds the intermediate call's
    parens, so dropping them here would make that specific needle
    structurally unmatchable no matter how correct the rest of the
    resolution is. Returns `None` when nothing resolves (never falls back
    to a bare, un-aliased name -- the pre-existing lexical scan already
    covers that case, matching every other language resolver's identical
    contract)."""
    if node.type == "simple_identifier":
        name = node_text(node)
        if name in var_alias_table:
            return var_alias_table[name]
        direct = import_table.get(name)
        if direct is not None:
            return direct
        if wildcard_prefixes:
            module = sorted(wildcard_prefixes)[0]
            return f"{module}.{name}"
        return None
    if node.type == "navigation_expression":
        base = node.children[0] if node.children else None
        if base is None:
            return None
        if base.type in ("simple_identifier", "type_identifier"):
            base_name = node_text(base)
            base_resolved = import_table.get(base_name) or var_alias_table.get(
                base_name
            )
        else:
            base_resolved = _kt_resolve_expr_text(
                base, import_table, var_alias_table, wildcard_prefixes
            )
        if base_resolved is None:
            return None
        suffix = _kt_cap_child_of_type(node, "navigation_suffix")
        if suffix is None:
            return base_resolved
        member = None
        for c in suffix.children:
            if c.type in ("simple_identifier", "type_identifier"):
                member = c
        if member is None:
            return base_resolved
        return f"{base_resolved}.{node_text(member)}"
    if node.type == "call_expression":
        callee = _kt_call_callee(node)
        if callee is None:
            return None
        inner = _kt_resolve_expr_text(
            callee, import_table, var_alias_table, wildcard_prefixes
        )
        return f"{inner}()" if inner is not None else None
    return None


def _kt_call_callee(node):  # noqa: ANN001, ANN201
    """The callee expression of a `call_expression` (T-0664) -- kotlin's
    grammar has no labeled `function` field (unlike TS/rust); the callee
    is simply the LAST non-`call_suffix` direct child (a bare `f(x)` has
    exactly one such child, `f`; a chained `Rt.getRuntime().exec(x)`'s
    OUTER call's callee is the `navigation_expression` covering `Rt.
    getRuntime().exec`)."""
    callee = None
    for c in node.children:
        if c.type != "call_suffix":
            callee = c
    return callee


def _kt_destructure_value_elements(value):  # noqa: ANN001, ANN201
    """The positional argument-expression list of a destructuring
    declaration's RHS `call_expression` (T-1063, taxonomy "destructuring
    declaration" row: `val (a, b) = Pair(::runCmd, 0)`) -- each `value_
    argument`'s one child, unwrapped, in source order. Empty for any other
    RHS shape (no positional elements to walk, fail-closed same as the
    rust/C++ destructure-alias tables)."""
    if value.type != "call_expression":
        return []
    suffix = _kt_cap_child_of_type(value, "call_suffix")
    if suffix is None:
        return []
    args = _kt_cap_child_of_type(suffix, "value_arguments")
    if args is None:
        return []
    elements = []
    for arg in args.children:
        if arg.type != "value_argument":
            continue
        named = [c for c in arg.children if c.is_named]
        if named:
            elements.append(named[0])
    return elements


def _record_kt_destructure_alias(
    multi_decl,  # noqa: ANN001 -- tree_sitter.Node (multi_variable_declaration)
    value,  # noqa: ANN001 -- tree_sitter.Node
    import_table: dict[str, str],
    var_alias_table: dict[str, str],
) -> None:
    """Bind each `variable_declaration` element of `multi_decl` to its
    POSITIONALLY corresponding element of `value`'s call-argument list
    (T-1063, taxonomy "destructuring declaration" row) -- mirrors rust's
    `_record_rust_destructure_alias`/C++'s `_record_c_structured_binding_
    alias`. A non-identifier binding target (kotlin destructuring targets
    are always a single `simple_identifier` per slot, unlike rust/C++'s
    richer nested patterns) or an unresolvable positional element is
    simply skipped."""
    left_elements = [
        _kt_cap_child_of_type(c, "simple_identifier")
        for c in multi_decl.children
        if c.type == "variable_declaration"
    ]
    right_elements = _kt_destructure_value_elements(value)
    for left_el, right_el in zip(left_elements, right_elements, strict=False):
        if left_el is None:
            continue
        resolved = None
        if right_el.type == "callable_reference":
            resolved = _kt_resolve_callable_reference(right_el, import_table)
        elif right_el.type == "simple_identifier":
            resolved = _kt_resolve_expr_text(right_el, import_table, var_alias_table)
        if resolved is not None:
            var_alias_table.setdefault(node_text(left_el), resolved)


def _record_kt_param_default_aliases(
    node,  # noqa: ANN001 -- tree_sitter.Node (function_value_parameters)
    import_table: dict[str, str],
    var_alias_table: dict[str, str],
) -> None:
    """Bind every `parameter` child of `node` (a `function_value_
    parameters` list) that is IMMEDIATELY followed by a `= default_value`
    pair to `var_alias_table` (T-1063, taxonomy "default parameter
    forwarding a callable" row: `fun call(cb: (String) -> Unit = ::runCmd)
    { cb(x) }`) -- mirrors C++'s `_record_c_default_param_alias`. Kotlin's
    grammar hangs a parameter's default value as a SIBLING of the
    `parameter` node (the `=` and its value sit directly inside `function_
    value_parameters`, not inside `parameter` itself, unlike C++'s
    `optional_parameter_declaration`), so this walks siblings positionally
    rather than a single node's own children. Kotlin's var-alias table is
    already file-wide, no per-function scope split (T-0664's documented
    posture), so this needs no scope-node lookup unlike the C++ sibling."""
    children = node.children
    for i, child in enumerate(children):
        if child.type != "parameter":
            continue
        name_node = _kt_cap_child_of_type(child, "simple_identifier")
        if name_node is None:
            continue
        if i + 2 >= len(children) or children[i + 1].type != "=":
            continue
        default_value = children[i + 2]
        resolved = None
        if default_value.type == "callable_reference":
            resolved = _kt_resolve_callable_reference(default_value, import_table)
        elif default_value.type == "simple_identifier":
            resolved = _kt_resolve_expr_text(
                default_value, import_table, var_alias_table
            )
        if resolved is not None:
            var_alias_table.setdefault(node_text(name_node), resolved)


def _kt_build_var_alias_table(root, import_table: dict[str, str]) -> dict[str, str]:  # noqa: ANN001
    """File-wide `name -> resolved_target` table (T-0664, taxonomy "val/var
    assignment"/"typealias for a function type"/":: callable reference"
    rows) built from every `property_declaration` whose value is a
    `callable_reference` or a chained `simple_identifier` -- visited in
    source (document) order, so `val f = ::runCmd; val g = f;` resolves
    `g` transitively the same way the C/rust/TS/python alias tables do. A
    `typealias` on the DECLARED TYPE (`val f: Handler = ::runCmd`) needs no
    separate handling: the type annotation is a different child entirely,
    never touched here -- the value is still a plain `callable_reference`,
    matching T-0663's identical "typedef/using-alias only renames the
    TYPE, not the binding grammar" finding for C++."""
    var_alias_table: dict[str, str] = {}

    def visit(node) -> None:  # noqa: ANN001
        if node.type == "property_declaration":
            multi_decl = _kt_cap_child_of_type(node, "multi_variable_declaration")
            if multi_decl is not None:
                value = None
                seen_eq = False
                for c in node.children:
                    if c.type == "=":
                        seen_eq = True
                        continue
                    if seen_eq:
                        value = c
                        break
                if value is not None:
                    _record_kt_destructure_alias(
                        multi_decl, value, import_table, var_alias_table
                    )
            else:
                name_node, value = _kt_property_name_and_value(node)
                if name_node is not None and value is not None:
                    resolved = None
                    if value.type == "callable_reference":
                        resolved = _kt_resolve_callable_reference(value, import_table)
                    elif value.type == "simple_identifier":
                        resolved = _kt_resolve_expr_text(
                            value, import_table, var_alias_table
                        )
                    if resolved is not None:
                        var_alias_table.setdefault(node_text(name_node), resolved)
        elif node.type == "function_value_parameters":
            _record_kt_param_default_aliases(node, import_table, var_alias_table)
        for child in node.children:
            visit(child)

    visit(root)
    return var_alias_table


def _kt_collect_candidates(
    node,  # noqa: ANN001
    import_table: dict[str, str],
    var_alias_table: dict[str, str],
    wildcard_prefixes: frozenset[str],
    candidates: list[tuple[str, int, int]],
) -> None:
    """Recursively walk `node`, appending `(resolved, start_byte, end_byte)`
    to `candidates` for every `call_expression` whose callee resolves
    through `_kt_resolve_expr_text` (T-0664) -- mirrors `_collect_c_
    candidates`/`_collect_rust_candidates`'s job."""
    if node.type == "call_expression":
        callee = _kt_call_callee(node)
        if callee is not None and callee.type in (
            "simple_identifier",
            "navigation_expression",
        ):
            resolved = _kt_resolve_expr_text(
                callee, import_table, var_alias_table, wildcard_prefixes
            )
            if resolved is not None:
                candidates.append((resolved, node.start_byte, node.end_byte))
    for child in node.children:
        _kt_collect_candidates(
            child, import_table, var_alias_table, wildcard_prefixes, candidates
        )


def _kt_resolved_candidates(path: Path) -> tuple[tuple[str, int, int], ...]:
    """Every `(resolved_name, start_byte, end_byte)` this kotlin file's call
    sites resolve to through its import table (plain/`as`-aliased/curated-
    wildcard) and file-wide `val`/`var`/`::`-reference alias table (T-0664).
    Empty for a non-kotlin file, an unparseable file, or one `frob.lang`
    has no grammar for -- degrades to the pre-existing lexical-only scan,
    never raises."""
    parsed = raw_tree(path)
    if parsed.is_err:
        return ()
    tree, _source, language_label = parsed.danger_ok
    if language_label != "kotlin":
        return ()

    import_table, wildcard_prefixes = _kt_import_table(tree.root_node)
    var_alias_table = _kt_build_var_alias_table(tree.root_node, import_table)
    candidates: list[tuple[str, int, int]] = []
    _kt_collect_candidates(
        tree.root_node, import_table, var_alias_table, wildcard_prefixes, candidates
    )
    return tuple(candidates)


# frob:ticket T-0664
def _kt_binding_capabilities(
    path: Path,
    table: dict[str, tuple[str, ...]],
    comment_spans: tuple[ByteSpan, ...],
) -> set[str]:
    """Capability kinds observed via kotlin import/alias-aware resolution
    only (T-0664) -- the union of every registry needle that matches a
    resolved call target, for sites outside a comment span. Merged into
    `scan_file_capabilities`'s lexical result. Mirrors `_c_binding_
    capabilities`."""
    found: set[str] = set()
    for resolved, start, end in _kt_resolved_candidates(path):
        if _fully_in_any_span(start, end, comment_spans):
            continue
        for capability, needles in table.items():
            if capability in found:
                continue
            if any(_needle_matches_resolved(needle, resolved) for needle in needles):
                found.add(capability)
    return found


# frob:ticket T-0664
def _kt_binding_operations(
    path: Path, comment_spans: tuple[ByteSpan, ...]
) -> tuple[_DangerousOperation, ...]:
    """`DANGEROUS_OPERATIONS` kotlin entries observed via import/alias-aware
    resolution only (T-0664) -- `_scan_file_operations`'s resolver-backed
    sibling to `_kt_binding_capabilities`. Mirrors `_c_binding_operations`."""
    candidates = _kt_resolved_candidates(path)
    if not candidates:
        return ()
    matched: list[_DangerousOperation] = []
    for entry in DANGEROUS_OPERATIONS:
        if entry.language != "kotlin" or not entry.needles:
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


# frob:ticket T-0664
def _extra_kt_binding_operations(
    path: Path,
    comment_spans: tuple[ByteSpan, ...],
    already_matched: list[_DangerousOperation],
) -> list[_DangerousOperation]:
    """`_kt_binding_operations` entries not already present in
    `already_matched` (T-0664) -- kotlin sibling of `_extra_c_binding_
    operations`, same set-based dedupe."""
    seen = set(already_matched)
    extra: list[_DangerousOperation] = []
    for entry in _kt_binding_operations(path, comment_spans):
        if entry not in seen:
            extra.append(entry)
            seen.add(entry)
    return extra
