"""Python import/binding-aware capability resolution (T-1420 LARGE001
split, T-1459 design step 2): scope-binding, alias-table construction, and
resolved-candidate collection for the python `_DangerousOperation` needle
family, split verbatim out of `frob.vet._capability` (T-0328 lineage).
Every name here is re-exported (or imported back) by `_capability` so the
module's public surface is unchanged."""

# frob:ticket T-1420
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from frob.graph.callgraph import CallGraph, build_call_graph, closure
from frob.lang import node_text, raw_tree

from ._capability_core import (
    ByteSpan,
    _compiled_capability_patterns,
    _fully_in_any_span,
    _needle_matches_resolved,
    _non_executable_byte_spans,
    _string_content_bytes,
)
from ._capability_registry import DANGEROUS_OPERATIONS, _DangerousOperation

# T-0328: import/binding-aware resolution for Python, the priority language
# (highest coverage). The plain substring scan above is EVADED by ordinary
# aliasing/from-import Python -- `import subprocess as sp; sp.run(x)` never
# contains the literal text "subprocess.run(" the needle table looks for,
# and `from os import system as e; e(x)` contains neither "os.system(" nor
# "eval(", so the scanner observes NOTHING even though the code genuinely
# execs. This block builds a per-file IMPORT/BINDING TABLE from the same
# tree-sitter parse `_comment_byte_spans` already uses, resolves each
# call/attribute site's leftmost name through it (reconstructing the
# fully-qualified target, e.g. `sp.run` -> `subprocess.run`), and re-checks
# the SAME needle tables against the RESOLVED identity string instead of
# raw source text -- no new registry field, no new needle vocabulary, just
# a second pass over a synthesized "what this call/attribute actually
# refers to" string. Every resolved match is still confirmed against
# `comment_spans` before counting (T-0209 posture unchanged).
#
# Scope-awareness (mandatory to avoid FALSE POSITIVES): a LOCAL binding --
# a function/method parameter, an assignment target, a `for`/`with ... as`
# target, or a nested `def`/`class` name -- SHADOWS an import of the same
# name in every enclosing scope from the site up to module level. `def
# g(system): system(x)` (param) and `class Job: def run(self): ...` then
# `Job().run()` (method access on an unrelated object) must NOT resolve to
# `os.system`/a dangerous `run`, because the leftmost name in each case
# either resolves to a local binding (shadowed) or to an expression this
# resolver deliberately does not chase further (a `call` node, e.g.
# `Job()`, is not a resolvable "object" for attribute-chain purposes, so
# `Job().run` never reaches the import table at all).
#
# Known limitations, documented rather than silently eaten (mirrors this
# module's existing "Honest limits" posture): `from X import *` adds no
# binding (a star-imported name is untraceable without also modeling X's
# own exports); a function-scoped `import` is folded into the SAME
# file-wide binding table as a module-level one (a narrow, safe-direction
# over-approximation -- it can only ADD a resolution, never suppress a
# real one); a relative import's dotted text (`from . import x`) is kept
# as literal text (`"..x"`-shaped), which will not coincidentally collide
# with any real registry needle in practice. TS/C-C++ are OUT of scope for
# this pass -- C/C++'s `#include` is coarse-only by design (module
# docstring), and TS's binding table is noted as follow-up work, not
# attempted here. Rust gets its own binding-aware pass, T-0378 below.
#
# T-1626: two evasions the T-0328 resolver used to miss silently (the
# ticket's own worked examples) are now resolved rather than dropped:
# `functools.partial(dangerous, ...)` (`_resolve_py_expr`'s `call` branch
# recognizes a resolved-`functools.partial` callee and resolves through to
# its first positional argument -- `p = functools.partial(os.system, cmd);
# p()` now resolves `p()` to `os.system`), and a literal-keyed dict/list
# dispatch (`_record_py_dict_container_alias`/`_record_py_list_container_
# alias` record one alias entry per literal key/index at assignment time,
# `_resolve_py_subscript` looks it up at the call site -- `funcs = {"run":
# subprocess.run}; funcs["run"](cmd)` now resolves). Both stayed
# genuinely silent before: a NON-literal key/index or a dynamically
# computed `getattr` name is a SEPARATE, already-covered case --
# `frob.gates._opaque`'s OPAQUE001 (`RUNTIME_OPAQUE_CONSTRUCTS`/
# `RUNTIME_OPAQUE_STRUCTURAL_CONSTRUCTS`, `_capability_scan.py`) already
# fires fail-closed on those (non-literal subscript-then-call, bare
# `getattr(`/`setattr(`/`eval(`/`exec(`/`__import__(`) -- this module
# only had to close the LITERAL-key gap OPAQUE001 explicitly defers to
# "the ordinary resolver's job" (`_subscript_key_looks_literal`'s
# docstring) but the ordinary resolver never actually implemented until
# now, which meant a literal-keyed dict/list dispatch fell through BOTH
# mechanisms: too resolvable to trip OPAQUE001, never actually resolved
# by this module. Cross-file wrapper attribution (a helper in another
# module forwarding to a dangerous callable) is NOT attempted here -- it
# needs `frob.graph.callgraph`-backed cross-file call resolution, a
# larger, separate unit of work; see T-1626's Done report / follow-up
# ticket for the split.
_PY_SCOPE_TYPES = ("function_definition", "class_definition", "module")


#: every literal needle registered for a python `_DangerousOperation`
#: (T-0659) -- flattened once at import time so `_py_target_is_dangerous`
#: can classify an already-resolved dotted target without re-deriving the
#: needle table on every call. Deliberately the SAME needle vocabulary the
#: rest of this module scans with (no parallel "dangerous name" list to
#: desync), just flattened across capability boundaries since fallback-
#: ordering safety (below) does not care WHICH capability a target belongs
#: to, only whether it is dangerous at all.
_PY_ALL_DANGEROUS_NEEDLES: tuple[str, ...] = tuple(
    needle
    for entry in DANGEROUS_OPERATIONS
    if entry.language == "python"
    for needle in entry.needles
)

#: every python stdlib/library module name `DANGEROUS_OPERATIONS` curates
#: an entry for (T-0659) -- used ONLY to decide whether a `from X import *`
#: wildcard is worth a best-effort fallback resolution (see
#: `_bind_import_from_statement`'s wildcard branch); a module absent from
#: this set gets no wildcard binding at all (an honest, documented under-
#: approximation for a star-import re-export of an UNTRACKED module,
#: matching the taxonomy's "degrades to opaque" caveat) rather than a
#: false claim of resolution.
_PY_WILDCARD_DANGEROUS_MODULES: frozenset[str] = frozenset(
    entry.library for entry in DANGEROUS_OPERATIONS if entry.language == "python"
)

