"""Python architectural checks: long-function, god-class, high-coupling,
deep-nesting, and the cross-file abstraction-opportunity signature grouping
(docs/modules/arch.md's Python rules).

Every walker is driven off the one shared `_iter_py_functions` generator so
the recursion (into class bodies and nested functions) lives in exactly one
place instead of a bespoke nested closure per check.
"""

from __future__ import annotations

import difflib
import re
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from typing import cast

from tree_sitter import Node, Tree

from frob.arch._models import ArchSuggestion
from frob.dup._legacy_py import _collect_locals_py, _serialize_py_body
from frob.lang import child_by_field as _child
from frob.lang import node_text as _node_text
from frob.logging import get_logger

_log = get_logger(__name__)

_NESTING_TYPES = frozenset(
    {
        "if_statement",
        "for_statement",
        "while_statement",
        "try_statement",
        "with_statement",
    }
)

# T-0289: the long-function rule must be complexity-aware, not just line-count
# aware -- a long-but-FLAT function (linear setup+asserts, a big match/case,
# a literal dispatch table) is not the smell the rule targets; only
# long-AND-complex fires. `_BRANCH_NODE_TYPES` is a cheap McCabe-style
# decision-point proxy computed off the existing tree-sitter parse (no new
# dependency): `if_statement` (python's grammar folds an entire if/elif/else
# chain into ONE `if_statement` node with `elif_clause` children, so a long
# elif dispatch chain scores the same as a single `if`, deliberately -- see
# below), `for_statement`/`while_statement` (loops), `except_clause`
# (exception branches), `boolean_operator` (`and`/`or` short-circuit
# branches), and `conditional_expression` (the ternary `a if b else c`).
# `match_statement`/`case_clause` are deliberately EXCLUDED: a match/case is
# the canonical flat-dispatch shape this rule must NOT punish, and (unlike
# python's if/elif folding) each `case_clause` is tree-sitter's own separate
# node, so counting them would make the exact "big match/case" case the
# ticket calls out score as maximally complex -- the opposite of intent.
_BRANCH_NODE_TYPES = frozenset(
    {
        "if_statement",
        "for_statement",
        "while_statement",
        "except_clause",
        "boolean_operator",
        "conditional_expression",
    }
)

#: Nesting depth (`_py_max_nesting`) at or above which a long function counts
#: as structurally complex enough to fire the long-function rule (T-0289).
#: Not a `frob.toml` knob -- see the ticket's design note on why per-function
#: complexity escapes stay at-the-code (`frob:waive ARCH001`), not global.
_LONG_FUNCTION_NESTING_THRESHOLD = 3

#: Cyclomatic-proxy count (`_py_cyclomatic`) at or above which a long
#: function counts as structurally complex enough to fire (T-0289). Chosen
#: empirically: a flat function with a handful of top-level guard clauses or
#: a linear assert block sits well under this; a function with real nested
#: decision logic clears it.
_LONG_FUNCTION_CYCLOMATIC_THRESHOLD = 8


def _iter_py_functions(
    node: Node, class_prefix: str = ""
) -> Iterator[tuple[Node, str, str]]:
    """Yield `(function_node, class_prefix, func_name)` for every function
    definition under `node`, recursing into class bodies (prefixing with the
    class name) and nested function bodies (prefix unchanged)."""
    for c in node.children:
        if c.type == "class_definition":
            name_node = _child(c, "name")
            cname = _node_text(name_node) if name_node else "?"
            body = _child(c, "body")
            if body:
                yield from _iter_py_functions(body, cname + ".")
        elif c.type == "function_definition":
            name_node = _child(c, "name")
            fname = _node_text(name_node) if name_node else "?"
            yield c, class_prefix, fname
            body = _child(c, "body")
            if body:
                yield from _iter_py_functions(body, class_prefix)


def _py_function_line_count(func_node: Node) -> int:
    """Line span of `func_node`'s body block (0 when it has no body)."""
    body = _child(func_node, "body")
    if body is None:
        return 0
    return body.end_point[0] - body.start_point[0] + 1


