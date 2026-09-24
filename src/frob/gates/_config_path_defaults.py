"""CONFIGPATH001: a pydantic `Field(default=...)` on a `*_path`-shaped
field whose default is a relative path is flagged (F-307 H3-5,
frob:ticket T-4109/T-4114).

No gate before this one compared an `AppConfig` default filesystem path
against the target deployment's filesystem, because there is no
deployment manifest on `main` to compare against (T-4109's own framing).
The proposed rule is deliberately cheaper than a real deployment-manifest
comparison: a relative default on a config path field silently resolves
against whatever the process's cwd happens to be at start time -- a real
deployment footgun independent of any manifest, and decidable purely from
the parsed field annotation and default (T-4114's own directive: decide
from parsed symbols, never lexically/textually).

`config_path_default_gate` enumerates every pydantic `Field(...)` call
(this repo's own `App`/`AppConfig` pattern, `~/.claude/refs/python-app.md`)
assigned to a class attribute whose:

  - name ends in `_path`, OR whose annotation is `Path`/`pathlib.Path`
    (T-4114's own "check which signal is more reliable" -- both are
    checked, since a `*_path`-named field with a non-`Path` annotation
    (e.g. `str`) is exactly the shape `App`/`AppConfig` config classes use
    in this repo, and a `Path`-annotated field need not be named `*_path`)
  - `default=` is a string or `Path(...)`-literal value that is not
    absolute and is not `None`

WARN-tier (advisory, matching this repo's own posture for a lint that
cannot always be certain -- some defaults are deliberately relative to a
package root) and waivable with the standard `frob:waive CONFIGPATH001`
mechanism.
"""
# frob:ticket T-4114

from __future__ import annotations

import ast
from pathlib import Path, PurePosixPath, PureWindowsPath

from frob.findings import Severity, Violation
from frob.gates._tracked_files import tracked_files as _tracked_files
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = ["config_path_default_gate"]


def _is_path_like_relative_literal(node: ast.expr) -> str | None:
    """The relative path string a `default=` AST node encodes, or `None`
    if the node is not a string/`Path(...)`-literal default, is `None`
    itself, or the literal path it encodes is already absolute (POSIX or
    Windows-style, since a config's deployment target is not assumed to
    be POSIX-only) -- the exact "not absolute and not None" test T-4114
    specifies, decided from the parsed AST node, never from source text."""
    value: str | None = None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        value = node.value
    elif (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Path"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ):
        value = node.args[0].value
    elif (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "Path"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ):
        value = node.args[0].value
    if value is None:
        return None
    # T-5478: `Path(value).is_absolute()` is platform-native (WindowsPath
    # on win32) and `PureWindowsPath(value).is_absolute()` covers a
    # Windows-shaped literal on any host, but NEITHER recognizes a
    # POSIX-style absolute literal (`/abs/dir/state.json`) when this
    # gate runs on win32 -- `PureWindowsPath` requires a drive/UNC root
    # for `is_absolute()`, so a bare-leading-slash path reads as
    # "relative" there even though it is a real absolute path on the
    # platform the source literal actually targets. Check all three so
    # the gate's answer does not depend on which OS `frob check` runs on.
    if (
        Path(value).is_absolute()
        or PureWindowsPath(value).is_absolute()
        or PurePosixPath(value).is_absolute()
    ):
        return None
    return value


def _annotation_is_path(annotation: ast.expr | None) -> bool:
    """True if a field's type annotation is (or contains, for `X | None`
    / `Optional[X]`) `Path` or `pathlib.Path` -- the annotation-based
    signal T-4114 asks to check alongside the `*_path` naming convention."""
    if annotation is None:
        return False
    if isinstance(annotation, ast.Name):
        return annotation.id == "Path"
    if isinstance(annotation, ast.Attribute):
        return annotation.attr == "Path"
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        return _annotation_is_path(annotation.left) or _annotation_is_path(
            annotation.right
        )
    if isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name):
        if annotation.value.id == "Optional":
            return _annotation_is_path(annotation.slice)
    return False