#: sentinel import-table KEY (not a legal python identifier, so it can
#: never collide with a real bound name) recording the set of wildcard-
#: imported dangerous modules for a file, NUL-joined (T-0659). Piggybacked
#: onto the plain `dict[str, str]` import table instead of widening every
#: resolver signature to carry a second collection -- see
#: `_bind_import_from_statement`'s wildcard branch and
#: `_resolve_py_identifier`'s fallback read.
_PY_WILDCARD_TABLE_KEY = "*"


def _py_target_is_dangerous(target: str) -> bool:
    """True if the resolved dotted `target` (e.g. `"subprocess.run"`) matches
    ANY python registry needle (T-0659) -- the single classification
    `_bind_py_name` uses to keep a dangerous import-table binding from
    being silently overwritten by a later, benign one (the conditional/
    try-except import-fallback soundness gap: order should never determine
    whether a genuinely dangerous alternative is observed)."""
    haystack = f"{target}("
    return any(
        needle in target or needle in haystack for needle in _PY_ALL_DANGEROUS_NEEDLES
    )


def _bind_py_name(table: dict[str, str], name: str, target: str) -> None:
    """Bind `name -> target` in `table`, UNLESS `name` already resolves to a
    dangerous target and `target` itself is not dangerous (T-0659): plain
    dict assignment is order-sensitive, so a `try`/`except ImportError`
    fallback pair binding the SAME name to a dangerous import in one branch
    and a benign one in the other silently loses the dangerous binding
    whenever the benign branch happens to be walked last (`_py_import_table`
    walks the whole tree unconditionally, with no notion of which branch
    actually executes at runtime -- a may-analysis over-approximation, by
    design, of exactly the kind T-0337's alias table already documents).
    Keeping the more dangerous of the two candidates makes detection
    ORDER-INDEPENDENT: whichever branch runs at runtime, the fallback
    pattern is still flagged."""
    existing = table.get(name)
    if (
        existing is not None
        and _py_target_is_dangerous(existing)
        and not _py_target_is_dangerous(target)
    ):
        return
    table[name] = target


#: sentinel `bound` position meaning "shadows from the very start of the
#: scope, regardless of call-site position" -- used for function/lambda
#: PARAMETERS (always in scope for the whole body) and nested `def`/`class`
#: names (mirrors Rust's `_RUST_ALWAYS_SHADOWS`, T-0378 round 2). Only
#: assignment-style targets get a REAL position (T-0468, see
#: `_collect_target_names`).
_PY_ALWAYS_SHADOWS = -1


def _record_py_binding(bound: dict[str, int], name: str, position: int) -> None:
    """Record that `name` starts shadowing an enclosing import binding at
    byte `position` within its scope, keeping the EARLIEST position on
    repeat bindings of the same name (a name rebound twice still shadows
    from its first occurrence onward, never un-shadows) -- the position-
    aware T-0468 fix's core bookkeeping primitive, mirrors Rust's
    `_record_rust_binding`."""
    existing = bound.get(name)
    bound[name] = position if existing is None else min(existing, position)


def _collect_target_names(node, position: int, bound: dict[str, int]) -> None:  # noqa: ANN001
    """Add every name an assignment-style TARGET pattern binds to `bound` AT
    `position` (T-0468: the enclosing assignment/`as`-pattern/walrus node's
    own `start_byte`, so a call site textually BEFORE this binding is not
    wrongly treated as already shadowed -- Python assignment does not
    hoist), recursing through tuple/list patterns and `as`-pattern wrappers
    but never through `attribute`/`subscript` targets (`obj.attr = x` /
    `obj[i] = x` mutate an existing object; they bind no new name)."""
    node_type = node.type
    if node_type == "identifier":
        _record_py_binding(bound, node_text(node), position)
        return
    if node_type in ("attribute", "subscript"):
        return
    for child in node.children:
        _collect_target_names(child, position, bound)


def _collect_param_name(node, bound: dict[str, int]) -> None:  # noqa: ANN001
    """Add one `parameters`-node child's bound name to `bound` at
    `_PY_ALWAYS_SHADOWS` (a plain `identifier`, or the name identifier
    inside `typed_parameter`/`default_parameter`/`typed_default_parameter`/
    `*args`/`**kwargs` patterns); punctuation/type-annotation/default-value
    children are skipped by construction (only the node's OWN direct
    `identifier` child is taken, never one nested inside a `type`
    subtree). A parameter is in scope for the WHOLE function body, so it
    shadows regardless of call-site position -- mirrors Rust's
    `_collect_rust_param_name`."""
    node_type = node.type
    if node_type == "identifier":
        _record_py_binding(bound, node_text(node), _PY_ALWAYS_SHADOWS)
        return
    if node_type in (
        "typed_parameter",
        "default_parameter",
        "typed_default_parameter",
        "list_splat_pattern",
        "dictionary_splat_pattern",
    ):
        for child in node.children:
            if child.type == "identifier":
                _record_py_binding(bound, node_text(child), _PY_ALWAYS_SHADOWS)
                return


def _scope_bind_step(node, is_top: bool, bound: dict[str, int]) -> bool:  # noqa: ANN001
    """Handle ONE node during `_py_scope_bound_names`'s walk: add whatever
    name(s) `node` binds directly to `bound` (with `_PY_ALWAYS_SHADOWS` for
    params/nested-def-class names, or the binding node's own `start_byte`
    for an assignment/`as`-pattern/walrus target, T-0468), and report
    whether the walk should recurse into `node`'s children (False at a
    nested scope boundary -- only its OWN name binds in the parent scope,
    never its body; True otherwise)."""
    node_type = node.type
    if not is_top and node_type in ("function_definition", "class_definition"):
        name_node = node.child_by_field_name("name")
        if name_node is not None:
            _record_py_binding(bound, node_text(name_node), _PY_ALWAYS_SHADOWS)
        return False
    if not is_top and node_type == "lambda":
        return False
    if node_type in ("parameters", "lambda_parameters"):
        for child in node.children:
            _collect_param_name(child, bound)
        return False
    if node_type in ("assignment", "augmented_assignment", "for_statement"):
        left = node.child_by_field_name("left")
        if left is not None:
            _collect_target_names(left, node.start_byte, bound)
    elif node_type == "as_pattern_target":
        _collect_target_names(node, node.start_byte, bound)
    elif node_type == "named_expression":
        name_node = node.child_by_field_name("name")
        if name_node is not None:
            _record_py_binding(bound, node_text(name_node), node.start_byte)
    return True