def _py_cyclomatic(node: Node) -> int:
    """Cheap cyclomatic-complexity proxy: count of `_BRANCH_NODE_TYPES` nodes
    in `node`'s subtree (T-0289). Deliberately excludes match/case -- see
    `_BRANCH_NODE_TYPES`'s module-level comment for why."""
    count = 1 if node.type in _BRANCH_NODE_TYPES else 0
    for c in node.children:
        count += _py_cyclomatic(c)
    return count


def _py_is_complex(body: Node) -> bool:
    """Whether a function body is structurally complex enough for the
    long-function rule to fire (T-0289): deep nesting OR a high cyclomatic
    proxy. A long-but-FLAT function (linear setup+asserts, a big match/case,
    a literal dispatch table) fails both and must not be flagged."""
    return (
        _py_max_nesting(body) >= _LONG_FUNCTION_NESTING_THRESHOLD
        or _py_cyclomatic(body) >= _LONG_FUNCTION_CYCLOMATIC_THRESHOLD
    )


def _check_long_functions(
    tree: object,
    rel: str,
    max_function_lines: int,
    out: list[ArchSuggestion],
) -> None:
    """Flag python functions that are BOTH longer than `max_function_lines`
    AND structurally complex (`_py_is_complex`, T-0289) -- a long-but-flat
    function no longer fires. Each finding carries a `symref`/`metric` so
    `frob.gates`' ARCH001 job can match a `frob:waive ARCH001` directive to
    the exact function and honor an optional `ceiling=` re-fire threshold."""
    t: Tree = cast("Tree", tree)
    for func, prefix, fname in _iter_py_functions(t.root_node):
        n_lines = _py_function_line_count(func)
        if n_lines <= max_function_lines:
            continue
        body = _child(func, "body")
        if body is not None and not _py_is_complex(body):
            continue
        out.append(
            ArchSuggestion(
                file=rel,
                line=func.start_point[0] + 1,
                category="long-function",
                severity="warning",
                message=(
                    f"function `{prefix}{fname}` has"
                    f" {n_lines} lines (threshold: {max_function_lines})"
                ),
                symref=f"{rel}::{prefix}{fname}",
                metric=n_lines,
            )
        )


def _py_methods(body: Node) -> list[Node]:
    """The `function_definition` children directly inside a class body."""
    return [n for n in body.named_children if n.type == "function_definition"]


def _check_god_classes(
    tree: object,
    rel: str,
    max_class_methods: int,
    out: list[ArchSuggestion],
) -> None:
    """Flag every top-level python class with more than `max_class_methods`."""
    t: Tree = cast("Tree", tree)
    for c in t.root_node.children:
        if c.type != "class_definition":
            continue
        body = _child(c, "body")
        if body is None:
            continue
        n_methods = len(_py_methods(body))
        if n_methods <= max_class_methods:
            continue
        name_node = _child(c, "name")
        cname = _node_text(name_node) if name_node else "?"
        out.append(
            ArchSuggestion(
                file=rel,
                line=c.start_point[0] + 1,
                category="god-class",
                severity="warning",
                message=f"class `{cname}` has {n_methods} methods"
                f" (threshold: {max_class_methods})",
            )
        )


def _check_high_coupling(
    path: Path,
    rel: str,
    root: Path,
    max_local_imports: int,
    out: list[ArchSuggestion],
) -> None:
    """Flag python files importing more than `max_local_imports` local modules."""
    from frob.lang import extract_imports, resolve_local_import

    specs_result = extract_imports(path)
    if specs_result.is_err:
        _log.debug("high-coupling: failed to parse %s: %s", rel, specs_result.err)
        return
    resolved = {
        resolve_local_import(spec, "python", file_dir=path.parent, root=root)
        for spec in specs_result.danger_ok
    }
    resolved.discard(None)
    n = len(resolved)
    if n > max_local_imports:
        out.append(
            ArchSuggestion(
                file=rel,
                category="high-coupling",
                severity="suggestion",
                message=f"file imports {n} local modules (threshold: {max_local_imports})",  # noqa: E501
            )
        )


