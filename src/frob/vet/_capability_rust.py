"""Rust import/binding-aware capability resolution (T-1420 LARGE001 split,
T-1459 design step 4): `use`-declaration binding, scope-binding, alias-table
construction, and resolved-candidate collection for the rust
`_DangerousOperation` needle family, split verbatim out of
`frob.vet._capability` (T-0378 lineage). Every name here is re-exported (or
imported back) by `_capability` so the module's public surface is
unchanged."""

# frob:ticket T-1420
from __future__ import annotations

from pathlib import Path

from frob.lang import node_text, raw_tree

from ._capability_core import ByteSpan, _fully_in_any_span, _needle_matches_resolved
from ._capability_registry import DANGEROUS_OPERATIONS, _DangerousOperation

# T-0378: import/binding-aware resolution for Rust, mirroring the T-0328
# python / T-0377 TS discipline above but scoped to what a Rust `use`
# statement actually needs: `use std::process::Command as C;` binds a local
# alias to a fully-qualified path, and a subsequent `C::new(...)` call must
# resolve to `std::process::Command::new` the same way `Command::new(...)`
# would -- the raw-text lexical scan looks for a literal `Command::new(`/
# `std::` substring, so a renamed `use` import evades it entirely.
#
# Bind table (`_rust_use_table`) forms:
#   use std::process::Command;        -> {"Command": "std::process::Command"}
#   use std::process::Command as C;   -> {"C": "std::process::Command"}
#   use foo;                          -> {"foo": "foo"}
# T-0661 closes the T-0378 grouped/nested-`use`/glob-`use` gap: `use a::{b,
# c as d};` -> `{"b": "a::b", "d": "a::c"}` (`_bind_rust_use_list`, recursed
# for a further-nested group like `a::{b::{c, d as e}}`); `use std::process
# ::*;` -> a best-effort glob wildcard fallback for a `_RUST_WILDCARD_
# DANGEROUS_MODULES`-curated path only (`_bind_rust_use_wildcard`, mirrors
# the python resolver's `from X import *` fallback). `use std::fs::{self,
# File};` -- the `self` re-export-of-the-parent-module keyword inside a
# group -- is not specially recognized (falls through as an ordinary
# `identifier` child bound to `"<prefix>::self"`, a harmless dead binding
# rather than a crash); a real fix is a narrow follow-up, not attempted
# here since it is not itself a capability-routing evasion.
#
# `pub use` re-export (taxonomy row): needs NO special-case at all -- a
# `pub` visibility modifier is simply one more `use_declaration` child this
# walk never dispatches on, so the path/alias/group/glob children are found
# exactly the same regardless of whether `pub` precedes them.
#
# Scope-awareness (mandatory, mirrors T-0328/T-0377): a function/closure
# PARAMETER or a local `let` binding of the same name as a `use`-bound alias
# SHADOWS it in every enclosing scope from the site up to the file
# (`source_file`) root -- `fn f() { let C = 5; C::new(...) }` (a local
# variable that happens to share the alias's name, then gets called like a
# path -- contrived but the same no-false-positive discipline as the
# python/TS resolvers) must not resolve `C` to the `use`-bound path.
#
# T-0378 ROUND 2 (reviewer REJECT -- soundness hole, T-0339 fail-closed):
# round 1's shadow check was ORDER-INSENSITIVE -- it collected every name
# bound ANYWHERE in the enclosing scope into a plain set, so a capability
# call textually BEFORE a same-named `let` rebinding was wrongly treated as
# already shadowed and silently dropped:
#
#   use std::process::Command as C;
#   fn f() {
#       C::new("sh");   // executes BEFORE `let C` -- MUST resolve to exec
#       let C = 5;
#   }
#
# A `let` binding does not hoist in Rust -- a use of the name before its
# `let` refers to whatever it resolved to beforehand (here, the `use`-bound
# alias), not the not-yet-effective local. Fixed: `_rust_scope_bound_names`
# now maps `name -> byte position from which it shadows`, not just `name`;
# `_rust_shadowing_scope` only treats a binding as shadowing a given call
# site when `site.start_byte >= that position` (`_RUST_ALWAYS_SHADOWS`, -1,
# for parameters and nested-fn-item names, which ARE in scope for the whole
# body/block by construction -- only `let` targets get a real position, the
# `let_declaration` node's own `start_byte`). A name rebound multiple times
# keeps its EARLIEST recorded position (`_record_rust_binding`): once truly
# shadowed, a call site stays shadowed, it never un-shadows.
_RUST_SCOPE_TYPES = ("function_item", "closure_expression", "source_file")


