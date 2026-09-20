"""C# import/binding-aware capability resolution (T-4536): using-
directive table (plain/aliased/`static`), fully-qualified member-access
chains, `var`-local type binding from `new Ns.Type(...)`, and resolved-
candidate collection for the csharp `_DangerousOperation` needle family --
modeled on `_capability_kotlin.py`/`_capability_typescript.py`'s shape.
Every name here is re-exported (or imported back) by `_capability` so the
module's public surface is unchanged."""

# frob:ticket T-4536
from __future__ import annotations

from pathlib import Path

from frob.lang import node_text, raw_tree

from ._capability_core import ByteSpan, _fully_in_any_span, _needle_matches_resolved
from ._capability_registry import DANGEROUS_OPERATIONS, _DangerousOperation

# C# static-binding resolution via `frob.lang._walk_csharp`.
#
# SCOPE: this resolver uses a FLAT, FILE-WIDE alias table -- no per-
# method/per-block shadow discipline. A local variable sharing a name
# with an imported alias is NOT distinguished by scope -- a REDUCED-
# FIDELITY model, accepted as an over-approximation risk, never a gap.
#
# A plain `using X.Y;` brings every type in that namespace into
# unqualified scope, so a BARE `File.WriteAllText(...)` resolves only
# because `System.IO` was `using`'d. The namespace set is curated to
# exactly the ones the csharp registry declares dangerous APIs under --
# fail-closed: an unlisted namespace's bare-name usage resolves nothing.
_CS_WILDCARD_DANGEROUS_NAMESPACES = frozenset(
    {
        "System",
        "System.IO",
        "System.Diagnostics",
        "System.Net",
        "System.Net.Http",
        "System.Net.Sockets",
        "System.Runtime.InteropServices",
        "System.Runtime.Serialization",
    }
)


def _cs_derive_wildcard_type_namespaces() -> dict[str, str]:
    """`type-name -> curated namespace` (T-4536), derived from
    every csharp `DANGEROUS_OPERATIONS` entry whose own `library` is one
    of `_CS_WILDCARD_DANGEROUS_NAMESPACES` -- a needle's leading identifier
    segment (`new `/`[` stripped, then split on the first `(` or `.`)
    names the TYPE it hangs off (`"File.Delete("` -> `"File"`, `"new
    TcpClient("` -> `"TcpClient"`). Disambiguates a bare identifier used
    as a member-access base when SEVERAL curated namespaces are `using`'d
    in the same file at once (`using System; using System.Diagnostics;
    using System.IO;` -- a plain longest-string or alphabetical tie-break
    cannot reliably tell `File` belongs under `System.IO`, not `System`
    or `System.Diagnostics`, but the registry's own needle table already
    knows). Single source of truth (no duplication): every entry here
    traces back to `_dangerous_ops_bash_csharp.py`'s own needle strings,
    never a second hand-typed type/namespace list."""
    mapping: dict[str, str] = {}
    for entry in DANGEROUS_OPERATIONS:
        if (
            entry.language != "csharp"
            or entry.library not in _CS_WILDCARD_DANGEROUS_NAMESPACES
        ):
            continue
        for needle in entry.needles:
            cleaned = needle
            if cleaned.startswith("new "):
                cleaned = cleaned[4:]
            if cleaned.startswith("["):
                cleaned = cleaned[1:]
            cleaned = cleaned.split("(", 1)[0]
            head = cleaned.split(".", 1)[0]
            if head:
                mapping.setdefault(head, entry.library)
    return mapping


#: computed once at import time (T-4536) -- `DANGEROUS_OPERATIONS`
#: is a frozen module-level tuple, so this never needs to be recomputed per
#: file the way a per-call cache would.
_CS_WILDCARD_TYPE_NAMESPACES: dict[str, str] = _cs_derive_wildcard_type_namespaces()


def _cs_cap_child_of_type(node, type_name: str):  # noqa: ANN001, ANN201
    """The first DIRECT child of `node` with tree-sitter type `type_name`
    (T-4536) -- kept as a positional fallback for the handful of
    csharp grammar nodes (`using_directive`'s alias/`static` shape) with no
    labeled field, mirroring `_kt_cap_child_of_type`'s identical role."""
    for c in node.children:
        if c.type == type_name:
            return c
    return None


_CS_USING_TARGET_TYPES = frozenset({"identifier", "qualified_name", "generic_name"})