def _py_max_nesting(func_body_node: Node) -> int:
    """Deepest control-flow nesting depth inside a function body block."""

    def depth(node: Node, current: int) -> int:
        best = current
        for c in node.children:
            nxt = current + 1 if c.type in _NESTING_TYPES else current
            best = max(best, depth(c, nxt))
        return best

    return depth(func_body_node, 0)


def _check_deep_nesting(
    tree: object,
    rel: str,
    max_nesting_depth: int,
    out: list[ArchSuggestion],
) -> None:
    """Flag python functions whose control-flow nesting exceeds the threshold."""
    t: Tree = cast("Tree", tree)
    for func, prefix, fname in _iter_py_functions(t.root_node):
        body = _child(func, "body")
        if body is None:
            continue
        depth = _py_max_nesting(body)
        if depth <= max_nesting_depth:
            continue
        out.append(
            ArchSuggestion(
                file=rel,
                line=func.start_point[0] + 1,
                category="deep-nesting",
                severity="suggestion",
                message=(
                    f"function `{prefix}{fname}` has"
                    f" nesting depth {depth}"
                    f" (threshold: {max_nesting_depth})"
                ),
            )
        )


def _annotation_text(node: Node) -> str:
    """The stripped source text of a type-annotation node."""
    return _node_text(node).strip()


def _py_param_types(func_node: Node) -> list[str]:
    """Annotated parameter type texts of `func_node` (unannotated skipped)."""
    params_node = _child(func_node, "parameters")
    if params_node is None:
        return []
    types: list[str] = []
    for p in params_node.named_children:
        if p.type in ("typed_parameter", "typed_default_parameter"):
            ann = _child(p, "type")
            if ann:
                types.append(_annotation_text(ann))
    return types


def _extract_signatures(
    tree: object,
    rel: str,
) -> list[tuple[str, str, tuple[str, ...], str, str]]:
    """`(rel, func_name, param_types, return_type, body_fingerprint)` for
    every python function carrying at least one annotated parameter or an
    annotated return type.

    T-0370: `body_fingerprint` is the alpha-renamed, literal-normalized
    token serialization of the function body (`frob.dup._legacy_py`'s
    `_collect_locals_py`/`_serialize_py_body`, the same normalizer the dup
    scanner uses) -- it lets `_check_abstraction_opportunities` tell a
    same-signature GROUP of near-duplicate bodies (a real extractable
    abstraction) apart from a same-signature group of unrelated bodies
    (a coincidental collision on a generic shape) without a bare shared
    signature being treated as evidence on its own."""
    t: Tree = cast("Tree", tree)
    results: list[tuple[str, str, tuple[str, ...], str, str]] = []
    for func, _prefix, fname in _iter_py_functions(t.root_node):
        param_types = _py_param_types(func)
        ret_node = _child(func, "return_type")
        ret = _annotation_text(ret_node) if ret_node else ""
        if param_types or ret:
            body_fp = _body_fingerprint(func)
            results.append((rel, fname, tuple(param_types), ret, body_fp))
    return results


def _body_fingerprint(func: Node) -> str:
    """Normalized token serialization of `func`'s body, or `""` if it has
    none (T-0370, reused for abstraction-opportunity body-similarity)."""
    body = _child(func, "body")
    if body is None:
        return ""
    locals_ = _collect_locals_py(func)
    return _serialize_py_body(body, locals_)


_DISPATCH_CONTAINER_TYPES = frozenset({"list", "set", "tuple"})