def _rust_path_text(node) -> str | None:  # noqa: ANN001
    """Flatten a `scoped_identifier` (`a::b::c`) or bare `identifier` node
    into its `::`-joined text, or `None` for any other node shape -- the
    Rust analog of walking a python `attribute` chain / TS `member_
    expression` into a dotted string."""
    if node.type == "identifier":
        return node_text(node)
    if node.type != "scoped_identifier":
        return None
    parts: list[str] = []

    def collect(n) -> None:  # noqa: ANN001
        if n.type == "identifier":
            parts.append(node_text(n))
        elif n.type == "scoped_identifier":
            for child in n.children:
                collect(child)

    collect(node)
    return "::".join(parts) if parts else None


def _bind_rust_use_as_clause(node, table: dict[str, str]) -> None:  # noqa: ANN001
    """One `use_as_clause` node's contribution to `_rust_use_table`: `use
    PATH as ALIAS;` -> `{ALIAS: PATH}` (grammar shape: `[path_node, "as",
    alias_identifier]`, path first and alias last by construction)."""
    children = node.children
    if len(children) < 3:
        return
    alias_node = children[-1]
    if alias_node.type != "identifier":
        return
    full = _rust_path_text(children[0])
    if full:
        table[node_text(alias_node)] = full


def _rust_use_list_prefix(node) -> str | None:  # noqa: ANN001
    """The `::`-joined path text a `scoped_use_list` node carries BEFORE its
    trailing `use_list` child (T-0661: `std::process::{Command, Stdio}` ->
    `"std::process"`, `d::{e, f as g}` (nested) -> `"d"`) -- `None` if the
    node carries no leading path segment at all (defensive; the grammar
    always emits at least one for a real `scoped_use_list`)."""
    parts: list[str] = []
    for child in node.children:
        if child.type == "use_list":
            break
        if child.type == "identifier":
            parts.append(node_text(child))
        elif child.type == "scoped_identifier":
            full = _rust_path_text(child)
            if full:
                parts.append(full)
    return "::".join(parts) if parts else None


def _rust_join_prefix(prefix: str | None, segment: str) -> str:
    """Join a (possibly absent) enclosing group prefix with one more path
    segment (T-0661), used by `_bind_rust_use_list`'s recursion into a
    nested `scoped_use_list`."""
    return f"{prefix}::{segment}" if prefix else segment


# frob:invariant terminates reason="recurses only into a scoped_use_list's own inner \
# use_list, one tree-sitter edge below the current node; a lexical prover cannot see \
# that the nested list is structurally smaller without dataflow" measure="tree-sitter \
# AST depth under list_node, finite per parse"
def _bind_rust_use_list(
    list_node,  # noqa: ANN001 -- tree_sitter.Node (use_list)
    prefix: str | None,
    table: dict[str, str],
) -> None:
    """One `use_list` node's contribution to `_rust_use_table` (T-0661,
    taxonomy "use path::{a, b}" grouped/nested row): each bare `identifier`
    child binds `{name: prefix::name}`; each `use_as_clause` child binds
    `{alias: prefix::name}` (`use std::process::{Command as C, Stdio};` ->
    `{"C": "std::process::Command", "Stdio": "std::process::Stdio"}` -- the
    exact evasion the pre-existing lexical scan AND the pre-T-0661 flat-only
    `_bind_rust_use_declaration` both missed: `C::new(...)` contains neither
    the literal `Command::new(` needle text nor a bound `use_table` entry);
    a nested `scoped_use_list` child (`d::{e, f as g}`) recurses with its
    own prefix segment appended."""
    for child in list_node.children:
        if child.type == "identifier":
            name = node_text(child)
            table.setdefault(name, _rust_join_prefix(prefix, name))
        elif child.type == "use_as_clause":
            children = child.children
            if len(children) < 3:
                continue
            source_node, alias_node = children[0], children[-1]
            if source_node.type != "identifier" or alias_node.type != "identifier":
                continue
            table.setdefault(
                node_text(alias_node),
                _rust_join_prefix(prefix, node_text(source_node)),
            )
        elif child.type == "scoped_use_list":
            sub_prefix = _rust_use_list_prefix(child)
            full_prefix = (
                _rust_join_prefix(prefix, sub_prefix) if sub_prefix else prefix
            )
            inner_list = next((c for c in child.children if c.type == "use_list"), None)
            if inner_list is not None:
                _bind_rust_use_list(inner_list, full_prefix, table)