def _py_scope_bound_names(scope_node) -> dict[str, int]:  # noqa: ANN001
    """Every name bound DIRECTLY within `scope_node` (a `function_
    definition`/`class_definition`/`module` node), mapped to the byte
    position from which it starts shadowing an enclosing import binding --
    parameters and nested `def`/`class` names at `_PY_ALWAYS_SHADOWS`,
    assignment/`for`/`with ... as`/walrus targets at their own binding
    node's `start_byte` -- WITHOUT recursing into a nested scope's own
    body. This is the per-scope shadow table every call/attribute site is
    checked against before ever consulting the import binding table
    (T-0328: mandatory scope-awareness so a local `run`/`system`/etc.
    never resolves to an imported dangerous symbol of the same name).
    T-0468: POSITION-aware (mirrors Rust's `_rust_scope_bound_names`,
    T-0378 round 2) so a call site textually BEFORE a same-named rebind is
    correctly NOT treated as shadowed -- Python assignment does not hoist;
    a use before the rebind refers to whatever the name resolved to
    beforehand (here, the import-bound alias), same as the real Python
    name-resolution rule this scanner approximates."""
    bound: dict[str, int] = {}

    def walk(node, is_top: bool) -> None:  # noqa: ANN001
        if _scope_bind_step(node, is_top, bound):
            for child in node.children:
                walk(child, False)

    walk(scope_node, True)
    return bound


def _bind_import_statement(node, table: dict[str, str]) -> None:  # noqa: ANN001
    """One `import_statement` node's contribution to `_py_import_table`
    (T-0328): `import X` -> `{X: X}` (bare `import a.b` binds only the top
    package name `a`, matching real Python semantics), `import X as Y` ->
    `{Y: X}`."""
    for name_node in node.children_by_field_name("name"):
        if name_node.type == "dotted_name":
            full = node_text(name_node)
            first = full.split(".", 1)[0]
            table.setdefault(first, first)
        elif name_node.type == "aliased_import":
            dotted = name_node.child_by_field_name("name")
            alias = name_node.child_by_field_name("alias")
            if dotted is not None and alias is not None:
                _bind_py_name(table, node_text(alias), node_text(dotted))


def _bind_import_from_statement(node, table: dict[str, str]) -> None:  # noqa: ANN001
    """One `import_from_statement` node's contribution to `_py_import_table`
    (T-0328): `from X import Z` -> `{Z: X.Z}`, `from X import Z as W` ->
    `{W: X.Z}`.

    T-0659: `from X import *` (`wildcard_import`) is no longer an
    unconditional no-op. A star import's individual re-exported names are
    genuinely untraceable in general (real limitation: this file alone
    cannot enumerate `X`'s own `__all__`/export surface), so this still
    adds NO per-name binding for an arbitrary `X`. But when `X` is one of
    the modules `DANGEROUS_OPERATIONS` already curates
    (`_PY_WILDCARD_DANGEROUS_MODULES`) -- exactly the closed, reviewed set
    this scanner's own needle tables treat as dangerous -- a star import of
    it is recorded via the `_PY_WILDCARD_TABLE_KEY` sentinel so
    `_resolve_py_identifier` can offer a best-effort `X.<name>` fallback
    resolution for any bare name that isn't otherwise bound (T-0339's
    "star-import re-export chain" row). This closes the specific evasion
    `from subprocess import *; run(x)` without claiming to resolve a star
    import of an arbitrary, untracked third-party module."""
    module_field = node.child_by_field_name("module_name")
    module_text = node_text(module_field) if module_field is not None else ""
    for name_node in node.children_by_field_name("name"):
        if name_node.type == "dotted_name":
            imported = node_text(name_node)
            target = f"{module_text}.{imported}" if module_text else imported
            _bind_py_name(table, imported, target)
        elif name_node.type == "aliased_import":
            dotted = name_node.child_by_field_name("name")
            alias = name_node.child_by_field_name("alias")
            if dotted is not None and alias is not None:
                imported = node_text(dotted)
                target = f"{module_text}.{imported}" if module_text else imported
                _bind_py_name(table, node_text(alias), target)
    if any(c.type == "wildcard_import" for c in node.children):
        # `wildcard_import` ("*") carries no `name` field of its own (it is
        # not itself a name being bound to anything), so it never appears
        # in the `children_by_field_name("name")` loop above -- checked
        # separately, directly against `node`'s children.
        if module_text in _PY_WILDCARD_DANGEROUS_MODULES:
            existing = table.get(_PY_WILDCARD_TABLE_KEY, "")
            modules = set(existing.split("\x00")) if existing else set()
            modules.add(module_text)
            table[_PY_WILDCARD_TABLE_KEY] = "\x00".join(sorted(modules))


def _py_import_table(module_node) -> dict[str, str]:  # noqa: ANN001
    """The file-wide local-name -> resolved-dotted-target binding table
    (T-0328), built from `_bind_import_statement`/`_bind_import_from_
    statement`. Walks the WHOLE tree (not just top-level statements) so a
    function-scoped import still contributes a binding -- a safe-direction
    over-approximation, see module docstring."""
    table: dict[str, str] = {}

    def visit(node) -> None:  # noqa: ANN001
        if node.type == "import_statement":
            _bind_import_statement(node, table)
        elif node.type == "import_from_statement":
            _bind_import_from_statement(node, table)
        for child in node.children:
            visit(child)

    visit(module_node)
    return table


def _shadowing_scope(name: str, site, scope_cache: dict[int, dict[str, int]]):  # noqa: ANN001, ANN201
    """The nearest LOCAL scope node enclosing `site` (site's own function ->
    class -> ... -> module, per `_py_scope_bound_names`, cached per scope
    node in `scope_cache`) that binds `name` directly AT OR BEFORE `site`'s
    own `start_byte`, or `None` if no enclosing scope binds it before this
    position -- the T-0328 shadow check every resolution goes through
    before consulting the import table. T-0337: returns the SCOPE NODE
    itself (rather than a bare bool) so a caller can look up whether that
    exact binding is a known dangerous local alias.

    T-0468 (soundness fix, mirrors T-0378 round 2's Rust fix): this used to
    be ORDER-INSENSITIVE -- it treated a name as shadowed anywhere in the
    enclosing scope, so a capability call occurring textually BEFORE a
    same-name rebind (`import os as o; o.system('ls'); o = None`) was
    silently missed (a real dangerous call un-flagged). Now POSITION-aware:
    a rebind recorded at a LATER byte position than `site` does NOT shadow
    this particular call site (it hasn't taken effect yet), so resolution
    correctly falls through to the import table instead of silently
    dropping a capability call that textually precedes its same-named
    local rebind. Parameters and nested `def`/`class` names still shadow
    unconditionally (`_PY_ALWAYS_SHADOWS`), since they are in scope for the
    whole enclosing body regardless of call-site position."""
    cur = site.parent
    while cur is not None:
        if cur.type in _PY_SCOPE_TYPES:
            key = cur.id
            cached = scope_cache.get(key)
            if cached is None:
                cached = _py_scope_bound_names(cur)
                scope_cache[key] = cached
            position = cached.get(name)
            if position is not None and site.start_byte >= position:
                return cur
            if cur.type == "module":
                break
        cur = cur.parent
    return None