# frob:waive ARCH001 reason="detector internal owned by a separate ticket (T-0360 dispatch-family detection); a single recursive tree-walk over one grammar's dispatch-position cases, splitting the case list across functions would scatter one cohesive traversal without reducing its real complexity" ceiling="60"  # noqa: E501
def _collect_dispatch_refs(node: Node, out: set[str]) -> None:
    """Collect every identifier used in a DISPATCH-LIKE syntactic position
    under `node`, into `out` (T-0360, reviewer-required fix).

    Deliberately structural, not textual: a plain mention of a name (an
    import, a docstring, a bare `__all__` string) proves nothing about
    dispatch -- a re-export list or a test file that imports and asserts
    against three unrelated functions mentions each name too, and a purely
    textual "appears >=2 times" signal cannot tell those apart from a real
    command table. Only these tree-sitter shapes count as "this name is
    being dispatched from here":

    - the callee of a `call` (`name(...)`) -- an `elif`/`match` branch
      calling a handler, or a direct dispatch call;
    - a positional or keyword ARGUMENT of a `call` (`register(name)`,
      `table.append(name)`, `dispatch(cmd, handler=name)`) -- a
      registration call;
    - a value inside a `dictionary` literal's `pair` (`{"scan": name}`) --
      a command table;
    - an element of a `list`/`set`/`tuple` literal (`[name_a, name_b]`) --
      a dispatch table built as a sequence.

    A bare `from mod import name` or `name` sitting in an `__all__` list of
    STRING literals (not identifiers) matches none of these and is
    correctly not counted.
    """
    for c in node.children:
        if c.type == "call":
            func = _child(c, "function")
            if func is not None and func.type == "identifier":
                out.add(_node_text(func))
            args = _child(c, "arguments")
            if args is not None:
                for a in args.named_children:
                    if a.type == "identifier":
                        out.add(_node_text(a))
                    elif a.type == "keyword_argument":
                        val = _child(a, "value")
                        if val is not None and val.type == "identifier":
                            out.add(_node_text(val))
        elif c.type == "dictionary":
            for pair in c.named_children:
                if pair.type == "pair":
                    val = _child(pair, "value")
                    if val is not None and val.type == "identifier":
                        out.add(_node_text(val))
        elif c.type in _DISPATCH_CONTAINER_TYPES:
            for el in c.named_children:
                if el.type == "identifier":
                    out.add(_node_text(el))
        _collect_dispatch_refs(c, out)


def _collect_file_dispatch_refs(tree: object) -> set[str]:
    """Every identifier name referenced in a dispatch-like context
    (`_collect_dispatch_refs`) anywhere in a parsed python file's tree.

    Public so `frob.arch` (the caller building the cross-file corpus) can
    decide, per file, whether to include it -- callers exclude
    `__init__.py` re-export modules and test files (`is_test_file`) before
    this function ever sees them, so this function itself stays a pure
    structural extraction with no naming/path policy baked in."""
    t: Tree = cast("Tree", tree)
    refs: set[str] = set()
    _collect_dispatch_refs(t.root_node, refs)
    return refs


def _is_dispatch_family(
    members: list[tuple[str, str]],
    all_dispatch_refs: dict[str, set[str]],
) -> bool:
    """Whether a shared-signature `members` group (T-0360) is an intentional
    dispatch/validator family rather than an accidental duplication.

    A same-signature group is NOT a missing abstraction when its members are
    each reachable from a common site -- a command table, a validator
    runner, an `elif` dispatch chain -- because the shared signature IS the
    contract that lets that site call them uniformly. `all_dispatch_refs`
    (built by `frob.arch` from `_collect_file_dispatch_refs`, already
    excluding `__init__.py` and test files) maps each eligible file to the
    set of names it references in a dispatch-like structural position
    (call callee, call argument, dict value, list/set/tuple element) --
    NOT every textual mention, so a re-export list or a test's assertion
    calls cannot masquerade as a dispatch site (reviewer-flagged false
    suppression, fixed here). Two members are "linked" if some single
    eligible file's ref-set contains both their names. A large group can
    legitimately be served by more than one such site (e.g. two separate
    command tables that each dispatch a handful of same-signature
    handlers) -- so the group is treated as an intentional family when
    every member is linked to at least one sibling, i.e. no member sits
    completely outside any dispatch site. A group with a member that is
    never linked to any other member has no such site for that member and
    still flags as a real opportunity.
    """
    names = [fname for _, fname in members]
    if len(names) < 2:
        return False
    linked: set[int] = set()
    for refs in all_dispatch_refs.values():
        referenced = [i for i, name in enumerate(names) if name in refs]
        if len(referenced) >= 2:
            linked.update(referenced)
    return len(linked) == len(names)