#: sentinel `use_table` KEY (not a legal Rust identifier -- starts with a
#: NUL byte -- so it can never collide with a real bound alias) recording
#: the set of glob-imported (`use path::*;`) module prefixes for a file,
#: NUL-joined (T-0661, mirrors the python resolver's `_PY_WILDCARD_TABLE_
#: KEY`/`_PY_WILDCARD_DANGEROUS_MODULES` best-effort fallback).
_RUST_WILDCARD_TABLE_KEY = "\x00wildcard"

#: every Rust `library` path `DANGEROUS_OPERATIONS` curates an entry for
#: (T-0661) -- used ONLY to decide whether a `use path::*;` glob import is
#: worth a best-effort fallback resolution; a module absent from this set
#: gets no wildcard binding at all (an honest, documented under-
#: approximation, matching the python resolver's `_PY_WILDCARD_DANGEROUS_
#: MODULES` posture for the taxonomy's "degrades to opaque" caveat).
_RUST_WILDCARD_DANGEROUS_MODULES: frozenset[str] = frozenset(
    entry.library for entry in DANGEROUS_OPERATIONS if entry.language == "rust"
)


def _bind_rust_use_wildcard(node, table: dict[str, str]) -> None:  # noqa: ANN001
    """One `use_wildcard` node's contribution to `_rust_use_table` (T-0661,
    taxonomy "use path::*" glob row): `use std::process::*;` records
    `"std::process"` into the `_RUST_WILDCARD_TABLE_KEY` sentinel set, ONLY
    when it is a `_RUST_WILDCARD_DANGEROUS_MODULES`-curated path -- an
    honest, narrow best-effort fallback (`_resolve_rust_identifier`'s
    wildcard branch), not a general glob-import points-to resolution."""
    parts: list[str] = []
    for child in node.children:
        if child.type == "*":
            break
        if child.type == "identifier":
            parts.append(node_text(child))
        elif child.type == "scoped_identifier":
            full = _rust_path_text(child)
            if full:
                parts.append(full)
    module = "::".join(parts) if parts else None
    if module is None or module not in _RUST_WILDCARD_DANGEROUS_MODULES:
        return
    existing = table.get(_RUST_WILDCARD_TABLE_KEY, "")
    modules = set(existing.split("\x00")) if existing else set()
    modules.add(module)
    table[_RUST_WILDCARD_TABLE_KEY] = "\x00".join(sorted(modules))


def _bind_rust_use_declaration(node, table: dict[str, str]) -> None:  # noqa: ANN001
    """One `use_declaration` node's contribution to `_rust_use_table`: an
    `as`-aliased path (`_bind_rust_use_as_clause`), a bare path (`use
    std::process::Command;` -> `{"Command": "std::process::Command"}`,
    keyed by the path's last segment), a grouped/nested `use` list (T-0661,
    `_bind_rust_use_list` via its enclosing `scoped_use_list`'s own path
    prefix), or a glob (T-0661, `_bind_rust_use_wildcard`). A leading `pub`
    visibility modifier (`pub use ...;`, taxonomy "pub use re-export" row)
    is simply an extra child this walk never dispatches on, so it needs no
    special case -- the path/alias/group/glob children are found and bound
    exactly the same regardless of whether `pub` precedes them."""
    for child in node.children:
        if child.type == "use_as_clause":
            _bind_rust_use_as_clause(child, table)
        elif child.type in ("identifier", "scoped_identifier"):
            full = _rust_path_text(child)
            if full:
                alias = full.rsplit("::", 1)[-1]
                table.setdefault(alias, full)
        elif child.type == "scoped_use_list":
            prefix = _rust_use_list_prefix(child)
            inner_list = next((c for c in child.children if c.type == "use_list"), None)
            if inner_list is not None:
                _bind_rust_use_list(inner_list, prefix, table)
        elif child.type == "use_wildcard":
            _bind_rust_use_wildcard(child, table)


def _rust_use_table(root_node) -> dict[str, str]:  # noqa: ANN001
    """The file-wide local-alias -> resolved-path binding table (T-0378,
    extended T-0661 for grouped/nested `use` lists and glob imports), built
    from every `use_declaration` in the tree (not just top-level -- mirrors
    `_py_import_table`'s function-scoped-import over-approximation: a
    module/fn-local `use` still contributes a file-wide binding)."""
    table: dict[str, str] = {}

    def visit(node) -> None:  # noqa: ANN001
        if node.type == "use_declaration":
            _bind_rust_use_declaration(node, table)
        for child in node.children:
            visit(child)

    visit(root_node)
    return table