def _cs_import_table(
    root,  # noqa: ANN001
) -> tuple[dict[str, str], frozenset[str], frozenset[str]]:
    """(alias/last-segment -> fully-dotted-path import table, `using
    static` fully-dotted class targets, curated wildcard namespace
    prefixes actually `using`'d in this file) built from every `using_
    directive` (T-4536, taxonomy "using"/"using alias ="/"using
    static" rows). A plain `using A.B.C;` binds `C` (the target's own last
    dotted segment) to the full path -- redundant with the raw lexical
    scan when `C` already IS the needle's literal text, harmless, matching
    kotlin's identical "declared + direct call needs no special
    resolution" precedent -- AND records `A.B.C` itself as a curated
    wildcard prefix candidate when it is in `_CS_WILDCARD_DANGEROUS_
    NAMESPACES` (a plain csharp `using` genuinely brings every type in
    that namespace into unqualified scope, unlike kotlin's per-class
    import). `using Alias = A.B.C;` binds `Alias` instead (works whether
    `A.B.C` names a namespace or a type -- both resolve identically
    through this one table). `using static A.B.C;` records `A.B.C` in the
    static-using set, for resolving a bare call through it."""
    table: dict[str, str] = {}
    static_usings: set[str] = set()
    wildcard: set[str] = set()

    def visit(node) -> None:  # noqa: ANN001
        if node.type == "using_directive":
            is_static = _cs_cap_child_of_type(node, "static") is not None
            target = None
            for c in node.named_children:
                if c.type in _CS_USING_TARGET_TYPES:
                    target = c
            if target is None:
                for child in node.children:
                    visit(child)
                return
            dotted = node_text(target)
            alias_id = None
            seen_eq = False
            for c in node.children:
                if c.type == "=":
                    seen_eq = True
                elif c.type == "identifier" and not seen_eq and c is not target:
                    alias_id = c
            if is_static:
                static_usings.add(dotted)
            elif alias_id is not None:
                table[node_text(alias_id)] = dotted
            else:
                table.setdefault(dotted.rsplit(".", 1)[-1], dotted)
                if dotted in _CS_WILDCARD_DANGEROUS_NAMESPACES:
                    wildcard.add(dotted)
        for child in node.children:
            visit(child)

    visit(root)
    return table, frozenset(static_usings), frozenset(wildcard)


# frob:ticket T-4536
# frob:waive ARCH001 reason="one recursive dispatch over csharp's three resolvable expression shapes (identifier/member_access_expression/invocation_expression); each branch is a single named case, splitting further would multiply indirection without shrinking real complexity" ceiling="95"  # noqa: E501
# frob:invariant terminates reason="the member_access_expression and invocation_expression branches recurse only into their own field's own descendant, one or more tree-sitter edges below node, in the finite parse tree" measure="tree-sitter AST depth under node, finite per parse"  # noqa: E501
def _cs_resolve_expr_text(
    node,  # noqa: ANN001
    import_table: dict[str, str],
    var_alias_table: dict[str, str],
    static_usings: frozenset[str] = frozenset(),
    wildcard_namespaces: frozenset[str] = frozenset(),
    *,
    is_bare_call_target: bool = False,
) -> str | None:
    """Resolve one csharp expression node to a fully-dotted target text
    (T-4536) -- a bare `identifier` through `var_alias_table`
    then `import_table` then (last resort) a curated `using static`
    prefix (`WriteLine` -> `System.Console.WriteLine` when `using static
    System.Console;` is in scope) or curated wildcard-namespace prefix
    (`File` -> `System.IO.File` when `using System.IO;` is in scope); a
    `member_access_expression` (`IO.File.WriteAllText`) by resolving its
    `expression` field (recursively) and appending `.name`; an
    `invocation_expression` used as a base (`GetClient().Foo`) by
    resolving its own `function` field. Returns `None` when nothing
    resolves (never falls back to a bare, un-aliased name -- the pre-
    existing lexical scan already covers that case, matching every other
    language resolver's identical contract)."""
    if node.type == "identifier":
        name = node_text(node)
        if name in var_alias_table:
            return var_alias_table[name]
        direct = import_table.get(name)
        if direct is not None:
            return direct
        # T-4536: `using static` only brings a TYPE's own
        # members into bare-call scope (`WriteLine()` via `using static
        # System.Console;`) -- it is never the right fallback for an
        # identifier used as a member-access BASE (`File.WriteAllText`
        # must fall through to the wildcard-namespace branch below, never
        # resolve as `System.Console.File`).
        if is_bare_call_target and static_usings:
            return f"{max(static_usings, key=len)}.{name}"
        if wildcard_namespaces:
            # T-4536: disambiguate via the registry-derived
            # type->namespace map first (`File` always resolves against
            # `System.IO`, never `System`, when both are `using`'d and
            # `File` is a KNOWN dangerous type under `System.IO`); only
            # an unrecognized type name falls back to the longest (most
            # specific) curated namespace as a deterministic last resort
            # -- harmless either way, since an unrecognized type name
            # cannot match a registry needle regardless of which
            # namespace prefix it lands under.
            namespace = _CS_WILDCARD_TYPE_NAMESPACES.get(name)
            if namespace is None or namespace not in wildcard_namespaces:
                namespace = max(wildcard_namespaces, key=len)
            return f"{namespace}.{name}"
        return None
    if node.type in ("qualified_name", "generic_name"):
        # already-contiguous dotted source text (T-4536): no
        # per-segment walk needed, but the LEADING segment may itself be
        # an alias (`IO.SomeType` where `using IO = System.IO;`).
        text = node_text(node)
        head, _, rest = text.partition(".")
        resolved_head = var_alias_table.get(head) or import_table.get(head)
        if resolved_head is not None:
            return f"{resolved_head}.{rest}" if rest else resolved_head
        return text
    if node.type == "member_access_expression":
        base = node.child_by_field_name("expression")
        member = node.child_by_field_name("name")
        if base is None or member is None:
            return None
        resolved_base = _cs_resolve_expr_text(
            base, import_table, var_alias_table, static_usings, wildcard_namespaces
        )
        if resolved_base is not None:
            base_resolved = resolved_base
        elif base.type == "identifier":
            # unresolvable bare identifier base: fall back to its own
            # literal text (a plain local var/type name with no import,
            # alias, or curated wildcard behind it) -- matches every
            # other language resolver's "declared + direct call needs no
            # special resolution" precedent.
            base_resolved = node_text(base)
        else:
            return None
        return f"{base_resolved}.{node_text(member)}"
    if node.type == "invocation_expression":
        callee = node.child_by_field_name("function")
        if callee is None:
            return None
        inner = _cs_resolve_expr_text(
            callee,
            import_table,
            var_alias_table,
            static_usings,
            wildcard_namespaces,
            is_bare_call_target=callee.type == "identifier",
        )
        return f"{inner}()" if inner is not None else None
    return None


