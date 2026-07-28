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
from frob.arch._normalized import (
    NormalizedBranch,
    NormalizedCall,
    NormalizedCallArg,
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
    NormalizedSubscript,
)
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

#: Matches a `frob:callee-raises` declaration comment (T-0689) on a call site's own
#: source line -- `# frob:callee-raises ValueError, OSError` or the empty-set form
#: `# frob:callee-raises` (declares "raises nothing", the valid errno-convention
#: shape T-0690's sibling ticket calls out). Deliberately matched against
#: the single physical line a `NormalizedCall.line` already names (same-line
#: only, no lookbehind/lookahead scan) -- the same line-adjacency-proxy
#: style `_mayraise.py`'s `_nearest_preceding_catch` already uses elsewhere
#: in this feature, kept simple rather than parsing a leading-comment block.
_FROB_RAISES_RE = re.compile(r"#\s*frob:callee-raises\b[ \t]*(.*)$")

#: T-1066: matches an `# arch-exempt: deep-nesting reason="..."` directive on
#: a leading-comment line directly above a function's `def`/`async def`
#: (same physical placement `frob:waive ARCH001` already uses above a
#: function, e.g. `_tarjan_sccs`'s existing waiver in
#: `frob.graph.summary`). Deliberately spelled WITHOUT a `frob:` prefix --
#: `frob.graph.dsl._LINE_RE` treats any `frob:<token>` comment as an
#: attempted directive and DSL001s it if the verb is not registered there,
#: and registering a new verb means editing `frob.graph.dsl` (outside this
#: ticket's `src/frob/arch/**`-scoped territory); a distinct, non-`frob:`
#: marker sidesteps that collision entirely rather than smuggling a new
#: verb through a module this ticket must not touch. deep-nesting is also
#: DELIBERATELY excluded from the generic `frob:waive` graph-edge channel
#: (`frob.gates._unwaivable_channel_rules`'s docstring: `ArchSuggestion`s
#: for this category never become `Violation`s, so no waiver edge could
#: ever bind to one) -- this marker is a SEPARATE, detector-owned
#: exemption, not a workaround of that boundary. It exists for exactly the
#: case ARCH001's own reasoned-waiver path already covers for
#: long-function: a genuinely irreducible algorithm (textbook iterative
#: Tarjan's SCC, explicit work-stack unwind) where a forced split would add
#: indirection without separating a real sub-concern, not a blanket escape
#: hatch. `reason=` is REQUIRED (mirrors `frob:waive`'s WAIVE001
#: discipline) -- an empty or missing reason does not match and the
#: finding still fires.
_ARCH_EXEMPT_DEEP_NESTING_RE = re.compile(
    r'#\s*arch-exempt:\s*deep-nesting\s+reason="([^"]+)"'
)


# frob:ticket T-1066
def _deep_nesting_exempt_reason(
    source_lines: tuple[str, ...], def_line: int
) -> str | None:
    """The reasoned exemption text from an `# arch-exempt: deep-nesting
    reason="..."` comment on one of the (possibly several) leading-comment
    lines directly above `def_line` (1-indexed, `NormalizedFunction.line`),
    or `None` when no such directive is present. Scans upward from
    `def_line - 1` while each line is blank or an unindented `#` comment --
    the same leading-comment-block shape a decorator/`frob:ticket`/
    `frob:waive` stack already occupies above a function -- and stops at
    the first non-comment, non-blank line, so a directive left over an
    unrelated earlier function can never leak onto this one."""
    i = def_line - 2  # 0-indexed line directly above def_line
    while i >= 0:
        stripped = source_lines[i].strip()
        if not stripped:
            i -= 1
            continue
        if not stripped.startswith("#"):
            break
        m = _ARCH_EXEMPT_DEEP_NESTING_RE.search(stripped)
        if m is not None:
            reason = m.group(1).strip()
            if reason:
                return reason
        i -= 1
    return None


# frob:ticket T-0689
def _frob_raises_declaration(
    source_lines: tuple[str, ...], line: int
) -> frozenset[str] | None:
    """The declared exception-name set (T-0689) from a `# frob:callee-raises ...`
    comment on `source_lines[line - 1]` (1-indexed, matching
    `NormalizedCall.line`), or `None` when that line carries no such
    comment. `# frob:callee-raises` with nothing after it declares the EMPTY set
    (a valid, distinct declaration -- see `NormalizedCall.declared_raises`'s
    docstring), not "no declaration"."""
    if line < 1 or line > len(source_lines):
        return None
    m = _FROB_RAISES_RE.search(source_lines[line - 1])
    if m is None:
        return None
    rest = m.group(1).strip()
    if not rest:
        return frozenset()
    return frozenset(name.strip() for name in rest.split(",") if name.strip())


# frob:invariant terminates reason="recurses only into a body node one tree-sitter \
# edge below the current node; a lexical prover cannot see that the child accessor is \
# structurally smaller without dataflow" measure="tree-sitter AST depth under node, \
# finite per parse"
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