#: sentinel `bound` position meaning "shadows from the very start of the
#: scope, regardless of call-site position" -- used for function/closure
#: PARAMETERS (always in scope for the whole body) and nested `fn` item
#: names (Rust hoists a block-local `fn`, so it can be called before its
#: textual definition within the same block). Only `let` bindings get a
#: REAL position (T-0378 round 2, see `_RUST_SCOPE_TYPES` block comment).
_RUST_ALWAYS_SHADOWS = -1


def _record_rust_binding(bound: dict[str, int], name: str, position: int) -> None:
    """Record that `name` starts shadowing an enclosing `use` alias at byte
    `position` within its scope, keeping the EARLIEST position on repeat
    bindings of the same name (a `let x` rebound twice still shadows from
    its first occurrence onward, never un-shadows) -- the position-aware
    T-0378 round 2 fix's core bookkeeping primitive."""
    existing = bound.get(name)
    bound[name] = position if existing is None else min(existing, position)


def _collect_rust_param_name(node, bound: dict[str, int]) -> None:  # noqa: ANN001
    """Add one `parameters`/`closure_parameters`-node child's bound name to
    `bound` at `_RUST_ALWAYS_SHADOWS` (a plain `identifier` for a closure
    param with no type annotation, or the leading `identifier` child of a
    `parameter`/`self_parameter` node -- the name always precedes the
    `:`/type in the Rust grammar, so the first `identifier` child found is
    the binding). A parameter is in scope for the WHOLE function body by
    construction, so it shadows regardless of call-site position -- no
    "used before declared" case exists for parameters the way it does for
    a mid-body `let`."""
    if node.type == "identifier":
        _record_rust_binding(bound, node_text(node), _RUST_ALWAYS_SHADOWS)
        return
    if node.type == "parameter":
        for child in node.children:
            if child.type == "identifier":
                _record_rust_binding(bound, node_text(child), _RUST_ALWAYS_SHADOWS)
                return


def _collect_rust_let_target(node, let_start: int, bound: dict[str, int]) -> None:  # noqa: ANN001
    """Add every name a `let_declaration` binds to `bound` AT `let_start`
    (the enclosing `let_declaration` node's own `start_byte`, T-0378 round
    2) -- stopping at the first `:` (type annotation) or `=` (initializer)
    child so only the PATTERN side is walked; recurses through simple
    nested patterns (e.g. a tuple pattern) collecting plain `identifier`
    leaves, mirroring `_collect_target_names`'s python job at Rust's
    coarser grain. Recording the BINDING's position (not `_RUST_ALWAYS_
    SHADOWS`) is what makes a call site textually BEFORE this `let` still
    resolve through the enclosing `use` alias instead of being wrongly
    treated as already shadowed."""
    for child in node.children:
        if child.type in (":", "="):
            break
        if child.type == "identifier":
            _record_rust_binding(bound, node_text(child), let_start)
        elif child.type not in ("let", "mutable_specifier"):
            _collect_rust_let_target(child, let_start, bound)


def _rust_scope_bind_step(node, is_top: bool, bound: dict[str, int]) -> bool:  # noqa: ANN001
    """Handle ONE node during `_rust_scope_bound_names`'s walk: add whatever
    name(s) `node` binds directly to `bound` (with `_RUST_ALWAYS_SHADOWS`
    for params/nested-fn-names, or the `let_declaration`'s own `start_byte`
    for a `let` target, T-0378 round 2), and report whether the walk should
    recurse into `node`'s children (False at a nested scope boundary --
    mirrors `_scope_bind_step`'s python job)."""
    node_type = node.type
    if not is_top and node_type in ("function_item", "closure_expression"):
        if node_type == "function_item":
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                _record_rust_binding(bound, node_text(name_node), _RUST_ALWAYS_SHADOWS)
        return False
    if node_type in ("parameters", "closure_parameters"):
        for child in node.children:
            _collect_rust_param_name(child, bound)
        return False
    if node_type == "let_declaration":
        _collect_rust_let_target(node, node.start_byte, bound)
    return True