# T-0370: types so ubiquitous that sharing one carries no abstraction
# signal on its own -- `(str) -> str`, `(AppConfig) -> None`, and similar
# shapes collide across dozens of semantically-unrelated functions purely
# because the type system only has so many primitives to offer, OR because
# one project-wide "contract" type is threaded through every subcommand
# entrypoint on purpose (`AppConfig`, the App/AppConfig pattern's uniform
# `run(config) -> None` shape every runner module implements). A signature
# built ENTIRELY from names in this set is "generic"; a signature with at
# least one name outside it (a real domain type like `TicketStore` or
# `CloneReport`, which does NOT appear here) is specific.
_GENERIC_TYPE_NAMES = frozenset(
    {
        "str",
        "int",
        "bool",
        "float",
        "bytes",
        "None",
        "Path",
        "object",
        "Any",
        "list",
        "dict",
        "set",
        "tuple",
        "frozenset",
        "Sequence",
        "Iterable",
        "Iterator",
        "Mapping",
        "Optional",
        "Union",
        "Callable",
        "self",
        "cls",
        # App/AppConfig pattern (~/.claude/refs/python-app.md): every
        # runner module's `run(config: AppConfig) -> None` entrypoint
        # shares this signature by DESIGN, not by coincidence -- it is
        # the uniform CLI-dispatch contract, not an extractable family.
        "AppConfig",
    }
)

_TYPE_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _type_is_generic(annotation: str) -> bool:
    """Whether every identifier token in `annotation` is one of the
    ubiquitous names in `_GENERIC_TYPE_NAMES` (T-0370) -- e.g. `str`,
    `list[str]`, `Path | None` are generic; `AppConfig`, `CloneReport` are
    not. An annotation with no identifier tokens (empty) counts as
    generic: it carries no specificity signal."""
    tokens = _TYPE_TOKEN_RE.findall(annotation)
    if not tokens:
        return True
    return all(tok in _GENERIC_TYPE_NAMES for tok in tokens)


def _signature_is_specific(ptypes: tuple[str, ...], ret: str) -> bool:
    """Whether a shared signature has at least one non-generic type
    (T-0370) -- the SIGNATURE-SPECIFICITY discriminator. A group sharing
    only ubiquitous types (`(str) -> str`, `(AppConfig) -> None`) needs
    body-similarity evidence instead; one carrying a domain type
    (`(TicketStore, str) -> Result[...]`) is specific enough on its own."""
    return any(not _type_is_generic(t) for t in (*ptypes, ret) if t)


# T-0370: two normalized bodies are near-duplicate when their token
# sequences (locals alpha-renamed, literals collapsed to `_S_`/`_N_` by
# `_serialize_py_body`) match at or above this ratio -- high enough that a
# body reshaped only by renamed variables still matches, low enough to
# tolerate a stray extra statement between otherwise-identical bodies.
_BODY_SIMILARITY_THRESHOLD = 0.9

# T-0370: bodies shorter than this many normalized tokens are excluded from
# body-similarity clustering entirely. `difflib.SequenceMatcher.ratio()` on
# very short strings is dominated by shared PUNCTUATION/keyword tokens
# (`_S_ return _v0 . x`-shaped one-liners) rather than shared LOGIC, so tiny
# unrelated one-line predicates/getters collide at >=0.9 by coincidence --
# exactly the false-positive noise the ticket calls out. A real extractable
# family has an actual body to share, not just a `return` statement.
_BODY_MIN_TOKENS = 8


