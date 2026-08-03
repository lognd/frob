"""SEC110: Python `os.environ`/`os.getenv` env-var access scan (T-0207
family 3) -- T-1076 split of `frob.gates._pii_structural`."""

from __future__ import annotations

import ast

from frob.gates._models import Severity, Violation
from frob.logging import get_logger

from ._declared_surface import _EMPTY_DECLARED_SURFACE, _DeclaredSurface
from ._node_index import _build_node_index, _NodeIndex
from ._python_fields import _literal_str

_log = get_logger(__name__)

#: Attribute/function names an env-access call site's dotted path may end
#: in, for `_is_env_access` (corpus family 3: "os.environ[...]/os.getenv/
#: load_dotenv() ... process.env, std::env::var" -- Python subset here).
_ENV_CALL_ATTRS = frozenset({"getenv"})

#: T-0353: known-non-secret env var names -- process/terminal/platform
#: plumbing that definitionally carries no secret (display server socket
#: names, terminal capability flags, interpreter/tooling paths, CI/test
#: markers). A read of a NON-allowlisted var still fires SEC110; this is a
#: precision narrowing, not a blanket mute -- every entry here is a var
#: this codebase actually reads at a site with no secret-shaped payload.
_ENV_VAR_ALLOWLIST = frozenset(
    {
        "DISPLAY",
        "WAYLAND_DISPLAY",
        "TERM",
        "NO_COLOR",
        "FORCE_COLOR",
        "PATH",
        "LD_LIBRARY_PATH",
        "HOME",
        "LANG",
        "TZ",
        "CI",
        "PYTEST_CURRENT_TEST",
        "VIRTUAL_ENV",
        "PYO3_PYTHON",
    }
)

#: Prefix-matched allowlist entries (`XDG_*` -- base-directory-spec vars,
#: all plain filesystem-location config, never a secret).
_ENV_VAR_ALLOWLIST_PREFIXES = ("XDG_",)


def _is_allowlisted_env_var(name: str) -> bool:
    """Whether `name` is a known-non-secret env var (`_ENV_VAR_ALLOWLIST`
    exact match or `_ENV_VAR_ALLOWLIST_PREFIXES` prefix match) -- T-0353."""
    if name in _ENV_VAR_ALLOWLIST:
        return True
    return any(name.startswith(prefix) for prefix in _ENV_VAR_ALLOWLIST_PREFIXES)


def _subscript_key(node: ast.Subscript) -> ast.expr:
    """The key expression of `node` -- `Subscript.slice` is already the
    bare key expr on the Python 3.9+ AST this repo targets (no legacy
    `ast.Index` wrapper to unwrap)."""
    return node.slice


def _dotted_prefix(node: ast.expr) -> str | None:
    """The dotted-name text of an `Attribute`/`Name` chain (`os.environ` ->
    `"os.environ"`), or `None` for anything else -- a small, local
    unparse rather than pulling in `ast.unparse` (stdlib 3.9+; kept local
    so the exact match surface is explicit and testable in isolation)."""
    parts: list[str] = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    else:
        return None
    return ".".join(reversed(parts))


def _is_environ_subscript(node: ast.Subscript) -> bool:
    """`os.environ["X"]` / `environ["X"]` (direct-import form)."""
    dotted = _dotted_prefix(node.value)
    return dotted in ("os.environ", "environ")


def _is_env_call(node: ast.Call) -> bool:
    """`os.getenv(...)` / `getenv(...)` (direct-import form) / `os.environ.
    get(...)` / `environ.get(...)`."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id in _ENV_CALL_ATTRS
    if isinstance(func, ast.Attribute):
        if func.attr in _ENV_CALL_ATTRS:
            return True
        if func.attr == "get":
            dotted = _dotted_prefix(func.value)
            return dotted in ("os.environ", "environ")
    return False


def _sec110_violation(rel_path: str, lineno: int, site: str) -> Violation:
    """The SEC110 `Violation` for one unmapped env-access site."""
    _log.warning("SEC110: %s:%d env access %s", rel_path, lineno, site)
    return Violation(
        rule="SEC110",
        severity=Severity.WARN,
        file=rel_path,
        line=lineno,
        message=(
            f"SEC110: {rel_path}:{lineno} reads {site} -- an env-var read is "
            f"a secret-source observation; map it to a declared std.secrets "
            f'node (T-0082), or `frob:waive SEC110 reason="..."` if this '
            f"var carries no secret"
        ),
    )


# frob:waive AFFECT001 reason="T-1209 adds an optional internal _index perf kwarg \
# (defaults to computing the same walk it always did); the documented SEC110 \
# behavior/output is unchanged (verified byte-identical before/after against this \
# repo's own tree), so docs/modules/gates.md#public-api needs no update"
def _scan_python_env_access(
    tree: ast.Module,
    rel_path: str,
    declared: _DeclaredSurface = _EMPTY_DECLARED_SURFACE,
    *,
    _index: _NodeIndex | None = None,
) -> tuple[Violation, ...]:
    """SEC110 over every `os.environ[...]`/`os.environ.get(...)`/
    `os.getenv(...)` call/subscript site in `tree` (module docstring:
    family 3, env/secret sources), joined against `declared`'s
    Secret-clearance code binding (T-0351) -- a file already code-bound to
    a declared std.secrets node is discharged, not merely waivable.
    `_index` (T-1209 perf): see `_scan_python_fields`'s docstring --
    `index._ordered(index.subscripts, index.calls)` recovers the same
    `Subscript`/`Call` document-order interleaving the original single
    `ast.walk` loop produced, so finding order is unchanged."""
    if declared._has_secret(rel_path):
        return ()
    index = _index if _index is not None else _build_node_index(tree)
    violations: list[Violation] = []
    for node in index._ordered(index.subscripts, index.calls):
        if isinstance(node, ast.Subscript) and _is_environ_subscript(node):
            var_name = _literal_str(_subscript_key(node))
            if var_name is not None and _is_allowlisted_env_var(var_name):
                continue
            violations.append(
                _sec110_violation(rel_path, node.lineno, "os.environ[...]")
            )
        elif isinstance(node, ast.Call) and _is_env_call(node):
            var_name = _literal_str(node.args[0]) if node.args else None
            if var_name is not None and _is_allowlisted_env_var(var_name):
                continue
            site = _dotted_prefix(node.func) or getattr(node.func, "attr", "getenv")
            violations.append(_sec110_violation(rel_path, node.lineno, f"{site}(...)"))
    return tuple(violations)
