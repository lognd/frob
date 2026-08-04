"""DOCENUM001: doc-claimed collection-member drift (docs/modules/gates.md,
T-1227, gate-gap class 1 in docs/audits/docs-staleness-2026-07-29.md).

Motivating case: a doc's prose routinely restates a code collection's
members as a table/list ("gates-native aliases: cycle, dup, ...") with no
graph edge at all -- DRIFT001 re-verifies the anchored symbol's own digest
alone, so a member ADDED OR REMOVED from the underlying collection never
fires anything; the prose silently goes stale (~40 confirmed instances in
the 2026-07-29 audit, the dominant gate-gap class found).

The fix is a `frob:enumerates` doc-side directive
(`<!-- frob:enumerates path.py::Sym members="a,b,c" -->`,
`frob.graph.dsl._ENUMERATES_RE`) that makes the doc author's claimed member
list EXPLICIT, CONTENT, not prose -- DOCENUM001 then AST-diffs that claimed
list against the named collection literal's REAL members at check time,
independent of ack state (unlike DRIFT001's digest-staleness check, a
doc's claimed member text can be byte-identical to its last ack and still
be WRONG if the underlying literal changed and the ack was never re-run;
DOCENUM001 re-derives the real members every run, so it cannot go stale
the way an ack-gated check can).

Supported collection shapes (T-1227's declared shape list): a module- or
class-level `dict`/`set`/`tuple`/`frozenset` literal assignment, a
`typing.Literal[...]` annotation, an `ErrorSet` subclass, or a `StrEnum`/
`Enum` subclass -- each contributes its member NAMES (dict keys as their
literal string/attribute value, not the assignment target; enum/errorset
member names; Literal's own string args). A collection shape this module
cannot resolve is NOT silently accepted as passing -- `_extract_members`
returns `None` and the gate reports an UNRESOLVABLE-shape violation
(punt), rather than a false "matches" result.
"""
# frob:ticket T-1227

from __future__ import annotations

import ast
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.graph._models import EdgeKind, GraphSnapshot
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = ["docenum001_gate"]


def _site_from_origin(origin: str) -> tuple[str, int]:
    """Best-effort `(file, line)` split of an edge's `path:line` origin."""
    file_part, _, line_part = origin.rpartition(":")
    if line_part.isdigit():
        return file_part, int(line_part)
    return origin, 0


def _parse_symref(symref: str) -> tuple[str, str] | None:
    """Split `path.py::Qualname` into `(path, qualname)`, or `None` if the
    target does not have exactly the one `::` separator this directive's
    target grammar requires (mirrors DOC007's own dotted-vs-`::` shape
    check, `frob.gates._docptr`)."""
    parts = symref.split("::")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return parts[0], parts[1]


def _find_node_for_qualname(tree: ast.Module, qualname: str) -> ast.AST | None:
    """Resolve a dotted `qualname` (e.g. `Outer.Inner.NAME`) to its own
    innermost defining AST node -- an assignment target's value, or a
    class definition -- walking the module tree one dotted segment at a
    time. `None` if any segment along the path cannot be found."""
    parts = qualname.split(".")
    scope: ast.AST = tree
    node: ast.AST | None = None
    for i, part in enumerate(parts):
        node = _find_in_scope(scope, part)
        if node is None:
            return None
        if i < len(parts) - 1:
            scope = node
    return node