def _near_duplicate_cluster(
    members: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    """The subset of `members` (`(rel, fname, body_fingerprint)`) that has
    at least one near-duplicate partner within the group (T-0370) -- the
    BODY-SIMILARITY discriminator, the strongest signal that a same-
    signature group is a genuine extractable abstraction rather than a
    coincidental collision. Bodies under `_BODY_MIN_TOKENS` tokens (empty
    stubs, trivial one-liners) never participate -- too short for
    similarity to mean anything. Returns the near-duplicate members only,
    NOT the whole input group: a group of 30 unrelated functions with one
    genuinely duplicated pair should be reported as that pair, not
    misrepresented as 30 functions all sharing logic."""
    eligible = [m for m in members if len(m[2].split()) >= _BODY_MIN_TOKENS]
    cluster_idx: set[int] = set()
    for i in range(len(eligible)):
        for j in range(i + 1, len(eligible)):
            ratio = difflib.SequenceMatcher(
                None, eligible[i][2], eligible[j][2]
            ).ratio()
            if ratio >= _BODY_SIMILARITY_THRESHOLD:
                cluster_idx.add(i)
                cluster_idx.add(j)
    return [eligible[i] for i in sorted(cluster_idx)]


def _emit_abstraction_suggestion(
    ptypes: tuple[str, ...],
    ret: str,
    flagged: list[tuple[str, str, str]],
    out: list[ArchSuggestion],
) -> None:
    """Append one `abstraction-opportunity` `ArchSuggestion` for `flagged`
    (T-0370, factored out of `_check_abstraction_opportunities` to keep
    the per-group decision logic and the message formatting each
    independently short)."""
    params_str = ", ".join(ptypes)
    sig_str = f"({params_str}) -> {ret}" if ret else f"({params_str})"
    fn_names = ", ".join(fname for _, fname, _ in flagged)
    out.append(
        ArchSuggestion(
            file=flagged[0][0],
            category="abstraction-opportunity",
            severity="suggestion",
            message=f"{len(flagged)} functions share signature `{sig_str}`: {fn_names}",
            detail="Consider a shared protocol or base class",
        )
    )


def _abstraction_group_evidence(
    ptypes: tuple[str, ...],
    ret: str,
    members_with_body: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    """The subset of `members_with_body` that constitutes genuine
    abstraction-opportunity evidence for this `(ptypes, ret)` group
    (T-0370): the whole group when the signature is SPECIFIC
    (`_signature_is_specific`), or the near-duplicate-body subset
    (`_near_duplicate_cluster`) when it is generic. Empty means no
    evidence -- the caller should not flag."""
    if _signature_is_specific(ptypes, ret):
        return members_with_body
    return _near_duplicate_cluster(members_with_body)


def _check_abstraction_opportunities(
    all_sigs: list[tuple[str, str, tuple[str, ...], str, str]],
    all_dispatch_refs: dict[str, set[str]],
    out: list[ArchSuggestion],
) -> None:
    """Flag signatures shared by 3+ functions with no common dispatch site
    AND genuine evidence of an extractable abstraction (T-0370): either the
    shared signature is SPECIFIC (`_signature_is_specific`, at least one
    non-generic type -- the whole group is reported, the signature itself
    is the evidence) or a subset of the members has near-duplicate BODIES
    (`_near_duplicate_cluster`, reusing the dup-scanner's normalizer --
    only that near-duplicate subset is reported, since the rest of a
    generic-signature group proved nothing). A group sharing only an
    over-generic signature (`(str) -> str`, `(AppConfig) -> None`) with no
    such duplicated subset is NOT flagged at all -- you cannot factor N
    unrelated functions into one helper just because they happen to take
    the same primitive types. Groups whose members are all reachable from
    one common caller/registry (`_is_dispatch_family`, T-0360) are
    intentional dispatch families and are still skipped first."""
    groups: dict[tuple[tuple[str, ...], str], list[tuple[str, str, str]]] = defaultdict(
        list
    )
    for rel, fname, ptypes, ret, body_fp in all_sigs:
        if not ptypes:
            continue
        groups[(ptypes, ret)].append((rel, fname, body_fp))

    for (ptypes, ret), members_with_body in groups.items():
        if len(members_with_body) < 3:
            continue
        members = [(rel, fname) for rel, fname, _ in members_with_body]
        if _is_dispatch_family(members, all_dispatch_refs):
            continue
        flagged = _abstraction_group_evidence(ptypes, ret, members_with_body)
        if len(flagged) < 2:
            continue
        _emit_abstraction_suggestion(ptypes, ret, flagged, out)