def _rust_scope_bound_names(scope_node) -> dict[str, int]:  # noqa: ANN001
    """Every name bound DIRECTLY within `scope_node` (a `function_item`/
    `closure_expression`/`source_file` node), mapped to the byte position
    from which it starts shadowing an enclosing `use` alias -- parameters,
    `let` targets, and nested `fn`/closure names -- WITHOUT recursing into
    a nested scope's own body. T-0378 round 2: unlike the python/TS
    resolvers' plain name SET, this is POSITION-aware (`name -> start_
    byte`, `_RUST_ALWAYS_SHADOWS` for params/nested-fn-names) so a call
    site textually BEFORE a same-named `let` rebinding is correctly NOT
    treated as shadowed -- Rust `let` bindings do not hoist; a use before
    the `let` refers to whatever the name resolved to beforehand (here, the
    `use`-bound alias), same as the real Rust name-resolution rule this
    scanner approximates."""
    bound: dict[str, int] = {}

    def walk(node, is_top: bool) -> None:  # noqa: ANN001
        if _rust_scope_bind_step(node, is_top, bound):
            for child in node.children:
                walk(child, False)

    walk(scope_node, True)
    return bound


def _rust_shadowing_scope(name: str, site, scope_cache: dict[int, dict[str, int]]):  # noqa: ANN001, ANN201
    """The nearest LOCAL scope node enclosing `site` that binds `name`
    directly AT OR BEFORE `site`'s own `start_byte` (per `_rust_scope_
    bound_names`, cached per scope node in `scope_cache`), or `None` if no
    enclosing scope binds it before this position -- the T-0378 shadow
    check every resolution goes through before consulting the `use`
    binding table. T-0378 round 2: POSITION-aware (fail-closed, T-0339) --
    a `let` binding recorded at a LATER byte position than `site` does NOT
    shadow this particular call site (it hasn't taken effect yet), so
    resolution correctly falls through to the `use` table instead of
    silently dropping a capability call that textually precedes its
    same-named local rebinding. Mirrors `_shadowing_scope`'s scope-walk
    shape, not its (order-insensitive) membership test."""
    cur = site.parent
    while cur is not None:
        if cur.type in _RUST_SCOPE_TYPES:
            key = cur.id
            cached = scope_cache.get(key)
            if cached is None:
                cached = _rust_scope_bound_names(cur)
                scope_cache[key] = cached
            position = cached.get(name)
            if position is not None and site.start_byte >= position:
                return cur
            if cur.type == "source_file":
                break
        cur = cur.parent
    return None


def _resolve_rust_identifier(
    node,
    use_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    alias_table: dict[int, dict[str, str]] | None = None,
) -> str | None:  # noqa: ANN001
    """Resolve a bare `identifier` node to its `use`-bound target, or (T-
    0661) a scope-local `alias_table` entry when it IS locally shadowed AT
    THIS POSITION (T-0378 round 2) -- mirrors the python/TS resolvers'
    alias-copy-propagation fallback. When not shadowed at all and not
    directly `use`-bound, falls back to the glob-import wildcard sentinel
    (`_RUST_WILDCARD_TABLE_KEY`, T-0661) the same way the python resolver's
    `from X import *` fallback does -- `None` if none of these apply."""
    name = node_text(node)
    scope = _rust_shadowing_scope(name, node, scope_cache)
    if scope is not None:
        if alias_table is None:
            return None
        return alias_table.get(scope.id, {}).get(name)
    direct = use_table.get(name)
    if direct is not None:
        return direct
    wildcards = use_table.get(_RUST_WILDCARD_TABLE_KEY)
    if wildcards:
        module = sorted(wildcards.split("\x00"))[0]
        return f"{module}::{name}"
    return None


def _resolve_rust_scoped(
    node,
    use_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    alias_table: dict[int, dict[str, str]] | None = None,
) -> str | None:  # noqa: ANN001
    """Resolve a `scoped_identifier` chain (`Head::rest::of::path`) by
    resolving its leading segment through `_resolve_rust_identifier` and
    re-appending the remaining `::`-joined segments -- e.g. `C::new` with
    `C` bound to `std::process::Command` resolves to
    `std::process::Command::new`."""
    parts: list = []

    def collect(n) -> None:  # noqa: ANN001
        if n.type == "identifier":
            parts.append(n)
        elif n.type == "scoped_identifier":
            for child in n.children:
                collect(child)

    collect(node)
    if not parts:
        return None
    resolved_head = _resolve_rust_identifier(
        parts[0], use_table, scope_cache, alias_table
    )
    if resolved_head is None:
        return None
    rest = "::".join(node_text(p) for p in parts[1:])
    return f"{resolved_head}::{rest}" if rest else resolved_head