def _check_long_functions(
    tree: object,
    rel: str,
    max_function_lines: int,
    out: list[ArchSuggestion],
) -> None:
    """Flag python functions that are BOTH longer than `max_function_lines`
    AND structurally complex (`_normalized_is_complex`, T-0289; re-expressed
    on `NormalizedModule` at T-0610) -- a long-but-flat function no longer
    fires. Each finding carries a `symref`/`metric` so `frob.gates`' ARCH001
    job can match a `frob:waive ARCH001` directive to the exact function and
    honor an optional `ceiling=` re-fire threshold."""
    module = _py_build_module(tree, rel)
    for func, prefix in _iter_normalized_functions(module):
        n_lines = func.body_line_count
        if n_lines <= max_function_lines:
            continue
        if not _normalized_is_complex(func):
            continue
        out.append(
            ArchSuggestion(
                file=rel,
                line=func.line,
                category="long-function",
                severity="warning",
                message=(
                    f"function `{prefix}{func.name}` has"
                    f" {n_lines} lines (threshold: {max_function_lines})"
                ),
                symref=f"{rel}::{prefix}{func.name}",
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
    """Flag every top-level python class with more than `max_class_methods`
    -- reads `NormalizedModule.classes` (T-0610) instead of walking `tree`
    directly."""
    module = _py_build_module(tree, rel)
    for c in module.classes:
        n_methods = len(c.methods)
        if n_methods <= max_class_methods:
            continue
        out.append(
            ArchSuggestion(
                file=rel,
                line=c.line,
                category="god-class",
                severity="warning",
                message=f"class `{c.name}` has {n_methods} methods"
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


# ---------------------------------------------------------------------------
# T-0610: python `LanguageAdapter` -- maps this module's tree-sitter walks
# onto the T-0609 `NormalizedModule` shape, and the checks migrated to
# consume it (long-function, god-class, deep-nesting).
#
# T-0632: `NormalizedCall` now also carries per-argument position/keyword +
# bare-identifier detail (`NormalizedCall.args`, `_py_call_args`), and
# `_extract_signatures` is migrated onto `NormalizedModule` for its
# name/param-types/return-type fields (see its own docstring for the one
# piece -- body-fingerprinting -- that stays raw-AST-based by reasoned
# decision, not oversight).
#
# `_collect_file_dispatch_refs`/`_collect_dispatch_refs` (abstraction-
# opportunity's cross-file dispatch-family corpus) stay on the raw tree-
# sitter walk, by the same kind of reasoned decision: dispatch detection
# needs every dict/list/set-literal element and every call argument
# ANYWHERE in the file -- module-level statements and class-body
# expressions included, not just inside a function/method body.
# `NormalizedModule` deliberately only models classes/functions/imports
# (T-0609's scope), with no top-level-statement or literal-expression
# projection at all; `_py_collect_body_events` (which DOES walk function
# bodies) also does not walk into container literals that are not call
# arguments (a bare `TABLE = {"a": handler}` module constant, for
# instance) because no current check needs that generality outside
# dispatch detection. Re-deriving a NormalizedModule shape general enough
# to carry arbitrary whole-file container literals would mean modeling
# nearly the entire expression grammar on the shared model for this one
# consumer -- not migrating a raw walk, but rebuilding it as normalized
# events one-for-one. `_collect_dispatch_refs` remains the single, already
# cohesive recursive walk it was before (T-0360); `NormalizedCall.args`
# added here is available for any FUTURE detector that only needs
# call-argument identifiers inside a function body, without forcing this
# one to give up its whole-file reach to use it.
# ---------------------------------------------------------------------------

_LOOP_KINDS = {"for_statement": "for", "while_statement": "while"}
_BRANCH_EVENT_TYPES = frozenset(
    {"if_statement", "boolean_operator", "conditional_expression"}
)


def _py_branch_condition_text(node: Node) -> str:
    """Source text of a branch node's own test condition: an `if_statement`
    reads its `condition` field; a `boolean_operator`/`conditional_expression`
    has no separate condition field, so its own text stands for it."""
    if node.type == "if_statement":
        cond = _child(node, "condition")
        return _node_text(cond) if cond is not None else _node_text(node)
    return _node_text(node)


def _py_call_callee_text(node: Node) -> str:
    """The callee text of a `call` node: a bare identifier (`f(...)`) or the
    dotted `obj.method` form (`obj.method(...)`)."""
    func = _child(node, "function")
    return _node_text(func) if func is not None else _node_text(node)


# frob:ticket T-0632
def _py_call_args(node: Node) -> list[NormalizedCallArg]:
    """`NormalizedCallArg`s for a `call` node's `arguments` list (T-0632),
    in source order: each positional argument gets its 0-based `index`,
    each keyword argument gets its `keyword` name, and a bare-identifier
    argument (either shape) also gets its `ident` text -- the detail
    `_collect_dispatch_refs`' own arg-walk needs, now available on the
    model instead of only via a raw-tree re-walk."""
    args_node = _child(node, "arguments")
    if args_node is None:
        return []
    out: list[NormalizedCallArg] = []
    position = 0
    for a in args_node.named_children:
        if a.type == "keyword_argument":
            val = _child(a, "value")
            name_node = _child(a, "name")
            keyword = _node_text(name_node) if name_node is not None else "?"
            out.append(
                NormalizedCallArg(
                    keyword=keyword,
                    ident=_node_text(val)
                    if val is not None and val.type == "identifier"
                    else None,
                )
            )
            continue
        out.append(
            NormalizedCallArg(
                index=position,
                ident=_node_text(a) if a.type == "identifier" else None,
            )
        )
        position += 1
    return out


def _py_is_self_attribute(node: Node) -> bool:
    """Whether an `attribute` node is a genuine `self.<field>` READ or
    WRITE (T-0977, audit finding 4 / ARCH101 false-positive root cause) --
    both of: (1) its OBJECT half is the bare identifier `self`, and (2) it
    is NOT itself the callee position of a `call` (`self.method(...)`,
    which is a method invocation, not a field access -- the callee already
    lands in `calls` via `NormalizedCall`, separately). The field-access
    extractor previously recorded EVERY `X.attr` expression as a
    `field_access` regardless of either check -- `node.ops` (a local AST-
    node parameter, not `self`), `self.generic_visit(...)` and
    `self._hit(...)` (method calls, not field reads/writes), and any other
    object's attribute all counted. That silently fed
    `frob.arch._srp.check_lcom4` (ARCH101) a field-usage graph padded with
    unrelated identifiers shared only by call-graph coincidence (e.g. two
    unrelated methods both calling `self._hit` looked like they shared a
    field named `_hit`), producing exactly the kind of gameable,
    structure-blind false signal this repo's arch audit already flagged
    for other checks (docs/audits/gates-quality.md finding 4). Restricting
    to genuine `self.<name>` reads/writes (the only shape
    `NormalizedFieldAccess`'s own docstring -- "`self.x`, `this->x`,
    `obj.attr`" -- and every LCOM4 consumer already assumes) is the fix."""
    obj = _child(node, "object")
    if obj is None or obj.type != "identifier" or _node_text(obj) != "self":
        return False
    parent = node.parent
    if parent is not None and parent.type == "call":
        func = _child(parent, "function")
        if func is not None and func.id == node.id:
            return False
    return True


def _py_is_field_write(node: Node) -> bool:
    """Whether an `attribute` node (`self.x`) is the assignment-target of an
    `assignment` (a write) rather than being read."""
    parent = node.parent
    if parent is None or parent.type != "assignment":
        return False
    target = _child(parent, "left")
    return target is not None and target.id == node.id


def _py_raise_exception_type(node: Node) -> str | None:
    """The exception type name of a `raise` statement where staticaly
    determinable (`raise ValueError(...)` -> `"ValueError"`), else `None`
    (a bare `raise` re-raise, or a raised expression too dynamic to name)."""
    for c in node.named_children:
        if c.type == "call":
            func = _child(c, "function")
            if func is not None and func.type == "identifier":
                return _node_text(func)
        elif c.type == "identifier":
            return _node_text(c)
    return None


def _py_except_exception_type(node: Node) -> str | None:
    """The caught exception type name of an `except_clause`, or `None` for a
    bare `except:` catch-all or a multi-type `except (A, B):` tuple's first
    member being taken as the representative type."""
    for c in node.named_children:
        if c.type in ("identifier", "attribute"):
            return _node_text(c)
        if c.type == "tuple":
            first = next(iter(c.named_children), None)
            if first is not None:
                return _node_text(first)
    return None


# frob:ticket T-0632
# frob:ticket T-0686
# frob:ticket T-0689
# frob:waive ARCH001 reason="a single flat per-node-type dispatch table over python's grammar, the same walk shape _kt_collect_body_events/_rust_collect_body_events/_ts_collect_body_events already carry this exact waiver for (T-0609) so the four language adapters stay structurally comparable; splitting by node-type would fragment one coherent walk into disconnected pieces without reducing the branching itself"  # noqa: E501
def _py_collect_body_events(
    node: Node,
    branches: list[NormalizedBranch],
    loops: list[NormalizedLoop],
    calls: list[NormalizedCall],
    field_accesses: list[NormalizedFieldAccess],
    returns: list[NormalizedReturn],
    raises: list[NormalizedRaise],
    catches: list[NormalizedCatch],
    subscripts: list[NormalizedSubscript],
    source_lines: tuple[str, ...] = (),
) -> None:
    """Flatten every structural event (T-0609 shape) inside `node`'s
    subtree, stopping at a nested `function_definition`/`class_definition`
    boundary -- those become their own `NormalizedFunction`/`NormalizedClass`
    (`_py_build_function`/`_py_build_class`), not events folded into the
    parent. `subscripts` (T-0686) collects `d[k]`-shaped expressions the
    may-raise resolver's builtin-raiser table keys off. `source_lines`
    (T-0689, optional -- empty when a caller has no raw source to offer)
    lets each `call` site pick up its own `# frob:callee-raises` declaration
    (`_frob_raises_declaration`) onto `NormalizedCall.declared_raises`."""
    for c in node.children:
        if c.type in ("function_definition", "class_definition"):
            continue
        if c.type in _BRANCH_EVENT_TYPES:
            branches.append(
                NormalizedBranch(
                    line=c.start_point[0] + 1,
                    condition_text=_py_branch_condition_text(c),
                )
            )
        if c.type in _LOOP_KINDS:
            loops.append(
                NormalizedLoop(line=c.start_point[0] + 1, kind=_LOOP_KINDS[c.type])
            )
        if c.type == "call":
            call_line = c.start_point[0] + 1
            calls.append(
                NormalizedCall(
                    callee=_py_call_callee_text(c),
                    line=call_line,
                    args=_py_call_args(c),
                    declared_raises=_frob_raises_declaration(source_lines, call_line),
                )
            )
        if c.type == "attribute" and _py_is_self_attribute(c):
            field_name_node = _child(c, "attribute")
            if field_name_node is not None:
                field_accesses.append(
                    NormalizedFieldAccess(
                        name=_node_text(field_name_node),
                        line=c.start_point[0] + 1,
                        is_write=_py_is_field_write(c),
                    )
                )
        if c.type == "return_statement":
            value = next(iter(c.named_children), None)
            returns.append(
                NormalizedReturn(
                    line=c.start_point[0] + 1,
                    value_text=_node_text(value) if value is not None else None,
                )
            )
        if c.type == "raise_statement":
            raises.append(
                NormalizedRaise(
                    line=c.start_point[0] + 1,
                    exception_type=_py_raise_exception_type(c),
                )
            )
        if c.type == "except_clause":
            catches.append(
                NormalizedCatch(
                    line=c.start_point[0] + 1,
                    exception_type=_py_except_exception_type(c),
                )
            )
        if c.type == "subscript":
            subscripts.append(NormalizedSubscript(line=c.start_point[0] + 1))
        _py_collect_body_events(
            c,
            branches,
            loops,
            calls,
            field_accesses,
            returns,
            raises,
            catches,
            subscripts,
            source_lines,
        )


def _py_normalize_params(func_node: Node) -> list[NormalizedParam]:
    """`NormalizedParam`s for `func_node`'s parameter list, in source order."""
    params_node = _child(func_node, "parameters")
    if params_node is None:
        return []
    out: list[NormalizedParam] = []
    for p in params_node.named_children:
        if p.type == "identifier":
            out.append(NormalizedParam(name=_node_text(p)))
        elif p.type in ("typed_parameter", "typed_default_parameter"):
            name_node = next(
                (n for n in p.named_children if n.type == "identifier"), None
            )
            ann = _child(p, "type")
            out.append(
                NormalizedParam(
                    name=_node_text(name_node) if name_node is not None else "?",
                    type=_annotation_text(ann) if ann is not None else None,
                    has_default=p.type == "typed_default_parameter",
                )
            )
        elif p.type == "default_parameter":
            name_node = _child(p, "name")
            out.append(
                NormalizedParam(
                    name=_node_text(name_node) if name_node is not None else "?",
                    has_default=True,
                )
            )
    return out


# frob:invariant terminates reason="recurses only into a nested function_definition \
# one tree-sitter edge below the current node's own body; a lexical prover cannot see \
# that the nested node's subtree is structurally smaller without dataflow" \
# measure="tree-sitter AST depth under func_node, finite per parse"
def _py_build_function(
    func_node: Node, is_method: bool, source_lines: tuple[str, ...] = ()
) -> NormalizedFunction:
    """One `function_definition` (top-level, method, or nested) as a
    `NormalizedFunction` -- events flattened via `_py_collect_body_events`,
    nested `function_definition`s recursed into `nested_functions`, and
    `max_nesting_depth`/`cyclomatic` computed via the pre-existing
    `_py_max_nesting`/`_py_cyclomatic` walks (kept as SEPARATE fields, not
    derived from the flattened event lists -- see
    `NormalizedFunction.max_nesting_depth`'s docstring) so these two metrics
    match the original per-language walk exactly, byte-for-byte.
    `source_lines` (T-0689, optional) is forwarded to
    `_py_collect_body_events` for `frob:callee-raises` declaration parsing."""
    name_node = _child(func_node, "name")
    name = _node_text(name_node) if name_node else "?"
    body = _child(func_node, "body")
    ret_node = _child(func_node, "return_type")
    branches: list[NormalizedBranch] = []
    loops: list[NormalizedLoop] = []
    calls: list[NormalizedCall] = []
    field_accesses: list[NormalizedFieldAccess] = []
    returns: list[NormalizedReturn] = []
    raises: list[NormalizedRaise] = []
    catches: list[NormalizedCatch] = []
    subscripts: list[NormalizedSubscript] = []
    nested: list[NormalizedFunction] = []
    if body is not None:
        _py_collect_body_events(
            body,
            branches,
            loops,
            calls,
            field_accesses,
            returns,
            raises,
            catches,
            subscripts,
            source_lines,
        )
        for c in body.named_children:
            if c.type == "function_definition":
                nested.append(
                    _py_build_function(c, is_method=False, source_lines=source_lines)
                )
    return NormalizedFunction(
        name=name,
        line=func_node.start_point[0] + 1,
        body_line_count=_py_function_line_count(func_node),
        params=_py_normalize_params(func_node),
        return_type=_annotation_text(ret_node) if ret_node is not None else None,
        is_method=is_method,
        max_nesting_depth=_py_max_nesting(body) if body is not None else 0,
        cyclomatic=_py_cyclomatic(body) if body is not None else 0,
        branches=branches,
        loops=loops,
        calls=calls,
        field_accesses=field_accesses,
        returns=returns,
        raises=raises,
        catches=catches,
        subscripts=subscripts,
        nested_functions=nested,
    )


# frob:ticket T-0727
def _py_class_fields(body: Node) -> list[NormalizedField]:
    """Class-level annotated assignments (`x: int`, `x: int = 0`) directly
    inside a class body -- `self.x = ...` instance fields set only inside
    `__init__` are intentionally not walked here (T-0610's first pass keeps
    this cheap; no existing check needs instance-field discovery yet).
    tree-sitter-python yields the `assignment` node directly as a named
    child of the class `block` (no `expression_statement` wrapper, unlike
    some other grammars) -- T-0727 fixed this gating on a wrapper node
    that never actually occurs, which silently dropped every class-level
    field."""
    out: list[NormalizedField] = []
    for c in body.named_children:
        inner = c
        if inner.type == "expression_statement":
            inner = next(iter(inner.named_children), None)
        if inner is None or inner.type != "assignment":
            continue
        left = _child(inner, "left")
        type_node = _child(inner, "type")
        if left is not None and left.type == "identifier":
            out.append(
                NormalizedField(
                    name=_node_text(left),
                    line=c.start_point[0] + 1,
                    type=_annotation_text(type_node) if type_node is not None else None,
                )
            )
    return out


def _py_build_class(
    class_node: Node, source_lines: tuple[str, ...] = ()
) -> NormalizedClass:
    """One `class_definition` as a `NormalizedClass`: its base-class names
    (as written), class-level fields (`_py_class_fields`), and direct
    methods (`_py_methods`, unchanged -- only `function_definition`
    children directly inside the class body, matching `_check_god_classes`'
    prior method count exactly). `source_lines` (T-0689, optional) is
    forwarded to each method's `_py_build_function`."""
    name_node = _child(class_node, "name")
    name = _node_text(name_node) if name_node else "?"
    bases: list[str] = []
    superclasses = _child(class_node, "superclasses")
    if superclasses is not None:
        bases = [_node_text(a) for a in superclasses.named_children]
    body = _child(class_node, "body")
    fields: list[NormalizedField] = []
    methods: list[NormalizedFunction] = []
    if body is not None:
        fields = _py_class_fields(body)
        methods = [
            _py_build_function(m, is_method=True, source_lines=source_lines)
            for m in _py_methods(body)
        ]
    return NormalizedClass(
        name=name,
        line=class_node.start_point[0] + 1,
        bases=bases,
        fields=fields,
        methods=methods,
    )


def _py_plain_import_statement_imports(stmt: Node) -> list[NormalizedImport]:
    """`NormalizedImport` entries for one bare `import x` / `import x as y`
    statement node (extracted from `_py_build_module` to cut nesting,
    T-0394)."""
    line = stmt.start_point[0] + 1
    out: list[NormalizedImport] = []
    for name_node in stmt.named_children:
        if name_node.type in ("dotted_name", "identifier"):
            out.append(NormalizedImport(module=_node_text(name_node), line=line))
        elif name_node.type == "aliased_import":
            mod_node = _child(name_node, "name")
            if mod_node is not None:
                out.append(NormalizedImport(module=_node_text(mod_node), line=line))
    return out


def _py_build_module(
    tree: object, rel: str, source_lines: tuple[str, ...] = ()
) -> NormalizedModule:
    """The whole-file `NormalizedModule` for a parsed python file: top-level
    imports, classes, and free functions (`PythonAdapter.adapt`).
    `source_lines` (T-0689, optional -- callers with no raw source, e.g. the
    per-check helpers in this module that only ever had a `tree`, pass
    nothing and every call site's `declared_raises` stays `None`) threads
    down to `_py_collect_body_events` for `frob:callee-raises` declaration
    parsing."""
    t: Tree = cast("Tree", tree)
    classes: list[NormalizedClass] = []
    functions: list[NormalizedFunction] = []
    imports: list[NormalizedImport] = []
    for c in t.root_node.children:
        if c.type == "class_definition":
            classes.append(_py_build_class(c, source_lines))
        elif c.type == "function_definition":
            functions.append(
                _py_build_function(c, is_method=False, source_lines=source_lines)
            )
        elif c.type == "import_statement":
            imports.extend(_py_plain_import_statement_imports(c))
        elif c.type == "import_from_statement":
            mod_node = _child(c, "module_name")
            names = [
                _node_text(n)
                for n in c.named_children
                if n.type == "dotted_name" and n is not mod_node
            ]
            imports.append(
                NormalizedImport(
                    module=_node_text(mod_node) if mod_node is not None else "",
                    line=c.start_point[0] + 1,
                    names=names,
                )
            )
    return NormalizedModule(
        path=rel,
        language="python",
        imports=imports,
        classes=classes,
        functions=functions,
    )


# frob:doc docs/modules/arch.md#normalized-code-model
# frob:tests tests/unit/test_arch.py::TestPythonAdapter.test_adapt_arch_python_fixture_shape  # noqa: E501
class PythonAdapter:
    """`LanguageAdapter` (T-0609) for python: maps a `raw_tree`-parsed
    python file's tree-sitter `Tree` onto a `NormalizedModule` by reusing
    this module's existing node-level walkers (`_py_build_module` and
    friends) -- the same tree-sitter grammar shapes `_check_*` already
    understood, just projected onto the shared shape instead of consumed
    directly, so the checks migrated onto `NormalizedModule`
    (`_check_long_functions`, `_check_god_classes`, `_check_deep_nesting`)
    read identical data through one extra layer of indirection."""

    language = "python"

    # frob:doc docs/modules/arch.md#normalized-code-model
    # frob:tests tests/unit/test_arch.py::TestPythonAdapter.test_adapt_arch_python_fixture_shape  # noqa: E501
    def adapt(self, tree: object, source: bytes, rel: str) -> NormalizedModule:
        """Build the `NormalizedModule` for one parsed python file (`tree`,
        `rel`) -- `source`'s decoded lines (T-0689) feed `_py_build_module`
        so each call site's `# frob:callee-raises` comment (`NormalizedCall.
        declared_raises`) can be parsed; tree-sitter `Node.text` still
        carries its own byte slice for everything else, unaffected."""
        source_lines = tuple(source.decode("utf-8", errors="replace").splitlines())
        return _py_build_module(tree, rel, source_lines)


def _iter_normalized_functions(
    module: NormalizedModule,
) -> Iterator[tuple[NormalizedFunction, str]]:
    """Yield `(function, qualname_prefix)` for every function in `module`
    (top-level free functions, class methods, and nested functions) -- the
    `NormalizedModule` analogue of `_iter_py_functions`, used by the checks
    migrated onto it (T-0610)."""

    def _rec(
        func: NormalizedFunction, prefix: str
    ) -> Iterator[tuple[NormalizedFunction, str]]:
        yield func, prefix
        for nested in func.nested_functions:
            yield from _rec(nested, prefix)

    for f in module.functions:
        yield from _rec(f, "")
    for c in module.classes:
        for m in c.methods:
            yield from _rec(m, f"{c.name}.")


def _normalized_is_complex(func: NormalizedFunction) -> bool:
    """Whether a `NormalizedFunction` is structurally complex enough for the
    long-function rule to fire (T-0289, re-expressed on the normalized
    model at T-0610): deep nesting OR a high cyclomatic proxy, reading the
    adapter-computed `max_nesting_depth`/`cyclomatic` fields -- identical
    thresholds and semantics to the pre-migration `_py_is_complex`."""
    return (
        func.max_nesting_depth >= _LONG_FUNCTION_NESTING_THRESHOLD
        or func.cyclomatic >= _LONG_FUNCTION_CYCLOMATIC_THRESHOLD
    )


def _check_deep_nesting(
    tree: object,
    path: Path,
    rel: str,
    max_nesting_depth: int,
    out: list[ArchSuggestion],
) -> None:
    """Flag python functions whose control-flow nesting exceeds the
    threshold -- reads `NormalizedModule`/`NormalizedFunction.
    max_nesting_depth` (T-0610) instead of walking `tree` directly.

    T-1066: a function whose leading-comment block carries a reasoned
    `# arch-exempt: deep-nesting reason="..."` directive
    (`_deep_nesting_exempt_reason`) is skipped -- a detector-owned escape
    for a genuinely irreducible textbook algorithm (e.g. an iterative
    Tarjan's SCC's work-stack unwind), never a blanket suppression; the
    generic `frob:waive` channel cannot reach this category at all (see
    `_ARCH_EXEMPT_DEEP_NESTING_RE`'s comment), so this exists specifically
    to give deep-nesting the same reasoned-override precedent ARCH001
    already has for long-function, without touching the gate/waiver
    pipeline this category is deliberately kept off."""
    module = _py_build_module(tree, rel)
    source_lines: tuple[str, ...] | None = None
    for func, prefix in _iter_normalized_functions(module):
        depth = func.max_nesting_depth
        if depth <= max_nesting_depth:
            continue
        if source_lines is None:
            source_lines = tuple(
                path.read_text(encoding="utf-8", errors="replace").splitlines()
            )
        exempt_reason = _deep_nesting_exempt_reason(source_lines, func.line)
        if exempt_reason is not None:
            _log.debug(
                "deep-nesting: %s::%s%s exempted: %s",
                rel,
                prefix,
                func.name,
                exempt_reason,
            )
            continue
        out.append(
            ArchSuggestion(
                file=rel,
                line=func.line,
                category="deep-nesting",
                severity="suggestion",
                message=(
                    f"function `{prefix}{func.name}` has"
                    f" nesting depth {depth}"
                    f" (threshold: {max_nesting_depth})"
                ),
            )
        )


def _annotation_text(node: Node) -> str:
    """The stripped source text of a type-annotation node."""
    return _node_text(node).strip()


# frob:ticket T-0632
def _extract_signatures(
    tree: object,
    rel: str,
) -> list[tuple[str, str, tuple[str, ...], str, str]]:
    """`(rel, func_name, param_types, return_type, body_fingerprint)` for
    every python function carrying at least one annotated parameter or an
    annotated return type.

    T-0632: `func_name`/`param_types`/`return_type` are read off
    `NormalizedModule` (`_iter_normalized_functions`, the same shape
    `_check_long_functions`/`_check_deep_nesting` already consume) instead
    of a bespoke raw-tree param/return walk -- `_py_param_types` (the prior
    ad-hoc walk) is gone, folded into the shared `NormalizedParam.type`
    field every adapter already fills in identically. `body_fingerprint`
    stays on the raw AST (`_body_fingerprint`, paired to its normalized
    function by `(class_prefix, name, line)`, a stable per-file key since
    two functions cannot share a definition line): T-0370's alpha-renaming
    (`frob.dup._legacy_py`'s `_collect_locals_py`/`_serialize_py_body`)
    needs the full raw parse tree to walk/rename every local, and
    `NormalizedFunction` deliberately carries no raw-body projection for
    it -- adding one would just duplicate the dup-scanner's own
    local-collection/serialization logic onto the model instead of
    replacing a raw walk with one, so this one piece is a reasoned
    decision to stay raw, not an oversight."""
    t: Tree = cast("Tree", tree)
    module = _py_build_module(tree, rel)
    fingerprints: dict[tuple[str, str, int], str] = {
        (prefix, fname, func.start_point[0] + 1): _body_fingerprint(func)
        for func, prefix, fname in _iter_py_functions(t.root_node)
    }
    results: list[tuple[str, str, tuple[str, ...], str, str]] = []
    for func, prefix in _iter_normalized_functions(module):
        param_types = [p.type for p in func.params if p.type]
        ret = func.return_type or ""
        if param_types or ret:
            body_fp = fingerprints.get((prefix, func.name, func.line), "")
            results.append((rel, func.name, tuple(param_types), ret, body_fp))
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


def _collect_dispatch_refs_from_call(call: Node, out: set[str]) -> None:
    """Collect dispatch-like identifier refs from one `call` node's own
    callee and argument list (extracted from `_collect_dispatch_refs` to
    cut nesting, T-0394; see that function's docstring for the shapes that
    count)."""
    func = _child(call, "function")
    if func is not None and func.type == "identifier":
        out.add(_node_text(func))
    args = _child(call, "arguments")
    if args is None:
        return
    for a in args.named_children:
        if a.type == "identifier":
            out.add(_node_text(a))
        elif a.type == "keyword_argument":
            val = _child(a, "value")
            if val is not None and val.type == "identifier":
                out.add(_node_text(val))


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
            _collect_dispatch_refs_from_call(c, out)
        elif c.type == "dictionary":
            _collect_dispatch_refs_from_dict(c, out)
        elif c.type in _DISPATCH_CONTAINER_TYPES:
            _collect_dispatch_refs_from_container(c, out)
        _collect_dispatch_refs(c, out)


def _collect_dispatch_refs_from_dict(dictionary: Node, out: set[str]) -> None:
    """Collect dispatch-like identifier refs from one `dictionary`
    literal's pair values (extracted from `_collect_dispatch_refs` to cut
    nesting, T-0394)."""
    for pair in dictionary.named_children:
        if pair.type == "pair":
            val = _child(pair, "value")
            if val is not None and val.type == "identifier":
                out.add(_node_text(val))


def _collect_dispatch_refs_from_container(container: Node, out: set[str]) -> None:
    """Collect dispatch-like identifier refs from one `list`/`set`/`tuple`
    literal's elements (extracted from `_collect_dispatch_refs` to cut
    nesting, T-0394)."""
    for el in container.named_children:
        if el.type == "identifier":
            out.add(_node_text(el))


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


# T-1068: the fixed, small set of per-language-adapter name tags a same-
# signature abstraction-opportunity group's members can carry -- mirrors
# frob.arch's own per-language walker convention (`_py_*`/`_rust_*`/
# `_kt_*`/`_ts_*`/`_cpp_*`, e.g. `arch/_rust.py`'s `_rust_build_module`/
# `_kt_build_module`/`_ts_build_module` trio) rather than any project-wide
# naming scheme, so this stays a narrow, reviewable allowlist, not a
# guess at what "looks like a language tag".
_LANGUAGE_TAGS = ("py", "rust", "kt", "ts", "cpp")

#: Matches a language tag as an underscore-delimited token anywhere in a
#: function name (`_LANGUAGE_TAG_RE.search("_kt_this_field_name")` ->
#: `"kt"`) -- underscore-delimited on BOTH sides so `_ts_...`/`..._ts_...`
#: match but an incidental substring like `results_summary` (no
#: underscore before `ts`) does not. This is the STRUCTURAL rigor T-0360's
#: own `_is_dispatch_family` docstring calls out (no raw text proximity):
#: the tag must occupy a real name-segment boundary, not just appear
#: somewhere in the string.
_LANGUAGE_TAG_RE = re.compile(
    r"(?:^|_)(?P<tag>" + "|".join(_LANGUAGE_TAGS) + r")(?:_|$)"
)


def _language_tag(fname: str) -> str | None:
    """The single language tag (T-1068, `_LANGUAGE_TAGS`) `fname` carries as
    an underscore-delimited prefix/infix segment, or `None` when it carries
    none. `_LANGUAGE_TAG_RE.search` finds the FIRST such segment only --
    good enough here since every real per-language walker name in this
    codebase carries exactly one tag (`_kt_build_module`, never a name
    combining two)."""
    m = _LANGUAGE_TAG_RE.search(fname)
    return m.group("tag") if m else None


def _is_language_parity_family(members: list[tuple[str, str]]) -> bool:
    """Whether a shared-signature `members` group (T-1068, filed from
    T-0393) is an intentional per-language-parity family rather than an
    accidental duplication: every member's name carries a language tag
    (`_language_tag`) AND every member carries a DIFFERENT tag from the
    fixed `_LANGUAGE_TAGS` set -- e.g. `_rust_build_module`/
    `_kt_build_module`/`_ts_build_module` each independently walking one
    language's own tree-sitter grammar to build the same
    `NormalizedModule` shape. This is NOT the T-0360 dispatch-table shape
    (`_is_dispatch_family`, no common call site is required here) but the
    same false-positive class: the shared signature is the point --
    `frob.lang.LanguageAdapter`'s per-language contract -- not a missing
    abstraction to extract.

    Distinctness is the load-bearing check: a group of 3 all-`_py_`-tagged
    helpers sharing a signature is NOT parity (three python functions
    happen to collide, exactly the accidental-duplication case this
    detector exists to catch) -- only genuine one-member-per-language
    spread is excluded. A group with even one untagged member (no
    recognized language segment at all) is never excluded either: with no
    tag to compare, "parity" cannot be established structurally, so the
    group falls through to the normal signature/body-similarity checks."""
    if len(members) < 2:
        return False
    tags = [_language_tag(fname) for _, fname in members]
    if any(tag is None for tag in tags):
        return False
    return len(set(tags)) == len(tags)


#: `frob.arch`'s own detector-registry naming convention (T-1112, filed
#: from T-1084): every `check_*` function across the package (`_python.py`,
#: `_rust.py`, `_typescript.py`, `_async_hazards.py`, and siblings) is a
#: detector plugged into the SAME `(NormalizedModule) -> list[ArchSuggestion]`
#: registry contract -- the arity mismatch is why a signature-shape check
#: alone cannot tell these apart from a real duplication (a handful of
#: `check_*` detectors take an extra param), so this is name-based, like
#: `_is_dispatch_family`/`_is_language_parity_family`'s own checks, never
#: raw text proximity. Measured empirically (T-1112) to also need each
#: family's own top-level `run_*_checks` aggregator (e.g. `_smells.py`'s
#: `run_smell_checks`, `_srp.py`'s `run_srp_checks`) alongside the bare
#: `check_*` detectors themselves -- an aggregator has the exact same
#: `(NormalizedModule) -> list[ArchSuggestion]` shape as the detectors it
#: calls (it just concatenates their results), so the same 27-member group
#: this ticket was filed to exclude is ~20 `check_*` detectors plus 7
#: `run_*_checks` aggregators, not `check_*` alone.
_CHECK_REGISTRY_NAME_RE = re.compile(r"^(check_[a-z_]+|run_[a-z_]+_checks)$")


def _is_check_registry_family(members: list[tuple[str, str]]) -> bool:
    """Whether a shared-signature `members` group (T-1112) is `frob.arch`'s
    own check-function registry rather than an accidental duplication:
    every member's bare name matches the package's `check_*` detector (or
    `run_*_checks` family-aggregator) convention (`_CHECK_REGISTRY_NAME_RE`).
    Structurally identical to `_is_dispatch_family`/`_is_language_parity_family`
    -- name/structure only, no raw text proximity -- but the discriminator
    here is a fixed project-wide naming convention rather than a
    dispatch-site lookup or a per-language tag set: `frob.arch`'s 27-member
    `(NormalizedModule) -> list[ArchSuggestion]` group (T-1084's triage) IS
    literally every `check_*` detector in the package plus each family's
    `run_*_checks` aggregator, the intentional common interface every
    detector module registers through, not duplicate logic to extract."""
    if len(members) < 2:
        return False
    return all(_CHECK_REGISTRY_NAME_RE.match(fname) for _, fname in members)


#: `frob.gates`'s own gate/rule-builder return-type convention (T-1141,
#: filed from T-1114 as the mirror of T-1112's `check_*` registry
#: exclusion): every gate function (`*_gate`) and every rule-builder
#: helper it dispatches to (`_tick001_duplicate_ids`, `_cov001`,
#: `_test006`, `_inv005`, and dozens of siblings across gates/__init__.py
#: and its `_*.py` split modules) returns one of these three shapes --
#: `Violation`, `list[Violation]`, or `tuple[Violation, ...]` -- because
#: `Violation` is `frob.gates`'s own domain type: nothing outside the
#: gates package constructs one. A shared return type built entirely from
#: `Violation`/collections of it is therefore the intentional common gate/
#: rule-builder contract this package registers every check through, the
#: same shape `_is_check_registry_family` already carves out for
#: `frob.arch`'s own `check_*`/`run_*_checks` convention -- not duplicate
#: logic, regardless of how many members happen to share it or what they
#: are individually named (a structural discriminator, mirroring
#: `_is_language_parity_family`'s per-language tag check, rather than a
#: name-pattern one like `_is_check_registry_family`'s, since gate/rule-
#: builder names do not share one fixed prefix/suffix convention the way
#: `check_*`/`run_*_checks` do).
_GATE_RULE_BUILDER_RETURN_TYPES = frozenset(
    {"Violation", "list[Violation]", "tuple[Violation, ...]"}
)


def _is_gate_rule_builder_family(ret: str) -> bool:
    """Whether a shared-signature group's return type `ret` (T-1141) is
    `frob.gates`'s own gate/rule-builder convention rather than an
    accidental duplication: `ret` is one of `_GATE_RULE_BUILDER_RETURN_
    TYPES`. Structural, not name-based -- see `_GATE_RULE_BUILDER_RETURN_
    TYPES`'s docstring for why a return-type check is the right
    discriminator for this family specifically."""
    return ret in _GATE_RULE_BUILDER_RETURN_TYPES


#: `frob.process`/`frob.check`'s own check-stage-runner return-type
#: convention (T-1144, filed from T-1124 as the mirror of T-1112's
#: `check_*` registry exclusion and T-1141's gate/rule-builder
#: exclusion): every check-stage runner/tool-result builder across
#: `src/frob/check/**`, `src/frob/process/parsers/**`, and the
#: individual arch/cycle/dup CLI runners returns `ToolResult` or
#: `ToolResult | None`, because `ToolResult` is `frob.process`'s own
#: domain type -- nothing outside the check/process stack constructs
#: one. T-1144's own investigation confirmed the genuine body-level
#: duplication in this area (`_opt_in_deploy_stage_result`,
#: `_missing_tool_result` forwarding to `tool_unavailable_result`) was
#: already extracted by T-1124; what remained across all 4 ToolResult-
#: shaped groups (24 members measured) was purely this same
#: convention-shape false positive, not a further extraction
#: opportunity -- a lone unrelated member like `parse_junit_xml`
#: (real XML-parsing logic that happens to share `(str, str) ->
#: ToolResult` with three trivial synthetic-result builders purely
#: because its `tool` parameter has a default) makes that especially
#: clear: there is no one coherent family to extract here, only the
#: shared return type.
_TOOL_RESULT_BUILDER_RETURN_TYPES = frozenset({"ToolResult", "ToolResult | None"})


def _is_tool_result_builder_family(ret: str) -> bool:
    """Whether a shared-signature group's return type `ret` (T-1144) is
    `frob.process`/`frob.check`'s own check-stage-runner convention
    rather than an accidental duplication: `ret` is one of `_TOOL_RESULT_
    BUILDER_RETURN_TYPES`. Structural, not name-based -- see
    `_TOOL_RESULT_BUILDER_RETURN_TYPES`'s docstring for why a return-type
    check is the right discriminator for this family specifically,
    mirroring `_is_gate_rule_builder_family`'s identical shape for
    `frob.gates`'s own `Violation` convention."""
    return ret in _TOOL_RESULT_BUILDER_RETURN_TYPES


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


def _near_duplicate_cluster_native(
    bodies: list[str],
) -> list[int] | None:
    """`frob_core.near_duplicate_indices` over `bodies`, or `None` when the
    native extension is not importable (T-0953). ONE marshal per
    same-signature group -- the whole eligible-body list crosses the FFI
    boundary once, not once per pairwise comparison (the batching shape
    T-0930's reverted `resolve_call_edges` prototype lacked, and the reason
    that prototype measured net slower where this kernel measures net
    faster: this repo's real same-signature groups run up to several dozen
    members, large enough for the O(n^2) comparison work to amortize the
    fixed PyO3 marshaling tax, unlike T-0930's per-symbol/per-package call
    sites)."""
    from frob.dup._core import core_available

    if not core_available():
        return None
    import frob_core

    return list(frob_core.near_duplicate_indices(bodies, _BODY_SIMILARITY_THRESHOLD))


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
    misrepresented as 30 functions all sharing logic.

    T-0953: dispatches to the `frob_core` kernel
    (`_near_duplicate_cluster_native`) when available -- measured ~2.6x
    faster than the pure-Python loop below at this repo's real
    same-signature-group sizes (median 2.49s -> 0.97s thread_time across
    this repo's own 67 real groups, 0 parity mismatches against
    `difflib.SequenceMatcher.ratio()`) -- and falls back to the original
    pairwise `difflib` loop, BYTE-IDENTICAL in result, when it is not."""
    eligible = [m for m in members if len(m[2].split()) >= _BODY_MIN_TOKENS]
    native_idx = _near_duplicate_cluster_native([m[2] for m in eligible])
    if native_idx is not None:
        return [eligible[i] for i in native_idx]
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
    intentional dispatch families and are still skipped first, as are
    groups whose members are each a distinctly-tagged per-language walker
    (`_is_language_parity_family`, T-1068) -- the same false-positive
    class filed from T-0393 (arch's own `_py_*`/`_rust_*`/`_kt_*`/`_ts_*`/
    `_cpp_*` walker families sharing a signature by design, not by
    accident) -- and groups whose members are all `frob.arch`'s own
    `check_*` detector-registry functions (`_is_check_registry_family`,
    T-1112, filed from T-1084), all `frob.gates`'s own gate/rule-
    builder return-type convention (`_is_gate_rule_builder_family`,
    T-1141, filed from T-1114), or all `frob.process`/`frob.check`'s own
    check-stage-runner return-type convention
    (`_is_tool_result_builder_family`, T-1144, filed from T-1124)."""
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
        if _is_language_parity_family(members):
            continue
        if _is_check_registry_family(members):
            continue
        if _is_gate_rule_builder_family(ret):
            continue
        if _is_tool_result_builder_family(ret):
            continue
        flagged = _abstraction_group_evidence(ptypes, ret, members_with_body)
        if len(flagged) < 2:
            continue
        _emit_abstraction_suggestion(ptypes, ret, flagged, out)
