"""GUARD001: a guard that reads a lockout/flag primitive with no reachable
writer in its own class (docs/modules/gates.md#guard001-t-4111).

F-307 H3-1 (T-4109/T-4111): a rate-limit-style guard reads a lockout state
(e.g. `retry_after_seconds(cls, ...)`) but nothing outside the guard's own
tests writes it (e.g. `record_failure(cls, ...)`) from a real, route-
reachable caller in the SAME class. A guard whose only writer is a test
calling the write primitive directly is a control that fires on nothing --
the exact gap the consumer's own test disguised. `WIRE001`
(`frob.gates._wire`) cannot see this: it answers "is this diff-added symbol
reached at all", never "does a specific READ primitive's class have a
route-reachable WRITE caller". `DEAD001`/`frob.graph.callgraph.
build_call_graph` cannot see it either -- that resolver only ever resolves
edges to PRIVATE (leading-underscore) callees (its own module docstring's
rule), while route handlers and guard/lockout primitives are routinely
PUBLIC. Per this ticket's own investigation (recorded in its body), this
is therefore a BESPOKE, narrowly-scoped closure check over parsed `ast`
symbols (never a text scan, unlike `WIRE001`'s reachability substrate,
and never routed through the private-only call-graph resolver) --
decided from parsed call/decorator nodes, not from source text.

Closure algorithm, per class:
1. Collect every method defined directly on the class.
2. A method is a ROUTE ENTRY POINT when it carries a decorator whose
   trailing name (the `Attribute.attr` or bare `Name.id` of the decorator
   expression, see `_decorator_name`) matches one of `_ROUTE_MARKERS` --
   configurable via `[guard_closure] route_decorator_markers` in
   `frob.toml`, never hardcoded to one framework's decorator spelling.
3. BFS over `self.<name>(...)`/`cls.<name>(...)`/bare `<name>(...)` calls
   within the class's own method bodies, starting from every route entry
   point, gives the CLOSURE of methods a real request can reach.
4. For every method that calls a configured READ primitive (a
   `GuardClosurePair.read` name match), the class is clean only if some
   method IN THE CLOSURE (reachable from a route entry point) calls the
   matching WRITE primitire for the same pair. A write call that exists
   in the class but is reachable only from a DIFFERENT class, or from no
   route entry at all (e.g. only from the class's own test file, which
   this check never parses as part of the production tree), does not
   satisfy closure -- distinguishing "a real caller reaches the write"
   from "a test calls the write directly", the exact gap this ticket
   exists to close.

`GuardClosurePair` names are configurable (`[[guard_closure.pairs]]` in
`frob.toml`, `read=`/`write=` keys) so this stays a naming-convention-
generic closure check, never hardcoded to one consumer's own symbol
names; `_DEFAULT_PAIRS` ships the one pair this ticket's own motivating
report named, and is used only when `frob.toml` configures none.
"""
# frob:ticket T-4111

from __future__ import annotations

import ast
import tomllib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from frob.excludes import iter_files
from frob.findings import Severity, Violation
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = [
    "GuardClosurePair",
    "guard_closure_gate",
    "load_guard_closure_pairs",
]


# frob:doc docs/modules/gates.md#guard001-t-4111
@dataclass(frozen=True)
class GuardClosurePair:
    """One configured lockout READ/WRITE primitive-name pair GUARD001
    checks class-scoped call closure over."""

    read: str
    write: str


#: The one pair this ticket's own motivating report (F-307 H3-1) named;
#: used only when `frob.toml` configures no `[[guard_closure.pairs]]`.
_DEFAULT_PAIRS: tuple[GuardClosurePair, ...] = (
    GuardClosurePair(read="retry_after_seconds", write="record_failure"),
)

#: Trailing decorator names (case-insensitive) treated as a route/entry-
#: point marker by default; overridden wholesale by `frob.toml`'s
#: `[guard_closure] route_decorator_markers`, never merged, so a project
#: with its own routing framework is never stuck also matching frob's
#: default guesses.
_DEFAULT_ROUTE_MARKERS: frozenset[str] = frozenset(
    {"route", "get", "post", "put", "patch", "delete", "websocket"}
)


# frob:doc docs/modules/gates.md#guard001-t-4111
def load_guard_closure_pairs(
    root: Path,
) -> tuple[tuple[GuardClosurePair, ...], frozenset[str]]:
    """Read `[[guard_closure.pairs]]` and `[guard_closure]
    route_decorator_markers` from `<root>/frob.toml`; fall back to
    `_DEFAULT_PAIRS`/`_DEFAULT_ROUTE_MARKERS` wholesale when either key is
    absent or the file itself does not exist."""
    toml_path = root / "frob.toml"
    if not toml_path.is_file():
        return _DEFAULT_PAIRS, _DEFAULT_ROUTE_MARKERS
    try:
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError, UnicodeDecodeError):
        _log.warning("guard_closure: failed to parse %s, using defaults", toml_path)
        return _DEFAULT_PAIRS, _DEFAULT_ROUTE_MARKERS
    section = data.get("guard_closure", {})
    raw_pairs = section.get("pairs", [])
    pairs = tuple(
        GuardClosurePair(read=p["read"], write=p["write"])
        for p in raw_pairs
        if "read" in p and "write" in p
    )
    if not pairs:
        pairs = _DEFAULT_PAIRS
    raw_markers = section.get("route_decorator_markers")
    markers = (
        frozenset(m.lower() for m in raw_markers)
        if raw_markers
        else _DEFAULT_ROUTE_MARKERS
    )
    _log.debug(
        "guard_closure: loaded %d pair(s), %d route marker(s)", len(pairs), len(markers)
    )
    return pairs, markers