def _resolve_rust_expr(
    node,
    use_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    alias_table: dict[int, dict[str, str]] | None = None,
) -> str | None:  # noqa: ANN001
    """Resolve one Rust expression node (a bare `identifier` or a
    `scoped_identifier` chain) to its `use`-bound target, or `None` if it is
    locally shadowed with no alias entry, or not `use`-bound at all. Mirrors
    `_resolve_py_expr`/`_resolve_ts_expr`'s dispatch, extended (T-0661) with
    the `alias_table` copy-propagation parameter."""
    if node.type == "identifier":
        return _resolve_rust_identifier(node, use_table, scope_cache, alias_table)
    if node.type == "scoped_identifier":
        return _resolve_rust_scoped(node, use_table, scope_cache, alias_table)
    return None


def _enclosing_rust_scope(node):  # noqa: ANN001, ANN201
    """The nearest `_RUST_SCOPE_TYPES` ancestor of `node` (its own function/
    closure -> ... -> `source_file`), or `None` if `node` has no scope
    ancestor at all -- (T-0661) used by `_build_rust_alias_table` to find
    which scope a `let` binding's target name binds into; mirrors
    `_enclosing_py_scope`/`_enclosing_ts_scope`."""
    cur = node.parent
    while cur is not None:
        if cur.type in _RUST_SCOPE_TYPES:
            return cur
        cur = cur.parent
    return None


def _record_rust_destructure_alias(
    left_pattern,  # noqa: ANN001 -- tree_sitter.Node (tuple_pattern)
    right_tuple,  # noqa: ANN001 -- tree_sitter.Node (tuple_expression)
    use_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    alias_table: dict[int, dict[str, str]],
    scope_aliases: dict[str, str],
) -> None:
    """Bind each plain-identifier element of `left_pattern` (a `tuple_
    pattern` destructuring target) to its POSITIONALLY corresponding element
    of `right_tuple`'s named children (T-0661, taxonomy "tuple/struct
    destructuring bind" row: `let (f, _) = (Command::new, 0); f("sh");`) --
    a `_` wildcard-pattern element is simply skipped (not an identifier), a
    nested pattern is skipped the same way (documented, narrow limitation,
    same posture as the python/TS resolvers' nested-pattern gap)."""
    left_elements = [c for c in left_pattern.children if c.is_named]
    right_elements = [c for c in right_tuple.children if c.is_named]
    for left_el, right_el in zip(left_elements, right_elements, strict=False):
        if left_el.type != "identifier":
            continue
        resolved = _resolve_rust_expr(right_el, use_table, scope_cache, alias_table)
        if resolved is not None:
            scope_aliases.setdefault(node_text(left_el), resolved)


def _record_rust_alias(
    node,  # noqa: ANN001 -- tree_sitter.Node (let_declaration)
    use_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    alias_table: dict[int, dict[str, str]],
) -> None:
    """If `node` (a `let_declaration`) binds a plain identifier or a tuple-
    destructuring pattern to a resolvable `value`, record it in
    `alias_table` (first resolution wins, mirrors the python/TS resolvers'
    `_record_py_alias`/`_record_ts_alias`) -- covers a simple `let` binding
    (`let f = Command::new;`), a CHAINED/shadowed `let` (`let f = cmd_new;
    let f = f;` -- the second `let` re-resolves the first through this same
    table, since the tree walk visits `let_declaration`s in source order),
    and tuple-destructuring (`_record_rust_destructure_alias`). A closure
    capturing a bound path (`let f = Command::new; let c = move |a|
    f(a).spawn();`) needs no separate handling here: the closure body's call
    site resolves `f` through this SAME scope-keyed alias table via
    `_rust_shadowing_scope`'s enclosing-scope walk once the closure's own
    scope (which does not itself bind `f`) is climbed past."""
    pattern = node.child_by_field_name("pattern")
    value = node.child_by_field_name("value")
    if pattern is None or value is None:
        return
    scope = _enclosing_rust_scope(node)
    if scope is None:
        return
    scope_aliases = alias_table.setdefault(scope.id, {})
    if pattern.type == "tuple_pattern" and value.type == "tuple_expression":
        _record_rust_destructure_alias(
            pattern, value, use_table, scope_cache, alias_table, scope_aliases
        )
        return
    if pattern.type != "identifier":
        return
    resolved = _resolve_rust_expr(value, use_table, scope_cache, alias_table)
    if resolved is not None:
        scope_aliases.setdefault(node_text(pattern), resolved)


