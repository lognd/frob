"""WEBSEC session/CSRF substrate: one normalized `SessionConfig` reader
(docs/modules/webapp-websec-session.md).

# frob:ticket T-5349

Every WEBSEC session/CSRF rule (cookie `secure`/`httponly`/`samesite`,
idle/absolute session timeout, CSRF middleware presence) needs the same
few facts out of a framework's session configuration, and each framework
spells those facts a different way: Django's settings module-level
assignments plus its `MIDDLEWARE` list, Flask's `app.config[...]`
subscript assignments plus `CSRFProtect(...)` wiring, Express's
`app.use(session({...}))` call-argument object, and Rails'
`config/initializers/session_store.rb` keyword arguments plus a
`protect_from_forgery` call in the controller. Parsing each of those
framework dialects once here into one `SessionConfig` model means every
downstream rule reads `read_session_config(...).secure` (etc.) instead of
re-parsing the same config file with its own bespoke AST walk -- the
exact "produce one normalized model every rule below reads" contract this
ticket's description states, and the shape `frob.webapp._detect`
(T-5302) already established for the framework-detection leaf this
module builds on.

Django/Flask/Express parse through `frob.lang.raw_tree` (T-5302's stated
escape hatch for node-level tree-sitter access), the same single
`get_parser` chokepoint every other `frob.lang` walker uses. Rails'
`.rb` files have no `frob.lang` grammar entry (T-0077's extension table
only wires the extensions each walker needs); parsing them goes through
`tree_sitter_language_pack.get_parser("ruby")` directly instead, the same
underlying grammar loader `frob.lang` itself wraps, scoped to this one
module rather than widening `frob.lang`'s own extension table for a
single WEBSEC-family consumer.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from tree_sitter import Node
from tree_sitter_language_pack import get_parser
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.lang import node_text, raw_tree
from frob.logging import get_logger
from frob.webapp._detect import FrameworkKind

_log = get_logger(__name__)

# Django MIDDLEWARE entry substring that marks CSRF protection as wired
# (dotted path is stable across Django versions; matched as a substring
# rather than an exact list membership since some repos subclass it).
_DJANGO_CSRF_MIDDLEWARE = "CsrfViewMiddleware"

# Express/Node CSRF middleware package names this reader recognizes as
# "CSRF protection is wired" when required and invoked via `app.use(...)`.
_EXPRESS_CSRF_PACKAGES = frozenset({"csurf", "csrf"})


# frob:doc docs/modules/webapp-websec-session.md#sessionconfigerror
class SessionConfigError(ErrorSet):
    """Failure values `read_session_config` can return -- never a bare
    exception (typani `Result` boundary, T-5349)."""

    ConfigFileNotFound = (
        "no recognized session-config file exists under root for this framework"
    )
    ParseFailed = "tree-sitter could not produce a usable tree for the config file"
    UnsupportedFramework = "this FrameworkKind has no session-config reader"


# frob:doc docs/modules/webapp-websec-session.md#sessionconfig
class SessionConfig(BaseModel):
    """One framework's normalized session/CSRF posture: cookie flags,
    session lifetime, and whether CSRF middleware is wired -- the single
    shape every WEBSEC session/CSRF rule reads instead of re-parsing the
    framework's own config file (T-5349).

    Every field defaults to `None`/`False` ("not stated in the config
    file") rather than a framework-specific "secure" default -- a rule
    reading `secure is not True` to flag a missing/explicit-`False`
    cookie flag is exactly the WEBSEC posture (absence is not assumed
    compliant), and collapsing "not stated" into a guessed default here
    would hide that distinction from every rule downstream.
    """

    model_config = {}

    framework: FrameworkKind
    source_path: Path
    secure: bool | None = None
    httponly: bool | None = None
    samesite: str | None = None
    csrf_middleware_present: bool = False
    idle_timeout: int | None = None
    absolute_timeout: int | None = None


def _node_scalar(node: Node | None) -> bool | int | str | None:
    """Decode a tree-sitter literal `node` (bool/int/string/ruby-symbol)
    into the matching Python scalar, or None for any node shape this
    reader does not recognize as a literal.

    frob:ticket T-5349
    """
    if node is None:
        return None
    kind = node.type
    if kind in ("true",):
        return True
    if kind in ("false",):
        return False
    if kind in ("integer", "number"):
        try:
            return int(node_text(node))
        except ValueError:
            return None
    if kind == "string":
        parts = [
            node_text(c)
            for c in node.children
            if c.type in ("string_content", "string_fragment")
        ]
        return "".join(parts)
    if kind == "simple_symbol":
        # Ruby `:strict` -> "strict" (leading colon stripped).
        text = node_text(node)
        return text[1:] if text.startswith(":") else text
    return None


def _bool_scalar(node: Node | None) -> bool | None:
    """`_node_scalar(node)` narrowed to `bool | None` (a `SessionConfig`
    boolean field's own type) -- a non-bool literal (e.g. a stray
    integer under a boolean-shaped key) decodes to `None` rather than a
    type error, since that shape means the config file did not actually
    set this flag the way this reader expects.

    frob:ticket T-5349
    """
    value = _node_scalar(node)
    return value if isinstance(value, bool) else None


def _str_scalar(node: Node | None) -> str | None:
    """`_node_scalar(node)` narrowed to `str | None` (a `SessionConfig`
    string field's own type).

    frob:ticket T-5349
    """
    value = _node_scalar(node)
    return value if isinstance(value, str) else None


def _int_scalar(node: Node | None) -> int | None:
    """`_node_scalar(node)` narrowed to `int | None` (a `SessionConfig`
    integer field's own type) -- `bool` is excluded even though Python's
    `bool` is an `int` subclass, since a timeout field seeing `True`/
    `False` means this reader read the wrong key, not a real timeout.

    frob:ticket T-5349
    """
    value = _node_scalar(node)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


# frob:invariant terminates reason="recurses only into a direct tree-sitter child one \
# edge below the current node; a lexical prover cannot see that the child accessor is \
# structurally smaller without dataflow" measure="tree-sitter AST depth under node, \
# finite per parse"
def _walk(node: Node):  # noqa: ANN201 -- generator of tree_sitter.Node
    """Depth-first walk of every descendant of `node`, `node` included.

    frob:ticket T-5349
    """
    yield node
    for child in node.children:
        yield from _walk(child)


def _collect_pairs(root: Node) -> dict[str, Node]:
    """Every `key: value`-shaped node reachable under `root` (JS object
    `pair`, Ruby hash `pair`/keyword argument) keyed by its decoded key
    text, last occurrence wins.

    frob:ticket T-5349
    """
    pairs: dict[str, Node] = {}
    for node in _walk(root):
        if node.type != "pair":
            continue
        key_node = node.child_by_field_name("key")
        value_node = node.child_by_field_name("value")
        if key_node is None or value_node is None:
            continue
        key_text = node_text(key_node).strip("\"':")
        pairs[key_text] = value_node
    return pairs


def _collect_python_assignments(root: Node) -> dict[str, Node]:
    """Every module-level `NAME = value` and `obj.config['NAME'] = value`
    assignment reachable under `root`, keyed by `NAME`.

    frob:ticket T-5349
    """
    out: dict[str, Node] = {}
    for node in _walk(root):
        if node.type != "assignment":
            continue
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        if left is None or right is None:
            continue
        if left.type == "identifier":
            out[node_text(left)] = right
        elif left.type == "subscript":
            index = left.child_by_field_name("subscript")
            if index is not None and index.type == "string":
                key = _node_scalar(index)
                if isinstance(key, str):
                    out[key] = right
    return out


def _call_identifiers(root: Node) -> frozenset[str]:
    """Every bare call-target identifier name reachable under `root`
    (`call_expression`/`call` nodes) -- used to detect CSRF-middleware
    invocations (`csurf()`, `protect_from_forgery`) without a full
    call-graph resolver.

    frob:ticket T-5349
    """
    names: set[str] = set()
    for node in _walk(root):
        if node.type not in ("call_expression", "call"):
            continue
        target = node.child_by_field_name("function") or (
            node.children[0] if node.children else None
        )
        if target is not None:
            names.add(node_text(target))
    return frozenset(names)


def _find_first(root: Path, *names: str) -> Path | None:
    """The first of `names` that exists directly under `root`, or None.

    frob:ticket T-5349
    """
    for name in names:
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def _read_django(root: Path) -> Result[SessionConfig, SessionConfigError]:
    """Read Django's `settings.py` (repo root, or one level under a
    project package directory) for `SESSION_COOKIE_*`/`CSRF_COOKIE_*`
    assignments and a `CsrfViewMiddleware` entry in `MIDDLEWARE`.

    frob:ticket T-5349
    """
    path = _find_first(root, "settings.py")
    if path is None:
        for candidate in sorted(root.glob("*/settings.py")):
            path = candidate
            break
    if path is None:
        _log.info("websec_session_config: no Django settings.py found under %s", root)
        return Err(SessionConfigError.ConfigFileNotFound)
    parsed = raw_tree(path)
    if parsed.is_err:
        _log.warning(
            "websec_session_config: Django settings.py parse failed at %s", path
        )
        return Err(SessionConfigError.ParseFailed)
    tree, _source, _language = parsed.danger_ok
    assignments = _collect_python_assignments(tree.root_node)
    middleware_node = assignments.get("MIDDLEWARE")
    middleware_text = node_text(middleware_node)
    return Ok(
        SessionConfig(
            framework=FrameworkKind.DJANGO,
            source_path=path,
            secure=_bool_scalar(assignments.get("SESSION_COOKIE_SECURE")),
            httponly=_bool_scalar(assignments.get("SESSION_COOKIE_HTTPONLY")),
            samesite=_str_scalar(assignments.get("SESSION_COOKIE_SAMESITE")),
            csrf_middleware_present=_DJANGO_CSRF_MIDDLEWARE in middleware_text,
            idle_timeout=None,
            absolute_timeout=_int_scalar(assignments.get("SESSION_COOKIE_AGE")),
        )
    )


def _read_flask(root: Path) -> Result[SessionConfig, SessionConfigError]:
    """Read Flask's app-factory module (`app.py`/`wsgi.py`) for
    `app.config['SESSION_COOKIE_*']` subscript assignments and a
    `CSRFProtect(...)` call.

    frob:ticket T-5349
    """
    path = _find_first(root, "app.py", "wsgi.py")
    if path is None:
        _log.info("websec_session_config: no Flask app.py/wsgi.py found under %s", root)
        return Err(SessionConfigError.ConfigFileNotFound)
    parsed = raw_tree(path)
    if parsed.is_err:
        _log.warning("websec_session_config: Flask app.py parse failed at %s", path)
        return Err(SessionConfigError.ParseFailed)
    tree, _source, _language = parsed.danger_ok
    assignments = _collect_python_assignments(tree.root_node)
    calls = _call_identifiers(tree.root_node)
    return Ok(
        SessionConfig(
            framework=FrameworkKind.FLASK,
            source_path=path,
            secure=_bool_scalar(assignments.get("SESSION_COOKIE_SECURE")),
            httponly=_bool_scalar(assignments.get("SESSION_COOKIE_HTTPONLY")),
            samesite=_str_scalar(assignments.get("SESSION_COOKIE_SAMESITE")),
            csrf_middleware_present="CSRFProtect" in calls,
            idle_timeout=_int_scalar(assignments.get("PERMANENT_SESSION_LIFETIME")),
            absolute_timeout=None,
        )
    )


def _read_express(root: Path) -> Result[SessionConfig, SessionConfigError]:
    """Read an Express app module (`app.js`/`server.js`/`index.js`) for
    the `app.use(session({...}))` call's `cookie` object and a
    `csurf()`/`csrf()` middleware call.

    frob:ticket T-5349
    """
    path = _find_first(root, "app.js", "server.js", "index.js")
    if path is None:
        _log.info(
            "websec_session_config: no Express app/server/index.js found under %s",
            root,
        )
        return Err(SessionConfigError.ConfigFileNotFound)
    parsed = raw_tree(path)
    if parsed.is_err:
        _log.warning("websec_session_config: Express app.js parse failed at %s", path)
        return Err(SessionConfigError.ParseFailed)
    tree, _source, _language = parsed.danger_ok
    top_pairs = _collect_pairs(tree.root_node)
    cookie_node = top_pairs.get("cookie")
    cookie_pairs = _collect_pairs(cookie_node) if cookie_node is not None else {}
    calls = _call_identifiers(tree.root_node)
    # `framework` is a placeholder here (Express has no dedicated
    # `FrameworkKind` member -- T-5302 detects a bare Node server tree as
    # `VITE`); `read_session_config` overwrites it with the caller-supplied
    # `FrameworkKind` before returning.
    return Ok(
        SessionConfig(
            framework=FrameworkKind.VITE,
            source_path=path,
            secure=_bool_scalar(cookie_pairs.get("secure")),
            httponly=_bool_scalar(cookie_pairs.get("httpOnly")),
            samesite=_str_scalar(cookie_pairs.get("sameSite")),
            csrf_middleware_present=bool(calls & _EXPRESS_CSRF_PACKAGES),
            idle_timeout=_int_scalar(cookie_pairs.get("maxAge")),
            absolute_timeout=None,
        )
    )


def _read_rails(root: Path) -> Result[SessionConfig, SessionConfigError]:
    """Read Rails' `config/initializers/session_store.rb` for its
    `session_store` keyword arguments, and
    `app/controllers/application_controller.rb` for a
    `protect_from_forgery` call.

    frob:ticket T-5349
    """
    path = root / "config" / "initializers" / "session_store.rb"
    if not path.is_file():
        _log.info(
            "websec_session_config: no Rails session_store.rb found under %s", root
        )
        return Err(SessionConfigError.ConfigFileNotFound)
    ruby_parser = get_parser("ruby")
    try:
        source = path.read_bytes()
    except OSError:
        _log.warning(
            "websec_session_config: Rails session_store.rb unreadable at %s", path
        )
        return Err(SessionConfigError.ParseFailed)
    tree = ruby_parser.parse(source)
    pairs = _collect_pairs(tree.root_node)

    csrf_present = False
    controller_path = root / "app" / "controllers" / "application_controller.rb"
    if controller_path.is_file():
        try:
            controller_source = controller_path.read_bytes()
        except OSError:
            controller_source = b""
        if controller_source:
            controller_tree = ruby_parser.parse(controller_source)
            csrf_present = "protect_from_forgery" in _call_identifiers(
                controller_tree.root_node
            )

    return Ok(
        SessionConfig(
            framework=FrameworkKind.RAILS,
            source_path=path,
            secure=_bool_scalar(pairs.get("secure")),
            httponly=_bool_scalar(pairs.get("httponly")),
            samesite=_str_scalar(pairs.get("same_site")),
            csrf_middleware_present=csrf_present,
            idle_timeout=_int_scalar(pairs.get("expire_after")),
            absolute_timeout=None,
        )
    )


_READERS = {
    FrameworkKind.DJANGO: _read_django,
    FrameworkKind.FLASK: _read_flask,
    FrameworkKind.RAILS: _read_rails,
}


# frob:doc docs/modules/webapp-websec-session.md#read_session_config
def read_session_config(
    root: Path, framework: FrameworkKind
) -> Result[SessionConfig, SessionConfigError]:
    """Parse `framework`'s session/CSRF config file under `root` into one
    normalized `SessionConfig` every WEBSEC session/CSRF rule reads
    instead of re-parsing the file itself (T-5349).

    Dispatches on `framework` (from `frob.webapp._detect.detect_frameworks`,
    T-5302 -- this reader never re-detects); a `FrameworkKind` with no
    reader registered (`FASTAPI`, `LARAVEL`, `SVELTEKIT`, `ASTRO`,
    `NEXTJS`) returns `Err(UnsupportedFramework)` since those frameworks
    have no single canonical session-config file this reader can locate
    the same way Django/Flask/Rails do; a Node/Express tree (detected as
    `VITE` by T-5302, since Express itself has no dedicated
    `FrameworkKind`) is read via `_read_express`.
    """
    if framework == FrameworkKind.VITE:
        result = _read_express(root)
    else:
        reader = _READERS.get(framework)
        if reader is None:
            _log.info("websec_session_config: no reader registered for %s", framework)
            return Err(SessionConfigError.UnsupportedFramework)
        result = reader(root)
    if result.is_err:
        return result
    config = result.danger_ok
    if config.framework != framework:
        config = config.model_copy(update={"framework": framework})
    _log.info(
        "websec_session_config: read %s config from %s (secure=%s httponly=%s csrf=%s)",
        framework,
        config.source_path,
        config.secure,
        config.httponly,
        config.csrf_middleware_present,
    )
    return Ok(config)