def _decorator_name(node: ast.expr) -> str:
    """The trailing attribute/call name of one decorator expression --
    `"route"` for both `@app.route(...)` and `@route`."""
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _is_route_entry(
    func: ast.FunctionDef | ast.AsyncFunctionDef, markers: frozenset[str]
) -> bool:
    """True when `func` carries a decorator whose trailing name matches a
    configured route marker (case-insensitive)."""
    return any(_decorator_name(d).lower() in markers for d in func.decorator_list)


def _call_names(node: ast.AST) -> frozenset[str]:
    """Every call target's trailing name (attribute or bare name) invoked
    anywhere inside `node`'s subtree."""
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            target = child.func
            if isinstance(target, ast.Attribute):
                names.add(target.attr)
            elif isinstance(target, ast.Name):
                names.add(target.id)
    return frozenset(names)


@dataclass(frozen=True)
class _ClassInfo:
    """One parsed class's own methods and which of them are configured
    route entry points, for closure to walk."""

    qualname: str
    path: str
    line: int
    methods: dict[str, ast.FunctionDef | ast.AsyncFunctionDef]
    entries: frozenset[str]


def _classes_in_file(path: Path, rel: str, markers: frozenset[str]) -> list[_ClassInfo]:
    """Every `class` in `path`, with its direct methods and route-entry
    subset; returns `[]` for an unparseable/unreadable file rather than
    raising -- a single bad fixture file must never abort the whole gate."""
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError, OSError) as exc:
        _log.debug("guard_closure: skipping unparseable %s: %s", path, exc)
        return []
    out: list[_ClassInfo] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        methods = {
            n.name: n
            for n in node.body
            if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
        }
        entries = frozenset(
            name for name, m in methods.items() if _is_route_entry(m, markers)
        )
        out.append(
            _ClassInfo(
                qualname=f"{rel}::{node.name}",
                path=rel,
                line=node.lineno,
                methods=methods,
                entries=entries,
            )
        )
    return out


def _reachable_methods(cls: _ClassInfo, starts: Iterable[str]) -> frozenset[str]:
    """BFS closure, within `cls` only, of `self.<name>()`/`cls.<name>()`/
    bare `<name>()` calls starting from `starts` (the class's route entry
    points)."""
    seen: set[str] = set()
    queue = list(starts)
    while queue:
        name = queue.pop()
        if name in seen or name not in cls.methods:
            continue
        seen.add(name)
        for called in _call_names(cls.methods[name]):
            if called in cls.methods and called not in seen:
                queue.append(called)
    return frozenset(seen)


# frob:enforces CHK-GATE-GUARD001
def _class_violations(
    cls: _ClassInfo, pairs: Sequence[GuardClosurePair]
) -> list[Violation]:
    """`GUARD001` findings for one class: a read call site whose pair has
    no route-reachable write caller in this same class."""
    if not cls.entries:
        # No configured route entry point in this class at all -- closure
        # has nothing to start BFS from, so this check has no opinion
        # (a different gate's job to flag an entirely unreached class).
        return []
    reachable = _reachable_methods(cls, cls.entries)
    reachable_calls: set[str] = set()
    for name in reachable:
        reachable_calls |= _call_names(cls.methods[name])

    violations: list[Violation] = []
    for pair in pairs:
        read_sites = [
            (name, m) for name, m in cls.methods.items() if pair.read in _call_names(m)
        ]
        if not read_sites:
            continue
        if pair.write in reachable_calls:
            continue
        for name, method in read_sites:
            violations.append(
                Violation(
                    rule="GUARD001",
                    severity=Severity.ERROR,
                    file=cls.path,
                    line=method.lineno,
                    message=(
                        f"GUARD001: {cls.qualname}.{name} reads lockout primitive "
                        f"'{pair.read}' but no route-reachable caller of write "
                        f"primitive '{pair.write}' exists in this class -- a "
                        f"test calling '{pair.write}' directly does not satisfy "
                        f"closure (docs/modules/gates.md#guard001-t-4111)"
                    ),
                    symref=cls.qualname,
                )
            )
    return violations


# frob:doc docs/modules/gates.md#guard001-t-4111
def guard_closure_gate(root: Path) -> list[Violation]:
    """GUARD001: flag every class whose lockout READ call site has no
    write-primitive caller reachable from a route entry point in that
    SAME class (see module docstring for the closure algorithm and why
    this is bespoke rather than `frob.graph.callgraph`-based)."""
    pairs, markers = load_guard_closure_pairs(root)
    files = [f for f in iter_files(root, suffix=".py") if "/tests/" not in f.as_posix()]
    violations: list[Violation] = []
    for f in files:
        rel = f.relative_to(root).as_posix()
        for cls in _classes_in_file(f, rel, markers):
            violations.extend(_class_violations(cls, pairs))
    _log.info(
        "guard_closure: %d GUARD001 violation(s) over %d file(s)",
        len(violations),
        len(files),
    )
    return violations