def _build_rust_alias_table(
    root_node,  # noqa: ANN001 -- tree_sitter.Node
    use_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
) -> dict[int, dict[str, str]]:
    """Scope-local copy-propagation table (T-0661, the Rust sibling of the
    python resolver's T-0337/T-0659 `_build_py_alias_table` and the TS/JS
    resolver's T-0660 `_build_ts_alias_table`): `id(scope_node) -> {name:
    resolved_dangerous_target}` for every `let_declaration` whose `value`
    resolves (via `_resolve_rust_expr`, which itself consults this same
    table as it is built) to a `use`-table entry or another local name
    already known to alias one. The tree walk visits `let_declaration`s in
    source (document) order, so an earlier alias is already recorded by the
    time a later statement copies it -- same document-order soundness
    argument as the python/TS tables."""
    alias_table: dict[int, dict[str, str]] = {}

    def visit(node) -> None:  # noqa: ANN001
        if node.type == "let_declaration":
            _record_rust_alias(node, use_table, scope_cache, alias_table)
        for child in node.children:
            visit(child)

    visit(root_node)
    return alias_table


def _record_rust_field_alias(
    node,  # noqa: ANN001 -- tree_sitter.Node (struct_expression)
    use_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    alias_table: dict[int, dict[str, str]],
    field_alias_table: dict[str, str],
) -> None:
    """Bind every `field: target` entry inside a `struct_expression`'s
    `field_initializer_list` to `field_alias_table` (T-1063, taxonomy
    "field rebinding via struct update" row: `let h = Handlers { run:
    C::new, ..default }; (h.run)("sh");`) -- keyed by FIELD NAME only, same
    best-effort object-identity-BY-NAME posture as C's `_record_c_field_
    alias` (two different struct variables with a same-named function-
    pointer field are not distinguished). The `..default`/`base_field_
    initializer` spread entry itself carries no resolvable target and is
    simply skipped -- it contributes no new binding, only a fallback for
    fields this literal does not mention."""
    field_list = node.child_by_field_name("body")
    if field_list is None:
        return
    for element in field_list.children:
        if element.type != "field_initializer":
            continue
        field_id = element.child_by_field_name("field")
        value = element.child_by_field_name("value")
        if field_id is None or field_id.type != "field_identifier":
            continue
        if value is None:
            continue
        resolved = _resolve_rust_expr(value, use_table, scope_cache, alias_table)
        if resolved is not None:
            field_alias_table.setdefault(node_text(field_id), resolved)


def _build_rust_field_alias_table(
    root_node,  # noqa: ANN001 -- tree_sitter.Node
    use_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    alias_table: dict[int, dict[str, str]],
) -> dict[str, str]:
    """File-wide `field_name -> resolved_dangerous_target` table (T-1063)
    built from every `struct_expression`'s field initializers -- the Rust
    sibling of C's `_record_c_field_alias`/`_c_field_alias_table`."""
    field_alias_table: dict[str, str] = {}

    def visit(node) -> None:  # noqa: ANN001
        if node.type == "struct_expression":
            _record_rust_field_alias(
                node, use_table, scope_cache, alias_table, field_alias_table
            )
        for child in node.children:
            visit(child)

    visit(root_node)
    return field_alias_table


def _collect_rust_candidates(
    node,
    use_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    candidates: list[tuple[str, int, int]],
    alias_table: dict[int, dict[str, str]] | None = None,
    field_alias_table: dict[str, str] | None = None,
) -> None:  # noqa: ANN001
    """Recursively walk `node`, appending `(resolved, start_byte, end_byte)`
    to `candidates` for every `call_expression` whose `function` resolves
    through `use_table` (T-0378), when locally shadowed through `alias_
    table`'s scope-local copy-propagation (T-0661), or (T-1063) a
    parenthesized field-expression call target (`(h.run)("sh")`) through
    `field_alias_table` -- mirrors `_collect_py_candidates`/`_collect_ts_
    candidates`'s job. Only the call site's function target is a
    resolvable "path" here (a bare `Command::new` field/method-style
    resolution beyond a plain scoped call, or a parenthesized field
    access, is not attempted, matching this pass's narrower acceptance
    criteria)."""
    if node.type == "call_expression":
        func = node.child_by_field_name("function")
        if func is not None and func.type in ("identifier", "scoped_identifier"):
            resolved = _resolve_rust_expr(func, use_table, scope_cache, alias_table)
            if resolved is not None:
                candidates.append((resolved, node.start_byte, node.end_byte))
        elif func is not None and func.type == "parenthesized_expression":
            inner = [c for c in func.children if c.is_named]
            if len(inner) == 1 and inner[0].type == "field_expression":
                field = inner[0].child_by_field_name("field")
                if field is not None and field.type == "field_identifier":
                    resolved = (field_alias_table or {}).get(node_text(field))
                    if resolved is not None:
                        candidates.append((resolved, node.start_byte, node.end_byte))
    for child in node.children:
        _collect_rust_candidates(
            child, use_table, scope_cache, candidates, alias_table, field_alias_table
        )