def _resolve_py_expr(
    node,
    import_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    alias_table: dict[int, dict[str, str]] | None = None,
) -> str | None:  # noqa: ANN001
    """Resolve one expression node (a bare `identifier` or an `attribute`
    chain) to its fully-qualified import-bound target, or `None` if it is
    locally shadowed (by a binding with no known dangerous resolution) or
    not a resolvable chain at all (T-0328). Any other expression (a `call`,
    subscript, literal, ...) is not a resolvable "object" for attribute-
    chain purposes -- e.g. `Job()` in `Job().run()` deliberately stops
    resolution here, so `.run` never reaches the import table (the T-0328
    no-false-positive case).

    T-0337: when `node` is an identifier LOCALLY shadowed by an enclosing
    scope, this no longer gives up unconditionally -- it consults
    `alias_table` (built by `_build_py_alias_table`, keyed by `scope.id`)
    for a resolved dangerous target THAT SPECIFIC BINDING scope recorded
    for the name. A parameter or a name bound only to a benign value has no
    alias_table entry, so resolution still correctly returns `None` there
    (the T-0328 no-false-positive/shadow guarantee is unchanged); a name
    locally rebound to an import-table entry, a dangerous attribute chain,
    or another already-aliased dangerous name DOES have an entry and
    resolves through it -- this is the local-rebinding copy-propagation
    fix."""
    if node.type == "identifier":
        return _resolve_py_identifier(node, import_table, scope_cache, alias_table)
    if node.type == "attribute":
        # frob:invariant terminates reason="mutually recurses with \
        # _resolve_py_attribute, which only calls back here with \
        # node.child_by_field_name('object'), a proper descendant of node in the \
        # finite tree-sitter parse tree" measure="node's subtree depth strictly \
        # decreases"
        return _resolve_py_attribute(node, import_table, scope_cache, alias_table)
    if node.type == "subscript":
        # frob:invariant terminates reason="_resolve_py_subscript performs one \
        # alias_table dict lookup and does not call back into _resolve_py_expr -- no \
        # recursion" measure="not applicable, non-recursive"
        return _resolve_py_subscript(node, alias_table)
    if node.type == "call":
        # frob:invariant terminates reason="mutually recurses with \
        # _resolve_py_partial_call, which only calls back here with node's own \
        # 'function' field child or a child of node's own 'arguments' field, both \
        # proper descendants of node in the finite tree-sitter parse tree" \
        # measure="node's subtree depth strictly decreases"
        return _resolve_py_partial_call(node, import_table, scope_cache, alias_table)
    if node.type == "assignment":
        # T-0659: a CHAINED assignment's right-hand side (`a = b = target`)
        # parses as a nested `assignment` node (`b = target`), not an
        # identifier/attribute -- peel through it to the ultimate value so
        # a chain of any depth resolves the same way a single assignment
        # does. `_record_py_alias` already visits the nested assignment
        # separately (it recurses over every child), so this is the one
        # piece that was missing: the OUTER target (`a` above) previously
        # saw `right.type == "assignment"` and gave up.
        right = node.child_by_field_name("right")
        if right is None:
            return None
        # frob:invariant terminates reason="right is node's own 'right' field child, a \
        # proper descendant of node in the finite tree-sitter parse tree" \
        # measure="node's subtree depth strictly decreases"
        return _resolve_py_expr(right, import_table, scope_cache, alias_table)
    return None


# frob:ticket T-0361
def _resolve_py_identifier(
    node,
    import_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    alias_table: dict[int, dict[str, str]] | None,
) -> str | None:  # noqa: ANN001
    """Resolve a bare `identifier` node to its import-bound target, consulting
    `alias_table` for locally-shadowed names (T-0337); split out of
    `_resolve_py_expr`'s identifier branch (T-0361).

    T-0659: when `name` has no direct import/alias binding at all (never
    imported, never shadowed), falls back to the `_PY_WILDCARD_TABLE_KEY`
    sentinel -- a best-effort `module.name` resolution for any bare name
    when the file did `from module import *` for a module
    `DANGEROUS_OPERATIONS` curates (see `_bind_import_from_statement`).
    Ambiguous when more than one dangerous module is star-imported in the
    same file (picks the lexicographically first, a documented, narrow
    edge case); never fires for an ordinary un-imported bare name (the
    T-0328 `test_bare_name_call_with_no_import_not_detected` guarantee is
    unaffected since the sentinel key is only ever present when a matching
    wildcard import was actually seen)."""
    name = node_text(node)
    scope = _shadowing_scope(name, node, scope_cache)
    if scope is not None:
        if alias_table is None:
            return None
        return alias_table.get(scope.id, {}).get(name)
    direct = import_table.get(name)
    if direct is not None:
        return direct
    wildcards = import_table.get(_PY_WILDCARD_TABLE_KEY)
    if wildcards:
        module = sorted(wildcards.split("\x00"))[0]
        return f"{module}.{name}"
    return None


# frob:ticket T-0361
def _resolve_py_attribute(
    node,
    import_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    alias_table: dict[int, dict[str, str]] | None,
) -> str | None:  # noqa: ANN001
    """Resolve an `attribute` chain node by recursively resolving its
    `object` child through `_resolve_py_expr` and appending the attribute
    name; split out of `_resolve_py_expr`'s attribute branch (T-0361)."""
    obj = node.child_by_field_name("object")
    attr = node.child_by_field_name("attribute")
    if obj is None or attr is None:
        return None
    # frob:invariant terminates reason="obj is node's own 'object' field child, a \
    # proper descendant of node in the finite tree-sitter parse tree; mutually \
    # recurses with _resolve_py_expr, which only descends into the 'attribute' branch \
    # by calling back here" measure="node's subtree depth strictly decreases"
    resolved_obj = _resolve_py_expr(obj, import_table, scope_cache, alias_table)
    if resolved_obj is not None:
        return f"{resolved_obj}.{node_text(attr)}"
    # T-0659: `obj` is not itself resolvable through the import table (it is
    # an ordinary local name, not an import or a name aliased to one) --
    # but its OWN `.attr` may have been directly REBOUND to a dangerous
    # target (`mod.run = subprocess.run; mod.run(x)`, taxonomy "attribute
    # rebinding"). `_attr_rebind_lookup` checks for that best-effort, by-
    # name binding (not a real points-to alias -- `mod` is identified only
    # by its local name, documented in `_record_py_alias`).
    if obj.type == "identifier" and alias_table is not None:
        return _attr_rebind_lookup(node_text(obj), node_text(attr), node, alias_table)
    return None