def _cs_object_creation_type_text(node) -> str | None:  # noqa: ANN001
    """The fully-dotted type text of an `object_creation_expression`
    (T-4536, taxonomy "var local bound from `new Ns.Type(...)`"
    row) -- its `type` field, whose own text is already contiguous dotted
    source (`qualified_name`/`generic_name`/`identifier`), returned
    verbatim. `None` for any other node shape."""
    if node.type != "object_creation_expression":
        return None
    type_node = node.child_by_field_name("type")
    if type_node is None:
        return None
    return node_text(type_node)


def _cs_build_var_alias_table(root, import_table: dict[str, str]) -> dict[str, str]:  # noqa: ANN001
    """File-wide `name -> resolved_target` table (T-4536,
    taxonomy "var local bound from `new Ns.Type(...)`"/"delegate bound
    from a method-group reference" rows) built from every `variable_
    declarator` whose value is an `object_creation_expression` (`var
    client = new System.Net.Http.HttpClient();` binds `client` to
    `System.Net.Http.HttpClient`, so a later `client.GetAsync(...)`
    resolves) or a resolvable expression (a method-group delegate
    binding, `Action<string> f = File.Delete;`), visited in source
    (document) order so a chain (`var a = new T(); var b = a;`) is not
    attempted -- csharp's `object_creation_expression`/plain-identifier
    RHS shapes are the only two this registry's taxonomy needs, mirroring
    kotlin's identical narrow-RHS-shape posture in `_kt_build_var_alias_
    table`."""
    var_alias_table: dict[str, str] = {}

    def visit(node) -> None:  # noqa: ANN001
        if node.type == "variable_declarator":
            name_node = node.child_by_field_name("name")
            value = None
            seen_eq = False
            for c in node.children:
                if c.type == "=":
                    seen_eq = True
                    continue
                if seen_eq:
                    value = c
                    break
            if name_node is not None and value is not None:
                resolved = None
                type_text = _cs_object_creation_type_text(value)
                if type_text is not None:
                    resolved = type_text
                elif value.type == "member_access_expression":
                    resolved = _cs_resolve_expr_text(value, import_table, {})
                elif value.type == "identifier":
                    resolved = _cs_resolve_expr_text(value, import_table, {})
                if resolved is not None:
                    var_alias_table.setdefault(node_text(name_node), resolved)
        for child in node.children:
            visit(child)

    visit(root)
    return var_alias_table