def _field_default_node(call: ast.Call) -> ast.expr | None:
    """The `default=` keyword's value node from a `Field(...)` call, or
    `None` if the call has no `default=` keyword at all (a required
    field -- T-4114's own "no default -- must stay quiet" case)."""
    for kw in call.keywords:
        if kw.arg == "default":
            return kw.value
    return None


def _field_candidates(
    tree: ast.Module,
) -> tuple[tuple[str, int, str], ...]:
    """Every `(field_name, line, relative_default)` triple for a class
    attribute assigned `Field(default=<relative literal>)` whose name ends
    in `_path` or whose annotation is `Path`-shaped, walked over the whole
    module (pydantic `BaseModel` subclasses are not distinguished from
    other classes here -- a `Field(...)` call with this exact shape is
    pydantic's own call convention regardless of which class body it
    sits in, and false-scoping to only classes literally named
    `*Config`/subclassing `BaseModel` by name would miss an aliased
    import or a mixin base, the same catalogued-is-not-enforced gap this
    ticket exists to close)."""
    found: list[tuple[str, int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.AnnAssign):
            continue
        if not isinstance(node.target, ast.Name):
            continue
        if node.value is None or not isinstance(node.value, ast.Call):
            continue
        call = node.value
        is_field_call = (
            isinstance(call.func, ast.Name) and call.func.id == "Field"
        ) or (isinstance(call.func, ast.Attribute) and call.func.attr == "Field")
        if not is_field_call:
            continue
        name = node.target.id
        name_signal = name.endswith("_path")
        annotation_signal = _annotation_is_path(node.annotation)
        if not (name_signal or annotation_signal):
            continue
        default_node = _field_default_node(call)
        if default_node is None:
            continue
        relative = _is_path_like_relative_literal(default_node)
        if relative is None:
            continue
        found.append((name, node.lineno, relative))
    return tuple(found)


# frob:enforces CHK-GATE-CONFIGPATH001
# frob:doc docs/modules/gate-config-path-defaults.md#configpath001-t-4114
def config_path_default_gate(root: Path) -> tuple[Violation, ...]:
    """CONFIGPATH001: flag every pydantic `Field(default=...)` on a
    `*_path`-named or `Path`-annotated field whose default value is a
    relative path -- a real deployment footgun (the process cwd at start
    time, not a fixed location, decides where it resolves) that no
    reference/wire/coverage gate notices today because the field IS
    referenced and IS wired up; only its literal default value is wrong.
    WARN severity (advisory posture, matching this repo's other
    can't-always-be-certain lints -- some defaults are deliberately
    relative to a package root) and waivable with the standard
    `frob:waive CONFIGPATH001 reason="..."` file-scoped directive."""
    tracked = _tracked_files(root, caller="config_path_defaults")
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
            _log.debug("config_path_defaults: %s failed to parse, skipping", rel)
            continue
        for name, lineno, relative in _field_candidates(tree):
            _log.debug(
                "config_path_defaults: %s:%d field %r has relative default %r",
                rel,
                lineno,
                name,
                relative,
            )
            violations.append(
                Violation(
                    rule="CONFIGPATH001",
                    severity=Severity.WARN,
                    file=rel,
                    line=lineno,
                    message=(
                        f"CONFIGPATH001: {rel}:{lineno} field {name!r} has a "
                        f"relative default path {relative!r} -- a config path "
                        "default should be absolute or None, since a relative "
                        "default silently resolves against whatever the "
                        "process's cwd happens to be at start time (a real "
                        "deployment footgun, F-307 H3-5). If this default is "
                        "deliberately relative to a package root, add "
                        '`# frob:waive CONFIGPATH001 reason="..."` anywhere '
                        f"in {rel}."
                    ),
                )
            )
    return tuple(violations)