def _resolve_py_partial_call(
    node,  # noqa: ANN001
    import_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    alias_table: dict[int, dict[str, str]] | None,
) -> str | None:
    """Resolve a `call` node through the `functools.partial(dangerous, ...)`
    evasion (T-1626, split out of `_resolve_py_expr`'s `call` branch to keep
    that function under ARCH001's line threshold): resolve the CALLEE
    first, and if it is (an alias of) `functools.partial` itself, the
    call's own resolved identity is whatever its first positional argument
    resolves to (`p = functools.partial(os.system, cmd)` makes `p` an
    alias for `os.system`, handled by the ordinary assignment/alias-table
    path once THIS resolves; `functools.partial(os.system, cmd)()` called
    directly also resolves here). Any other callee -- an ordinary function
    call like `Job()` -- returns `None`, matching `_resolve_py_expr`'s
    pre-existing "a `call` node is not a resolvable object" posture for
    everything except this one recognized wrapper shape."""
    func = node.child_by_field_name("function")
    if func is None:
        return None
    # frob:invariant terminates reason="func is node's own 'function' field child, a \
    # proper descendant of node in the finite tree-sitter parse tree; mutually \
    # recurses with _resolve_py_expr, which only descends into the 'call' branch by \
    # calling back here" measure="node's subtree depth strictly decreases"
    resolved_func = _resolve_py_expr(func, import_table, scope_cache, alias_table)
    if resolved_func != "functools.partial":
        return None
    arguments = node.child_by_field_name("arguments")
    if arguments is None:
        return None
    target = _first_py_positional_arg(arguments)
    if target is None:
        return None
    # frob:invariant terminates reason="target is a child of node's own 'arguments' \
    # field, a proper descendant of node in the finite tree-sitter parse tree; \
    # mutually recurses with _resolve_py_expr, which only descends into the 'call' \
    # branch by calling back here" measure="node's subtree depth strictly decreases"
    return _resolve_py_expr(target, import_table, scope_cache, alias_table)


def _py_scope_alias_lookup(
    key: str,
    site,  # noqa: ANN001
    alias_table: dict[int, dict[str, str]],
) -> str | None:
    """Walk `site`'s enclosing python scope chain (function -> class -> ...
    -> module, stopping at module) looking up `key` in each scope's
    `alias_table` entry (T-1626: shared scope-walk primitive -- was
    `_attr_rebind_lookup`'s own body verbatim; also used by the T-1626
    container (dict/list literal, subscript-by-literal-key) alias lookup so
    both routes share ONE scope walk instead of two copies of the same
    loop). Returns `None` if no enclosing scope ever recorded `key`."""
    cur = site.parent
    while cur is not None:
        if cur.type in _PY_SCOPE_TYPES:
            found = alias_table.get(cur.id, {}).get(key)
            if found is not None:
                return found
            if cur.type == "module":
                break
        cur = cur.parent
    return None


def _attr_rebind_lookup(
    obj_name: str,
    attr_name: str,
    site,  # noqa: ANN001
    alias_table: dict[int, dict[str, str]],
) -> str | None:
    """Best-effort lookup for an attribute-target REBIND (T-0659,
    `_record_py_alias`'s attribute branch): synthesizes the
    `"{obj_name}.{attr_name}"` key (never a legal python identifier by
    itself, so it cannot collide with a real identifier alias key in the
    same `alias_table`) and looks it up via `_py_scope_alias_lookup` for a
    scope that recorded `obj.attr = <dangerous target>`."""
    return _py_scope_alias_lookup(f"{obj_name}.{attr_name}", site, alias_table)


#: sentinel python `subscript` KEY-NODE types `_py_literal_key_text`
#: extracts a stable, literal string form from (T-1626) -- a string
#: literal's own content text, or an integer literal's digit text. Any
#: other key-expression shape (a name, a call, a slice, an f-string with
#: interpolation) is NOT literal and gets no container-alias entry at all,
#: matching `_capability_scan._subscript_key_looks_literal`'s own
#: literal/non-literal split (OPAQUE001 fires fail-closed on the
#: non-literal case; this module only ever handles the literal one).
_PY_LITERAL_KEY_NODE_TYPES = frozenset({"string", "integer"})


def _py_literal_key_text(node) -> str | None:  # noqa: ANN001
    """The literal text a `dictionary` `pair`'s `key` (or a `list` element's
    own position) can be looked up by (T-1626): a `string` node's decoded
    content bytes, or an `integer` node's digit text verbatim. `None` for
    any other node shape -- computed keys are not tracked here (that is
    OPAQUE001's `_subscript_key_looks_literal`/structural-construct job,
    not this resolver's)."""
    if node.type == "string":
        return _string_content_bytes(node).decode("utf-8", errors="replace")
    if node.type == "integer":
        return node_text(node)
    return None


def _record_py_dict_container_alias(
    left,  # noqa: ANN001
    right,  # noqa: ANN001
    import_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    alias_table: dict[int, dict[str, str]],
    scope_aliases: dict[str, str],
) -> None:
    """Record one container-alias entry per STRING/INTEGER-literal-keyed
    `pair` of a `dictionary` literal RHS (T-1626, the ticket's own "indirect
    binding ... through a dict" worked example): `d = {"run": subprocess.
    run}` binds the synthesized key `d["run"]` (mirrors `_attr_rebind_
    lookup`'s `obj.attr` synthesis, but for subscript access) to
    `subprocess.run` in `left`'s enclosing scope, so `d["run"](cmd)`
    resolves via `_resolve_py_subscript`. A non-literal key (an
    identifier, an expression) gets no entry -- OPAQUE001's structural
    subscript-call construct already covers a non-literal-KEYED subscript
    call fail-closed; this only closes the literal-key gap that construct
    explicitly defers to "the ordinary resolver"."""
    name = node_text(left)
    for pair in right.children:
        if pair.type != "pair":
            continue
        key_node = pair.child_by_field_name("key")
        value_node = pair.child_by_field_name("value")
        if key_node is None or value_node is None:
            continue
        key_text = _py_literal_key_text(key_node)
        if key_text is None:
            continue
        # frob:invariant terminates reason="value_node is one pair's own 'value' field \
        # child, a proper descendant of right which is a proper descendant of the \
        # assignment node -- no recursion back into this function" measure="not \
        # applicable, not recursive"
        resolved = _resolve_py_expr(value_node, import_table, scope_cache, alias_table)
        if resolved is not None:
            scope_aliases.setdefault(f"{name}[{key_text}]", resolved)


def _record_py_list_container_alias(
    left,  # noqa: ANN001
    right,  # noqa: ANN001
    import_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    alias_table: dict[int, dict[str, str]],
    scope_aliases: dict[str, str],
) -> None:
    """Record one container-alias entry per positional element of a `list`
    literal RHS (T-1626, the ticket's "... or a list" sibling of
    `_record_py_dict_container_alias`): `lst = [subprocess.run]` binds the
    synthesized key `lst[0]` to `subprocess.run`, so `lst[0](cmd)` resolves
    via `_resolve_py_subscript`. Index is the element's POSITION among
    named children only (matches real python indexing -- the `[`/`]`/`,`
    tokens are unnamed and never counted)."""
    name = node_text(left)
    index = 0
    for element in right.children:
        if not element.is_named:
            continue
        # frob:invariant terminates reason="element is one of right's own children, a \
        # proper descendant of right which is a proper descendant of the assignment \
        # node -- no recursion back into this function" measure="not applicable, not \
        # recursive"
        resolved = _resolve_py_expr(element, import_table, scope_cache, alias_table)
        if resolved is not None:
            scope_aliases.setdefault(f"{name}[{index}]", resolved)
        index += 1


