"""ROUTE001: a decorated route function that returns a bare dict literal
with no declared response model is flagged (F-307 H3-7, frob:ticket
T-4109/T-4115).

Before this gate, COV/WIRE gates see a response-model class as referenced
once ANY route uses it -- a route that instead returns a bare `dict`
literal directly is structurally invisible to every reference gate,
because there is no missing reference to notice: the gap is a route that
never referenced a response model in the first place. This is the same
FAMILY as an existing guard-inventory check (a consumer repo's own
SIT-011, which frob itself does not carry): "build an inventory of every
X and flag the ones missing Y" -- here, X is every decorated route
function, Y is a response model on its return.

`route_response_model_gate` enumerates every function decorated with a
CONFIGURABLE route-decorator name pattern (default: any decorator whose
attribute name is one of the conventional HTTP verbs -- `get`, `post`,
`put`, `patch`, `delete` -- called as `@<anything>.<verb>(...)`, e.g.
`@app.get("/x")`/`@router.post("/y")`; not hardcoded to one specific web
framework's exact import path, since frob itself defines no HTTP routes
of its own to anchor a hardcoded pattern against, per T-4115's own
directive) whose body contains a `return {...}` (a `dict` DISPLAY --
`ast.Dict` -- constructed directly in the return statement) rather than
an instantiated typed object.

The concern is scoped precisely to a BARE dict literal in source, not
every dict-shaped return value: `return StatusResponse(...)` (a call, not
a dict display) never fires, and `return {**model.model_dump()}` (a dict
display whose only content is a double-starred unpack of a typed-looking
expression) is treated as a typed-shaped return, not a raw literal --
disclosed as a hand-drawn boundary, not left implicit (T-4115's own "decide
and document" instruction for exactly this case).

WARN-tier (advisory) and waivable with the standard `frob:waive ROUTE001`
mechanism.
"""
# frob:ticket T-4115

from __future__ import annotations

import ast
from pathlib import Path

from frob.findings import Severity, Violation
from frob.gates._tracked_files import tracked_files as _tracked_files
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = ["route_response_model_gate"]

_HTTP_VERBS = frozenset({"get", "post", "put", "patch", "delete"})


def _is_route_decorator(decorator: ast.expr) -> bool:
    """True if `decorator` is `@<anything>.<verb>(...)` for one of the
    conventional HTTP verb method names -- the configurable route-
    decorator pattern T-4115 asks for (a verb-attribute call on ANY
    base object, not one hardcoded framework's exact decorator import),
    matched from the parsed decorator AST, never from source text."""
    if not isinstance(decorator, ast.Call):
        return False
    func = decorator.func
    return isinstance(func, ast.Attribute) and func.attr in _HTTP_VERBS


def _is_typed_shaped_unpack_dict(node: ast.Dict) -> bool:
    """True if `node` (a dict display) is ENTIRELY a double-starred
    unpack of a single expression (`{**expr}`) rather than any literal
    key/value pairs -- the `return {**model.model_dump()}` boundary
    T-4115 asks to decide and document explicitly: this repo treats a
    pure-unpack dict as derived from a typed object, not a raw literal,
    so it does NOT fire, distinct from a dict display that mixes literal
    keys with an unpack (`{**model.model_dump(), "extra": 1}`), which
    still contains a literal key/value pair and DOES fire -- the literal
    pair is exactly the un-typed surface this rule exists to catch."""
    if not node.keys:
        return False
    return all(key is None for key in node.keys)


def _returns_bare_dict_literal(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True if any `return` statement in `func`'s body (non-recursive
    into nested function/class defs, whose own returns belong to a
    different callable) returns a dict display (`ast.Dict`) that is not
    a pure `{**expr}` unpack -- the bare-dict-literal shape T-4115 flags."""
    for node in ast.walk(func):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node is not func
        ):
            continue
        if not isinstance(node, ast.Return):
            continue
        if node.value is None or not isinstance(node.value, ast.Dict):
            continue
        if _is_typed_shaped_unpack_dict(node.value):
            continue
        return True
    return False


def _route_candidates(tree: ast.Module) -> tuple[tuple[str, int], ...]:
    """Every `(function_name, line)` pair for a route-decorated function
    whose body returns a bare dict literal, walked over the whole
    module."""
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not any(_is_route_decorator(dec) for dec in node.decorator_list):
            continue
        if _returns_bare_dict_literal(node):
            found.append((node.name, node.lineno))
    return tuple(found)


# frob:enforces CHK-GATE-ROUTE001
# frob:doc docs/modules/gate-route-response-model.md#route001-t-4115
def route_response_model_gate(root: Path) -> tuple[Violation, ...]:
    """ROUTE001: flag every route-decorated function (`@<obj>.get/post/
    put/patch/delete(...)`) whose body returns a bare `dict` literal
    instead of an instantiated response-model/typed object -- a gap
    invisible to every COV/WIRE reference gate today, since the route IS
    wired and referenced; only its return shape carries no declared
    response model. WARN severity (advisory) and waivable with the
    standard `frob:waive ROUTE001 reason="..."` file-scoped directive."""
    tracked = _tracked_files(root, caller="route_response_model")
    if not tracked:
        return ()

    violations: list[Violation] = []
    for rel in sorted(tracked):
        if not rel.endswith(".py"):
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError:
            _log.debug("route_response_model: %s failed to parse, skipping", rel)
            continue
        for name, lineno in _route_candidates(tree):
            _log.debug(
                "route_response_model: %s:%d route %r returns a bare dict literal",
                rel,
                lineno,
                name,
            )
            violations.append(
                Violation(
                    rule="ROUTE001",
                    severity=Severity.WARN,
                    file=rel,
                    line=lineno,
                    message=(
                        f"ROUTE001: {rel}:{lineno} route {name!r} returns a "
                        "bare dict literal with no declared response model -- "
                        "COV/WIRE reference gates only see a response model "
                        "once a route uses it, so a route that returns a raw "
                        "dict instead never shows up as a gap (F-307 H3-7). "
                        "Instantiate a typed response model instead, or if "
                        "this route deliberately has no response model, add "
                        '`# frob:waive ROUTE001 reason="..."` anywhere in '
                        f"{rel}."
                    ),
                )
            )
    return tuple(violations)