def _rust_resolved_candidates(path: Path) -> tuple[tuple[str, int, int], ...]:
    """Every `(resolved_path, start_byte, end_byte)` this Rust file's call
    sites resolve to through its `use` binding table (extended T-0661 for
    grouped/nested `use` lists and glob-import wildcard fallback), POSITION-
    aware enclosing-scope shadow check (T-0378, round 2 fixes an order-
    insensitivity soundness hole -- see `_rust_scope_bound_names`),
    (T-0661) scope-local `let`-alias copy-propagation table, and (T-1063) a
    file-wide struct-field alias table for a parenthesized field-expression
    call target (`(h.run)("sh")` after `let h = Handlers { run: C::new,
    ..default };`). Empty for a
    non-rust file, an unparseable file, or one `frob.lang` has no grammar
    for -- degrades to the pre-existing lexical-only scan, never raises."""
    parsed = raw_tree(path)
    if parsed.is_err:
        return ()
    tree, _source, language_label = parsed.danger_ok
    if language_label != "rust":
        return ()

    use_table = _rust_use_table(tree.root_node)
    scope_cache: dict[int, dict[str, int]] = {}
    alias_table = _build_rust_alias_table(tree.root_node, use_table, scope_cache)
    field_alias_table = _build_rust_field_alias_table(
        tree.root_node, use_table, scope_cache, alias_table
    )
    candidates: list[tuple[str, int, int]] = []
    _collect_rust_candidates(
        tree.root_node,
        use_table,
        scope_cache,
        candidates,
        alias_table,
        field_alias_table,
    )
    return tuple(candidates)


def _rust_binding_capabilities(
    path: Path,
    table: dict[str, tuple[str, ...]],
    comment_spans: tuple[ByteSpan, ...],
) -> set[str]:
    """Capability kinds observed via Rust `use`/binding-aware resolution
    only (T-0378) -- the union of every registry needle that matches a
    resolved call target, for sites outside a comment span. Merged into
    `scan_file_capabilities`'s lexical result; adds recall (aliased `use`
    evasions) without touching the existing raw-text path at all. Mirrors
    `_python_binding_capabilities`/`_ts_binding_capabilities`."""
    found: set[str] = set()
    for resolved, start, end in _rust_resolved_candidates(path):
        if _fully_in_any_span(start, end, comment_spans):
            continue
        for capability, needles in table.items():
            if capability in found:
                continue
            if any(_needle_matches_resolved(needle, resolved) for needle in needles):
                found.add(capability)
    return found


def _rust_binding_operations(
    path: Path, comment_spans: tuple[ByteSpan, ...]
) -> tuple[_DangerousOperation, ...]:
    """`DANGEROUS_OPERATIONS` rust entries observed via `use`/binding-aware
    resolution only (T-0378) -- `_scan_file_operations`'s resolver-backed
    sibling to `_rust_binding_capabilities`. Mirrors `_python_binding_
    operations`/`_ts_binding_operations`."""
    candidates = _rust_resolved_candidates(path)
    if not candidates:
        return ()
    matched: list[_DangerousOperation] = []
    for entry in DANGEROUS_OPERATIONS:
        if entry.language != "rust" or not entry.needles:
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


def _extra_rust_binding_operations(
    path: Path,
    comment_spans: tuple[ByteSpan, ...],
    already_matched: list[_DangerousOperation],
) -> list[_DangerousOperation]:
    """`_rust_binding_operations` entries not already present in
    `already_matched` (T-0378) -- Rust sibling of `_extra_binding_
    operations`/`_extra_ts_binding_operations`, same set-based dedupe."""
    seen = set(already_matched)
    extra: list[_DangerousOperation] = []
    for entry in _rust_binding_operations(path, comment_spans):
        if entry not in seen:
            extra.append(entry)
            seen.add(entry)
    return extra