def _first_py_positional_arg(arguments_node):  # noqa: ANN001, ANN201
    """The first POSITIONAL argument node of a `call`'s `arguments` field
    (T-1626, for `functools.partial(dangerous, ...)` resolution): the first
    named child that is not a `keyword_argument`/`dictionary_splat`/
    `list_splat` -- `functools.partial(target, key=val)` and `functools.
    partial(target, *args)` both still resolve through `target`, since
    only the FIRST positional slot ever holds `partial`'s own wrapped
    callable. `None` for a call with no positional argument at all
    (`functools.partial()`, a runtime `TypeError` this resolver does not
    need to simulate)."""
    for child in arguments_node.children:
        if not child.is_named:
            continue
        if child.type in ("keyword_argument", "dictionary_splat", "list_splat"):
            continue
        return child
    return None


def _resolve_py_subscript(
    node,  # noqa: ANN001
    alias_table: dict[int, dict[str, str]] | None,
) -> str | None:
    """Resolve a `subscript` node (`d["run"]`/`lst[0]`) through the
    container-alias entries `_record_py_dict_container_alias`/`_record_py_
    list_container_alias` recorded (T-1626) -- `None` when the subscripted
    object is not a bare identifier, the key is not a literal
    (`_py_literal_key_text`), or no enclosing scope ever recorded a
    matching container-alias entry. Best-effort, by-NAME container
    identity only (same posture as `_attr_rebind_lookup` -- not a real
    points-to alias)."""
    if alias_table is None:
        return None
    value = node.child_by_field_name("value")
    key_node = node.child_by_field_name("subscript")
    if value is None or key_node is None or value.type != "identifier":
        return None
    key_text = _py_literal_key_text(key_node)
    if key_text is None:
        return None
    return _py_scope_alias_lookup(f"{node_text(value)}[{key_text}]", node, alias_table)


def _enclosing_py_scope(node):  # noqa: ANN001, ANN201
    """The nearest `_PY_SCOPE_TYPES` ancestor of `node` (its own function ->
    class -> ... -> module), or `None` if `node` is itself the module root
    with no scope ancestor -- used by `_build_py_alias_table` to find which
    scope an assignment's target name binds into."""
    cur = node.parent
    while cur is not None:
        if cur.type in _PY_SCOPE_TYPES:
            return cur
        cur = cur.parent
    return None


def _build_py_alias_table(
    module_node,
    import_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
) -> dict[int, dict[str, str]]:
    """Scope-local copy-propagation table (T-0337): `id(scope_node) ->
    {name: resolved_dangerous_target}` for every plain-identifier
    assignment target whose RHS resolves (via `_resolve_py_expr`, which
    itself consults this same table as it is built) to an import-table
    entry, a dangerous attribute chain, or another local name already known
    to alias one -- covering single rebinds (`xyz = run`), attribute
    rebinds (`e = os.system`), and transitive chains (`a = run; b = a`) in
    one pass, since the tree walk visits assignments in source (document)
    order so an earlier alias is already recorded by the time a later
    statement copies it. Cycle-safe by construction: only NEW bindings ever
    get looked up, and `_resolve_py_expr`'s shadow check means a name can
    only alias a resolution recorded in an enclosing/self scope that has
    already been walked, never itself circularly.

    Sound for may-analysis by design, not flow-sensitive: once a name is
    recorded as aliasing a dangerous target within a scope, a LATER benign
    reassignment of that same name in the same scope does not clear the
    entry -- `dict.setdefault` keeps the first (dangerous) resolution, so a
    call through the name anywhere in the scope is still flagged. This is
    the documented over-approximation choice (T-0337): a name that was EVER
    bound to a dangerous target in a scope may still be dangerous at any
    call site of that name in that scope.

    T-0659: also records a PARAMETER's own alias when a `default_parameter`/
    `typed_default_parameter`'s default value itself resolves to a
    dangerous target (`def f(cb=subprocess.run): cb(x)`) -- the parameter
    is already recorded in `_py_scope_bound_names` as ALWAYS shadowing
    (`_PY_ALWAYS_SHADOWS`), so without an alias_table entry keyed to the
    function's own scope id, `_resolve_py_identifier` would find the
    parameter shadow and then find NOTHING to resolve it through, silently
    dropping this evasion."""
    alias_table: dict[int, dict[str, str]] = {}

    def visit(node) -> None:  # noqa: ANN001
        if node.type == "assignment":
            _record_py_alias(node, import_table, scope_cache, alias_table)
        elif node.type == "function_definition":
            _record_py_default_param_aliases(
                node, import_table, scope_cache, alias_table
            )
        for child in node.children:
            visit(child)

    visit(module_node)
    return alias_table


def _record_py_default_param_aliases(
    func_node,
    import_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    alias_table: dict[int, dict[str, str]],
) -> None:  # noqa: ANN001
    """Record an alias entry for every `default_parameter`/
    `typed_default_parameter` of `func_node` whose default value resolves
    to a dangerous target (T-0659: default-arg forwarding, taxonomy row
    `def f(cb=subprocess.run): cb(x)`), keyed to `func_node`'s OWN scope id
    -- the same scope `_shadowing_scope` returns for a call site inside the
    function body, since the parameter shadows unconditionally
    (`_PY_ALWAYS_SHADOWS`)."""
    params = func_node.child_by_field_name("parameters")
    if params is None:
        return
    scope_aliases = alias_table.setdefault(func_node.id, {})
    for param in params.children:
        if param.type not in ("default_parameter", "typed_default_parameter"):
            continue
        name_node = param.child_by_field_name("name")
        value_node = param.child_by_field_name("value")
        if name_node is None or value_node is None:
            continue
        resolved = _resolve_py_expr(value_node, import_table, scope_cache, alias_table)
        if resolved is not None:
            scope_aliases.setdefault(node_text(name_node), resolved)


#: `assignment`-target pattern node types `_record_py_alias`'s destructuring
#: branch recurses through (T-0659): an un-parenthesized tuple target
#: (`pattern_list`, e.g. `f, g = ...`) or a parenthesized/bracketed one
#: (`tuple_pattern`/`list_pattern`) -- tree-sitter-python's grammar uses
#: `pattern_list` for the common bare-comma form; the parenthesized/
#: bracketed variants are included defensively (a plain `tuple`/`list` node
#: also occurs as a target in some grammar builds) so this does not depend
#: on which exact node type a given tree-sitter-python build emits.
_PY_DESTRUCTURE_TARGET_TYPES = ("pattern_list", "tuple_pattern", "list_pattern")

#: RHS node types `_record_py_alias`'s destructuring branch treats as a
#: literal, positionally-indexable sequence (T-0659) -- `tuple`/`list`
#: literals and the comma-separated `expression_list` a bare
#: `a, b = x, y` RHS parses as (no enclosing parens/brackets).
_PY_SEQUENCE_LITERAL_TYPES = ("tuple", "list", "expression_list")


