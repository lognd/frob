"""WEBSEC401: route/handler owner-check substrate (T-5356).

Per-framework route-table extraction (Flask/FastAPI/Django route
decorators/`request`-taking view functions; Rails controller actions)
plus a body scan for an ORM lookup/filter call that is never correlated,
anywhere in the same handler body, with the authenticated user's own
identity (`current_user`/`request.user`/`g.user`). This is a documented
HEURISTIC, not a sound analysis -- same posture as PERF008's loop-
invariant-effect heuristic (`src/frob/perf/_cache_effects.py` module
docstring): over-recall by design, and the fix for a false positive is a
reasoned `frob:waive WEBSEC401 reason="..."`, not a smarter parser.

WHY THIS MODULE TAKES A PARSED `Node`, NOT A `Path`: `[arch.layering]`
(`frob.toml`) makes `webapp` a leaf layer with no allowed imports of its
own (same table T-5302 left this module's sibling `_detect.py` in, and
T-5313's `_a11y_substrate.py` documents identically) -- this module
therefore never imports `frob.lang` itself. The eventual `WEBSEC401` gate
rule (a later leaf, living under `frob.gates`, which IS allowed to import
both `lang` and `webapp`) calls `frob.lang.raw_tree`/`parse_file` itself
and hands this module the resulting `tree_sitter.Node` root (python) or
raw source text (Rails, see below) plus the file path; this module only
ever walks what it is given, and never imports `frob.gates` either (the
`Violation`/`Severity` wrapping is that later leaf's job, not this one's)
-- it returns its own `AuthzFinding` model instead.

Language coverage is bounded by `frob.lang`'s grammar table (T-0077):
Flask/FastAPI/Django route through python's tree-sitter grammar (the
caller's job to parse; see above). Rails has NO tree-sitter grammar in
this repo at all, so `.rb` controller actions are matched with a text-
regex heuristic instead of a `Node` walk -- same "text rule over a file a
real grammar cannot reach" posture T-5307's Jinja/ERB sink rules already
use; `scan_rails_controller` takes raw source TEXT, not a `Node`, for
exactly that reason. Express (JavaScript) is OUT of scope for this
walker: T-5302's `FrameworkKind` has no member for it (`nextjs/vite/
django/flask/fastapi/rails/laravel/sveltekit/astro` only), and adding one
is a `frob.webapp._detect` change outside this ticket's declared scope --
filed as a follow-up rather than silently widened into (T-5356 done-
report).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pydantic import BaseModel
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.logging import get_logger

if TYPE_CHECKING:
    from tree_sitter import Node

_log = get_logger(__name__)

__all__ = [
    "AUTH_IDENTIFIER_NAMES",
    "AuthzFinding",
    "AuthzSubstrateError",
    "scan_python_handlers",
    "scan_rails_controller",
]


# frob:doc docs/modules/webapp-websec-authz.md#errors
class AuthzSubstrateError(ErrorSet):
    """Failure values `scan_python_handlers` can return.

    frob:ticket T-5356
    """

    UnsupportedLanguage = (
        "language is not python -- scan_rails_controller is the .rb entry point"
    )


#: The authenticated-user identifiers this heuristic accepts as evidence a
#: handler correlates its ORM lookup with the caller's own identity --
#: the exact vocabulary named in T-5356's ticket body.
AUTH_IDENTIFIER_NAMES: frozenset[str] = frozenset(
    {"current_user", "request.user", "g.user"}
)

_AUTH_IDENT_RE = re.compile(r"\b(current_user|request\.user|g\.user)\b")

#: ORM lookup/filter call shapes this heuristic treats as "fetches a
#: specific record" -- the call a missing owner-correlation makes unsafe.
_ORM_LOOKUP_RE = re.compile(
    r"\.(get|filter|filter_by|where|find|find_by)\s*\(|get_object_or_404\s*\("
)

#: Flask/FastAPI decorator shapes: `@app.route(...)`, `@bp.get(...)`,
#: `@router.post(...)`, etc. -- any `.<verb>(` call used as a decorator.
_ROUTE_DECORATOR_RE = re.compile(r"@\w+\.(route|get|post|put|patch|delete)\s*\(")

_RAILS_ACTION_RE = re.compile(r"^\s*def\s+(\w+)\b", re.MULTILINE)
_RAILS_CLASS_RE = re.compile(r"class\s+\w+Controller\b")


# frob:doc docs/modules/webapp-websec-authz.md#authzfinding
class AuthzFinding(BaseModel):
    """One handler whose ORM lookup/filter call is never correlated with
    an authenticated-user identifier -- the raw match; a caller under
    `frob.gates` wraps this in a `Violation` with rule/severity.

    frob:ticket T-5356
    """

    file: str
    line: int
    handler: str


def _decorator_text(decorated: Node) -> str:
    """The source text of every decorator attached to `decorated`
    (a `decorated_definition` node), concatenated -- empty for a plain
    (undecorated) `function_definition`."""
    if decorated.type != "decorated_definition":
        return ""
    parts: list[str] = []
    for child in decorated.children:
        if child.type == "decorator":
            parts.append((child.text or b"").decode("utf-8", errors="ignore"))
    return "\n".join(parts)


def _is_handler_candidate(decorator_text: str, func_node: Node, source: bytes) -> bool:
    """True if `func_node` looks like a Flask/FastAPI route handler (a
    route-shaped decorator) or a Django view (first parameter named
    `request`) -- the gate that keeps this heuristic off ordinary helper
    functions the walker would otherwise flag by accident."""
    if _ROUTE_DECORATOR_RE.search(decorator_text):
        return True
    params = func_node.child_by_field_name("parameters")
    if params is None:
        return False
    params_text = source[params.start_byte : params.end_byte].decode(
        "utf-8", errors="ignore"
    )
    return bool(re.match(r"\(\s*self\s*,\s*request\b|\(\s*request\b", params_text))


def _function_body_text(func_node: Node, source: bytes) -> str:
    """The raw source text of `func_node`'s body block, with a leading
    docstring statement (if any) excluded -- a docstring's own PROSE
    ("...no request.user reference anywhere...") would otherwise satisfy
    `_AUTH_IDENT_RE` by accident and silently suppress a real finding."""
    body = func_node.child_by_field_name("body")
    if body is None:
        return ""
    children = list(body.children)
    start = body.start_byte
    if children:
        first = children[0]
        is_docstring = first.type == "expression_statement" and any(
            c.type == "string" for c in first.children
        )
        if is_docstring:
            start = first.end_byte
    return source[start : body.end_byte].decode("utf-8", errors="ignore")


def _function_name(func_node: Node) -> str:
    """`func_node`'s declared name, or "<anonymous>" if the grammar gave none."""
    name_node = func_node.child_by_field_name("name")
    if name_node is None:
        return "<anonymous>"
    return (name_node.text or b"").decode("utf-8", errors="ignore")