def _find_in_scope(scope: ast.AST, name: str) -> ast.AST | None:
    """One dotted segment's lookup within `scope`'s immediate body: a
    class/function definition by name, or an assignment target's RHS
    value by name (module- or class-level `NAME = <literal>`)."""
    body = getattr(scope, "body", None)
    if body is None:
        return None
    for stmt in body:
        if isinstance(stmt, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if stmt.name == name:
                return stmt
            continue
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return stmt.value
        elif isinstance(stmt, ast.AnnAssign):
            if isinstance(stmt.target, ast.Name) and stmt.target.id == name:
                return stmt.annotation if stmt.value is None else stmt.value
    return None


def _literal_str(node: ast.AST) -> str | None:
    """A dict-key/element node's own member name, if it is a plain string
    or attribute-style constant this gate can name -- `None` for anything
    it cannot resolve to a bare identifier/string."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _resolved_names(nodes: list[ast.AST]) -> frozenset[str] | None:
    """`frozenset` of each node's `_literal_str`, or `None` if `nodes` is
    empty or ANY entry fails to resolve to a bare name (a partial match is
    never silently returned as if it were the whole set)."""
    resolved: list[str] = []
    for node in nodes:
        name = _literal_str(node)
        if name is None:
            return None
        resolved.append(name)
    return frozenset(resolved) if resolved else None


# frob:ticket T-1504
def _extract_members(tree: ast.Module, qualname: str) -> frozenset[str] | None:
    """The real member-name set for `qualname`'s collection literal/class,
    or `None` if the shape is not one of the supported kinds (dict/set/
    tuple/frozenset literal, `Literal[...]`, `ErrorSet`/`StrEnum`/`Enum`
    subclass) -- a punt, not a silent pass."""
    node = _find_node_for_qualname(tree, qualname)
    if node is None:
        return None
    if isinstance(node, ast.ClassDef):
        # ErrorSet/StrEnum/Enum subclass: each class-body assignment target
        # name is one member (T-1227's ErrorSet/StrEnum shapes).
        members = {
            target.id
            for stmt in node.body
            if isinstance(stmt, ast.Assign)
            for target in stmt.targets
            if isinstance(target, ast.Name)
        }
        return frozenset(members) if members else None
    if isinstance(node, ast.Dict):
        keys = [k for k in node.keys if k is not None]
        return _resolved_names(list(keys))
    if isinstance(node, (ast.Set, ast.Tuple, ast.List)):
        return _resolved_names(list(node.elts))
    if isinstance(node, ast.Subscript):
        # typing.Literal[...] annotation.
        base = node.value
        base_name = (
            base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", None)
        )
        if base_name != "Literal":
            return None
        sl = node.slice
        elts: list[ast.AST] = list(sl.elts) if isinstance(sl, ast.Tuple) else [sl]
        return _resolved_names(elts)
    if isinstance(node, ast.Call):
        # frozenset({...}) call form.
        func_name = node.func.id if isinstance(node.func, ast.Name) else None
        if func_name != "frozenset" or len(node.args) != 1:
            return None
        return _extract_members_from_container(node.args[0])
    # frob:todo T-1506
    # Punt, disclosed: argparse `choices=[...]` lists (cycle.md/xref.md
    # --lang, parse.md tool table) are not resolved here -- a
    # `parser.add_argument(..., choices=[...])` call site has no bare
    # module/class-level assignment target `_find_node_for_qualname` can
    # walk to at all (the ticket's own "cheaply reachable" caveat); the
    # follow-up ticket above tracks widening `_extract_members` to this
    # shape rather than leaving it silently unsupported forever.
    return None


def _extract_members_from_container(node: ast.AST) -> frozenset[str] | None:
    """The set/list/tuple literal wrapped by a `frozenset(...)` call."""
    if isinstance(node, (ast.Set, ast.Tuple, ast.List)):
        return _resolved_names(list(node.elts))
    return None


def _resolve_edge_tree(
    root: Path, code_path: str, tree_cache: dict[str, ast.Module | None]
) -> ast.Module | None:
    """Parse (and memoize) `code_path`'s AST in `tree_cache`, or `None` if
    it cannot be read/parsed -- shared across every edge targeting the same
    file so DOCENUM001 never re-parses a source file per doc anchor."""
    if code_path not in tree_cache:
        try:
            text = (root / code_path).read_text(encoding="utf-8")
            tree_cache[code_path] = ast.parse(text, filename=code_path)
        except (OSError, SyntaxError, UnicodeDecodeError) as exc:
            _log.warning("DOCENUM001: cannot parse %s: %s", code_path, exc)
            tree_cache[code_path] = None
    return tree_cache[code_path]


def _member_mismatch_violation(
    file: str, line: int, edge, claimed: frozenset[str], actual: frozenset[str]
) -> Violation | None:
    """The DOCENUM001 `Violation` for one edge's claimed-vs-actual member
    diff, or `None` if the sets already match exactly."""
    if claimed == actual:
        return None
    missing = sorted(actual - claimed)
    extra = sorted(claimed - actual)
    parts = []
    if missing:
        parts.append(f"doc omits: {', '.join(missing)}")
    if extra:
        parts.append(f"doc claims stale/nonexistent: {', '.join(extra)}")
    detail = "; ".join(parts) if parts else "member sets differ"
    return Violation(
        rule="DOCENUM001",
        severity=Severity.ERROR,
        file=file,
        line=line,
        message=(
            f"DOCENUM001: frob:enumerates at {edge.src} claims a stale "
            f"member list for {edge.target!r} ({detail})"
        ),
    )


# frob:enforces CHK-GATE-DOCENUM001
def _docenum001_violation_for_edge(
    root: Path, edge, tree_cache: dict[str, ast.Module | None]
) -> Violation | None:
    """The DOCENUM001 `Violation` for one `frob:enumerates` markdown edge,
    or `None` if its claimed member list matches the literal's actual
    members exactly."""
    file, line = _site_from_origin(edge.origin)
    parsed = _parse_symref(edge.target)
    if parsed is None:
        return Violation(
            rule="DOCENUM001",
            severity=Severity.ERROR,
            file=file,
            line=line,
            message=(
                f"DOCENUM001: frob:enumerates target {edge.target!r} at "
                f"{edge.src} is not a `path.py::Qualname` reference"
            ),
        )
    code_path, qualname = parsed
    tree = _resolve_edge_tree(root, code_path, tree_cache)
    if tree is None:
        return Violation(
            rule="DOCENUM001",
            severity=Severity.ERROR,
            file=file,
            line=line,
            message=(
                f"DOCENUM001: frob:enumerates at {edge.src} targets "
                f"{edge.target!r}, but {code_path} could not be read/parsed"
            ),
        )
    actual = _extract_members(tree, qualname)
    if actual is None:
        return Violation(
            rule="DOCENUM001",
            severity=Severity.WARN,
            file=file,
            line=line,
            message=(
                f"DOCENUM001: frob:enumerates at {edge.src} targets "
                f"{edge.target!r}, whose collection shape this gate cannot "
                "resolve (unsupported literal/class shape) -- member "
                "claim left unverified, not silently passed"
            ),
        )
    claimed = frozenset(
        m.strip() for m in edge.attrs.get("members", "").split(",") if m.strip()
    )
    return _member_mismatch_violation(file, line, edge, claimed, actual)


# frob:doc docs/modules/gates.md#docenum001-t-1227
def docenum001_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """DOCENUM001: every `frob:enumerates` doc anchor's claimed
    `members="..."` list must AST-match its bound collection literal's
    real members exactly, checked fresh every run (content-verified,
    ack-immune -- T-1227)."""
    root = Path(root)
    tree_cache: dict[str, ast.Module | None] = {}
    violations = [
        v
        for edge in snapshot.edges
        if edge.kind == EdgeKind.ENUMERATES
        for v in (_docenum001_violation_for_edge(root, edge, tree_cache),)
        if v is not None
    ]
    _log.info("docenum001: %d violation(s)", len(violations))
    return tuple(violations)