def _record_py_destructure_alias(
    left_pattern,  # noqa: ANN001
    right_elements: list,  # noqa: ANN001 -- list[tree_sitter.Node]
    import_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    alias_table: dict[int, dict[str, str]],
    scope_aliases: dict[str, str],
) -> None:
    """Bind each plain-identifier element of `left_pattern` (a
    `pattern_list`-shaped tuple/list unpacking target) to its POSITIONALLY
    corresponding element of `right_elements` (T-0659: `f, g = subprocess.
    run, os.system; f(x)`), honoring a single `list_splat_pattern` (`*rest`)
    the same way real Python unpacking does: identifiers BEFORE the splat
    match from the front of `right_elements`, identifiers AFTER it match
    from the back (`f, *rest = [subprocess.run]` binds `f` to the FIRST
    element regardless of how many trailing elements `rest` swallows). The
    splat-bound name itself (`rest`) is never resolvable to a single
    symbol, so it gets no alias entry -- a documented, correct
    under-approximation (a container, not a callable). Nested patterns
    (`(a, b), c = ...`) are not recursed into -- a narrow, documented
    limitation rather than silently mis-binding one."""
    left_elements = [c for c in left_pattern.children if c.is_named]
    splat_index = next(
        (i for i, c in enumerate(left_elements) if c.type == "list_splat_pattern"),
        None,
    )
    if splat_index is None:
        pairs = list(zip(left_elements, right_elements, strict=False))
    else:
        before = list(
            zip(left_elements[:splat_index], right_elements[:splat_index], strict=False)
        )
        after_left = left_elements[splat_index + 1 :]
        after_right = right_elements[len(right_elements) - len(after_left) :]
        pairs = before + list(zip(after_left, after_right, strict=False))
    for left_el, right_el in pairs:
        if left_el.type != "identifier":
            continue
        resolved = _resolve_py_expr(right_el, import_table, scope_cache, alias_table)
        if resolved is not None:
            scope_aliases.setdefault(node_text(left_el), resolved)


# frob:ticket T-0361
def _record_py_alias(
    node,
    import_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    alias_table: dict[int, dict[str, str]],
) -> None:  # noqa: ANN001
    """If `node` (an `assignment`) binds a plain identifier to a resolvable
    RHS, record it in `alias_table` (first resolution wins, per the
    over-approximation policy documented on `_build_py_alias_table`); split
    out of that function's tree-walk visitor (T-0361).

    T-0659: also handles a tuple/list DESTRUCTURING target (delegates to
    `_record_py_destructure_alias` when both the left target and the right
    value are literal, positionally-indexable shapes) -- chained
    assignment's outer target (`a = b = target`) is handled separately, in
    `_resolve_py_expr`'s `assignment` branch, since it is a single-name
    bind through a nested `assignment` RHS rather than a destructuring
    shape."""
    left = node.child_by_field_name("left")
    right = node.child_by_field_name("right")
    if left is None or right is None:
        return
    scope = _enclosing_py_scope(node)
    if scope is None:
        return
    scope_aliases = alias_table.setdefault(scope.id, {})
    if left.type in _PY_DESTRUCTURE_TARGET_TYPES and right.type in (
        _PY_SEQUENCE_LITERAL_TYPES
    ):
        right_elements = [c for c in right.children if c.is_named]
        _record_py_destructure_alias(
            left, right_elements, import_table, scope_cache, alias_table, scope_aliases
        )
        return
    if left.type == "attribute":
        # T-0659: attribute-target rebind (`mod.run = subprocess.run`) --
        # best-effort, by-NAME object identity only (no real points-to);
        # see `_attr_rebind_lookup`'s docstring for the tradeoff.
        obj = left.child_by_field_name("object")
        attr = left.child_by_field_name("attribute")
        if obj is None or attr is None or obj.type != "identifier":
            return
        resolved = _resolve_py_expr(right, import_table, scope_cache, alias_table)
        if resolved is not None:
            scope_aliases.setdefault(f"{node_text(obj)}.{node_text(attr)}", resolved)
        return
    if left.type == "identifier" and right.type == "dictionary":
        # T-1626: `d = {"run": subprocess.run}` -- container alias, not a
        # single scalar binding; see _record_py_dict_container_alias.
        _record_py_dict_container_alias(
            left, right, import_table, scope_cache, alias_table, scope_aliases
        )
        return
    if left.type == "identifier" and right.type == "list":
        # T-1626: `lst = [subprocess.run]` sibling of the dict case above.
        _record_py_list_container_alias(
            left, right, import_table, scope_cache, alias_table, scope_aliases
        )
        return
    if left.type != "identifier":
        return
    resolved = _resolve_py_expr(right, import_table, scope_cache, alias_table)
    if resolved is None:
        return
    scope_aliases.setdefault(node_text(left), resolved)


def _collect_py_candidates(
    node,
    import_table: dict[str, str],
    scope_cache: dict[int, dict[str, int]],
    candidates: list[tuple[str, int, int]],
    alias_table: dict[int, dict[str, str]] | None = None,
) -> None:  # noqa: ANN001
    """Recursively walk `node`, appending `(resolved, start_byte, end_byte)`
    to `candidates` for every call/attribute/subscript site that resolves
    through `import_table` (T-0328), `alias_table`'s scope-local copy-
    propagation for a locally-shadowed name (T-0337), a resolved
    `functools.partial` first argument (T-1626), or a literal-keyed dict/
    list container alias (T-1626, `_resolve_py_subscript`)."""
    if node.type == "call":
        func = node.child_by_field_name("function")
        # T-1626: `subscript` added -- `d["run"](cmd)`'s callee is a
        # `subscript` node, not a bare identifier/attribute.
        if func is not None and func.type in ("identifier", "attribute", "subscript"):
            resolved = _resolve_py_expr(func, import_table, scope_cache, alias_table)
            if resolved is not None:
                candidates.append((resolved, node.start_byte, node.end_byte))
    elif node.type in ("attribute", "subscript"):
        resolved = _resolve_py_expr(node, import_table, scope_cache, alias_table)
        if resolved is not None:
            candidates.append((resolved, node.start_byte, node.end_byte))
    for child in node.children:
        _collect_py_candidates(
            child, import_table, scope_cache, candidates, alias_table
        )


def _python_resolved_candidates(path: Path) -> tuple[tuple[str, int, int], ...]:
    """Every `(resolved_dotted_target, start_byte, end_byte)` this file's
    call/attribute sites resolve to through its import binding table,
    enclosing-scope shadow check, and scope-local alias copy-propagation
    (T-0328, extended by T-0337 for local rebinding of a dangerous name).
    Empty for a non-Python file, an unparseable file, or one `frob.lang`
    has no grammar for -- degrades to the pre-existing lexical-only scan,
    never raises."""
    parsed = raw_tree(path)
    if parsed.is_err:
        return ()
    tree, _source, language_label = parsed.danger_ok
    if language_label != "python":
        return ()

    import_table = _py_import_table(tree.root_node)
    scope_cache: dict[int, dict[str, int]] = {}
    alias_table = _build_py_alias_table(tree.root_node, import_table, scope_cache)
    candidates: list[tuple[str, int, int]] = []
    _collect_py_candidates(
        tree.root_node, import_table, scope_cache, candidates, alias_table
    )
    return tuple(candidates)