# frob:doc docs/modules/webapp-websec-authz.md#scan_python_handlers
# frob:ticket T-5356
def scan_python_handlers(
    path: str, root: Node, source: bytes, language: str
) -> Result[tuple[AuthzFinding, ...], AuthzSubstrateError]:
    """WEBSEC401 findings across every Flask/FastAPI/Django-shaped
    handler in an already-parsed python `root` (caller owns the
    `frob.lang.raw_tree` call, see module docstring). `Err(
    UnsupportedLanguage)` for any `language` other than "python"."""
    if language != "python":
        _log.debug(
            "scan_python_handlers: unsupported language %s at %s", language, path
        )
        return Err(AuthzSubstrateError.UnsupportedLanguage)
    hits: list[AuthzFinding] = []
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type in ("module", "block"):
            stack.extend(node.children)
            continue
        if node.type in ("decorated_definition", "function_definition"):
            func_node = node
            decorator_text = ""
            if node.type == "decorated_definition":
                decorator_text = _decorator_text(node)
                func_node = next(
                    (c for c in node.children if c.type == "function_definition"),
                    None,
                )
                if func_node is None:
                    continue
            if not _is_handler_candidate(decorator_text, func_node, source):
                stack.extend(node.children)
                continue
            body_text = _function_body_text(func_node, source)
            if _ORM_LOOKUP_RE.search(body_text) and not _AUTH_IDENT_RE.search(
                body_text
            ):
                line = func_node.start_point[0] + 1
                hits.append(
                    AuthzFinding(
                        file=path, line=line, handler=_function_name(func_node)
                    )
                )
            continue
        stack.extend(node.children)
    _log.info("scan_python_handlers: %s -> %d finding(s)", path, len(hits))
    return Ok(tuple(hits))


# frob:doc docs/modules/webapp-websec-authz.md#scan_rails_controller
# frob:ticket T-5356
def scan_rails_controller(path: str, text: str) -> tuple[AuthzFinding, ...]:
    """WEBSEC401 findings across a Rails controller file's source TEXT:
    `def <action>` bodies (split on the next `def`/end-of-file -- a text-
    regex heuristic, not a parser; see module docstring) that reach an
    ORM lookup but never mention `current_user`/`request.user`/`g.user`.
    `()` for any file that is not a `...Controller` class body."""
    if not _RAILS_CLASS_RE.search(text):
        return ()
    hits: list[AuthzFinding] = []
    matches = list(_RAILS_ACTION_RE.finditer(text))
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[start:end]
        if _ORM_LOOKUP_RE.search(body) and not _AUTH_IDENT_RE.search(body):
            line = text.count("\n", 0, match.start()) + 1
            hits.append(AuthzFinding(file=path, line=line, handler=match.group(1)))
    _log.info("scan_rails_controller: %s -> %d finding(s)", path, len(hits))
    return tuple(hits)