def _cs_collect_candidates(
    node,  # noqa: ANN001
    import_table: dict[str, str],
    var_alias_table: dict[str, str],
    static_usings: frozenset[str],
    wildcard_namespaces: frozenset[str],
    candidates: list[tuple[str, int, int]],
) -> None:
    """Recursively walk `node`, appending `(resolved, start_byte,
    end_byte)` to `candidates` for every `invocation_expression` whose
    callee resolves through `_cs_resolve_expr_text` (T-4536) --
    mirrors `_kt_collect_candidates`'s job."""
    if node.type == "invocation_expression":
        callee = node.child_by_field_name("function")
        if callee is not None and callee.type in (
            "identifier",
            "member_access_expression",
        ):
            resolved = _cs_resolve_expr_text(
                callee,
                import_table,
                var_alias_table,
                static_usings,
                wildcard_namespaces,
                is_bare_call_target=callee.type == "identifier",
            )
            if resolved is not None:
                candidates.append((resolved, node.start_byte, node.end_byte))
    for child in node.children:
        _cs_collect_candidates(
            child,
            import_table,
            var_alias_table,
            static_usings,
            wildcard_namespaces,
            candidates,
        )


def _cs_resolved_candidates(path: Path) -> tuple[tuple[str, int, int], ...]:
    """Every `(resolved_name, start_byte, end_byte)` this csharp file's
    call sites resolve to through its `using` table (plain/aliased/
    `static`) and file-wide `var`-local/delegate alias table
    (T-4536). Empty for a non-csharp file, an unparseable file,
    or one `frob.lang` has no grammar for -- degrades to the pre-existing
    lexical-only scan, never raises."""
    parsed = raw_tree(path)
    if parsed.is_err:
        return ()
    tree, _source, language_label = parsed.danger_ok
    if language_label != "csharp":
        return ()

    import_table, static_usings, wildcard_namespaces = _cs_import_table(tree.root_node)
    var_alias_table = _cs_build_var_alias_table(tree.root_node, import_table)
    candidates: list[tuple[str, int, int]] = []
    _cs_collect_candidates(
        tree.root_node,
        import_table,
        var_alias_table,
        static_usings,
        wildcard_namespaces,
        candidates,
    )
    return tuple(candidates)


# frob:ticket T-4536
# frob:waive DUP001 reason="sibling per-language capability-resolution entry point across all six binding families; each caller's own language dispatch needs its own named symbol, a shared indirection layer would add a callback parameter to remove a shape this small"  # noqa: E501
def _cs_binding_capabilities(
    path: Path,
    table: dict[str, tuple[str, ...]],
    comment_spans: tuple[ByteSpan, ...],
) -> set[str]:
    """Capability kinds observed via csharp `using`/alias-aware resolution
    only (T-4536) -- the union of every registry needle that
    matches a resolved call target, for sites outside a comment span.
    Merged into `scan_file_capabilities`'s lexical result. Mirrors `_kt_
    binding_capabilities`."""
    found: set[str] = set()
    for resolved, start, end in _cs_resolved_candidates(path):
        if _fully_in_any_span(start, end, comment_spans):
            continue
        for capability, needles in table.items():
            if capability in found:
                continue
            if any(_needle_matches_resolved(needle, resolved) for needle in needles):
                found.add(capability)
    return found


# frob:ticket T-4536
# frob:waive DUP001 reason="sibling per-language DANGEROUS_OPERATIONS entry-matching pass across all six binding families; each caller's own language dispatch needs its own named symbol, a shared indirection layer would add a callback parameter to remove a shape this small"  # noqa: E501
def _cs_binding_operations(
    path: Path, comment_spans: tuple[ByteSpan, ...]
) -> tuple[_DangerousOperation, ...]:
    """`DANGEROUS_OPERATIONS` csharp entries observed via `using`/alias-
    aware resolution only (T-4536) -- `_scan_file_operations`'s
    resolver-backed sibling to `_cs_binding_capabilities`. Mirrors `_kt_
    binding_operations`."""
    candidates = _cs_resolved_candidates(path)
    if not candidates:
        return ()
    matched: list[_DangerousOperation] = []
    for entry in DANGEROUS_OPERATIONS:
        if entry.language != "csharp" or not entry.needles:
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


# frob:ticket T-4536
# frob:waive DUP001 reason="sibling small set-based dedupe helper across all six per-language binding families (python/typescript/rust/c-cpp/kotlin/csharp); extracting a shared helper would need a language-specific callback parameter, adding real indirection to remove a shape this small"  # noqa: E501
def _extra_cs_binding_operations(
    path: Path,
    comment_spans: tuple[ByteSpan, ...],
    already_matched: list[_DangerousOperation],
) -> list[_DangerousOperation]:
    """`_cs_binding_operations` entries not already present in
    `already_matched` (T-4536) -- csharp sibling of `_extra_kt_
    binding_operations`, same set-based dedupe."""
    seen = set(already_matched)
    extra: list[_DangerousOperation] = []
    for entry in _cs_binding_operations(path, comment_spans):
        if entry not in seen:
            extra.append(entry)
            seen.add(entry)
    return extra