def _python_binding_capabilities(
    path: Path,
    table: dict[str, tuple[str, ...]],
    comment_spans: tuple[ByteSpan, ...],
) -> set[str]:
    """Capability kinds observed via import/binding-aware resolution only
    (T-0328) -- the union of every registry needle that matches a resolved
    call/attribute target, for sites outside a comment span. Merged into
    `scan_file_capabilities`'s lexical result; adds recall (aliased/from-
    import evasions) without touching the existing raw-text path at all.

    T-0829: matches each candidate against one precompiled regex per
    capability instead of a Python-level `any(needle in resolved ...)` loop
    -- see `_compiled_capability_patterns`. `needle in resolved or needle in
    f"{resolved}("` collapses to a single `needle in f"{resolved}("` check:
    `resolved` is always a prefix of `f"{resolved}("`, so any needle found
    in `resolved` is necessarily also found in the longer string; searching
    only the longer string is behavior-identical and halves the substring
    work per needle. Also short-circuits the whole per-candidate loop once
    every capability with a nonempty needle set has already been found."""
    found: set[str] = set()
    patterns = _compiled_capability_patterns(table)
    if not patterns:
        return found
    for resolved, start, end in _python_resolved_candidates(path):
        if _fully_in_any_span(start, end, comment_spans):
            continue
        haystack = f"{resolved}("
        for capability, pattern in patterns:
            if capability in found:
                continue
            # frob:waive PERF008 reason="pattern is one of the pre-compiled re.Pattern \
            # objects from _compiled_capability_patterns(table), built once above this \
            # whole walk; .search(haystack) is a plain regex match with no I/O. \
            # PERF008 resolves the bare method name 'search' by name-only coincidence \
            # to an unrelated same-named function that genuinely reaches walk_pruned \
            # elsewhere in the repo -- a resolver ambiguity, not a real fs-walk on \
            # this call. Tracked as a resolver precision follow-up (T-1041's Done \
            # report)"
            if pattern.search(haystack):
                found.add(capability)
        if len(found) == len(patterns):
            break
    return found


def _python_binding_operations(
    path: Path, comment_spans: tuple[ByteSpan, ...]
) -> tuple[_DangerousOperation, ...]:
    """`DANGEROUS_OPERATIONS` python entries observed via import/binding-
    aware resolution only (T-0328) -- `_scan_file_operations`'s resolver-
    backed sibling to `_python_binding_capabilities`. An entry with no
    `needles` (bare-builtin `compile()`) is never resolver-matched here;
    it stays exclusively on the existing `_has_bare_compile_call` special
    check, since there is no import alias for a builtin to resolve."""
    candidates = _python_resolved_candidates(path)
    if not candidates:
        return ()
    matched: list[_DangerousOperation] = []
    for entry in DANGEROUS_OPERATIONS:
        if entry.language != "python" or not entry.needles:
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


# frob:ticket T-1752
# frob:tests \
# tests/test_vet.py::TestCapabilityScan.test_wrapper_capabilities_resolve_cross_file_vi\
# a_call_graph kind="unit"
def _build_wrapper_call_graph(root: Path, python_paths: Sequence[str]) -> CallGraph:
    """`frob.graph.callgraph.build_call_graph` over `python_paths` (repo-
    root-relative POSIX paths), built ONCE per scanned source tree and
    shared across every file `_python_wrapper_capabilities` resolves
    (T-1752): rebuilding it per-file would make a whole-package scan
    O(files^2), the exact cost concern this ticket's own design questions
    raised for a `frob vet` hot path that runs per-lockfile, potentially
    many packages. `mark_unresolved=False` (the default): a dangling call
    that only LOOKS private is silently dropped here, matching this
    module's existing fail-open-on-ambiguity posture (never a false
    accusation, only a narrower catch) -- this scanner degrades to "no
    wrapper found" the same way it already degrades on an unparseable or
    non-python file, never raising. Private (T-1752): only `_capability_
    scan.py`'s directory aggregation calls this today; a future external
    caller should go through that same aggregation path rather than
    building its own graph."""
    return build_call_graph(root, python_paths)


# frob:ticket T-1752
def _python_wrapper_capabilities(
    path: Path,
    root: Path,
    graph: CallGraph,
    table: dict[str, tuple[str, ...]],
) -> set[str]:
    """Cross-file wrapper attribution (T-1752, the follow-up T-1626's Done
    report deferred): if `path` calls a PRIVATE helper defined in ANOTHER
    file under `root`, and that helper -- or anything IT transitively
    calls, up to `frob.graph.callgraph.closure`'s bounded depth/node cap --
    itself resolves to a dangerous target, attribute that capability to
    `path` too. SYMBOLIC, never lexical: resolution walks real call-graph
    edges (`graph`, built once by `build_wrapper_call_graph` over the
    whole scanned tree), never matches a callee's NAME against a
    "looks-like-a-wrapper" heuristic -- the same standing principle every
    other resolver pass in this module (T-0328's import/binding table,
    T-1626's partial/dispatch-table resolution) already follows.

    Bounded by the callgraph's own private-callee-only resolution rule
    (T-0841): a PUBLIC wrapper is not followed -- a call graph edge is
    only ever recorded for a private/module-local callee, so this closes
    the SAME class of wrapper T-0328's own binding resolver already
    reaches within one file, just extended across file boundaries. A
    public forwarding function (`def run_thing(cmd): return _do(cmd)`
    where `_do` lives in another file and `run_thing` is itself called
    from a third file) is a disclosed remaining gap, not a false
    accusation -- consistent with this codebase's fail-open-on-ambiguity
    posture elsewhere (e.g. `build_call_graph`'s own `mark_unresolved`
    docstring). Same-file callees are skipped (`_python_binding_
    capabilities`'s ordinary intra-file resolution already covers them);
    only genuinely CROSS-FILE closure members contribute here."""
    try:
        rel_path = path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return set()
    caller_prefix = f"{rel_path}::"
    starts = [caller for caller in graph.calls if caller.startswith(caller_prefix)]
    found: set[str] = set()
    seen_files: set[str] = set()
    for start in starts:
        for callee in closure(graph, start):
            callee_file = callee.split("::", 1)[0]
            if callee_file == rel_path or callee_file in seen_files:
                continue
            seen_files.add(callee_file)
            callee_path = root / callee_file
            if not callee_path.is_file():
                continue
            callee_comment_spans = _non_executable_byte_spans(callee_path)
            found |= _python_binding_capabilities(
                callee_path, table, callee_comment_spans
            )
    return found
