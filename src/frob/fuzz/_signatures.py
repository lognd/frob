"""Best-effort dynamic import of a Python target's parameter types (FUZZ002 input).

`frob.graph` never inspects Python's own type system -- `RawSymbol` carries
token streams, not `type` objects, so FUZZ002 (a param type has no
generator) needs a live import to get real types to hand to `resolve`.
That import is inherently impure and inherently Python-only, so it lives
here as a clearly separate, best-effort step: any failure returns `None`
rather than raising, and FUZZ002 treats `None` as "could not introspect"
(skipped, not a violation) rather than a false positive.
"""

# frob:waive TEST005 reason="module line coverage 80.3%, debt T-0160"

from __future__ import annotations

import importlib
import inspect
import sys
import typing
from collections.abc import Callable
from pathlib import Path, PurePosixPath

from frob.logging import get_logger

_log = get_logger(__name__)

_SELF_PARAMS = frozenset({"self", "cls"})


def _module_name(path: str) -> str | None:
    """The dotted import name for a `src/...`-relative `.py` path, or `None`."""
    parts = PurePosixPath(path).parts
    if parts and parts[0] == "src":
        parts = parts[1:]
    if not parts or not parts[-1].endswith(".py"):
        return None
    stem = PurePosixPath(parts[-1]).stem
    parts = (*parts[:-1], stem)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return None
    return ".".join(parts)


def _resolve_attr(module: object, qualname: str) -> object | None:
    """Walk a dotted qualname off `module`, returning `None` on any miss."""
    obj: object = module
    for part in qualname.split("."):
        obj = getattr(obj, part, None)
        if obj is None:
            return None
    return obj


# frob:doc docs/modules/fuzz.md#implementation-notes
# frob:waive TEST005 reason="resolve_param_types 75.0% branch cover, debt T-0160"
def resolve_param_types(root: Path, ref: str) -> tuple[type, ...] | None:
    """Best-effort: the non-`self`/`cls` parameter types of the Python symbol `ref`.

    `ref` is a `path::qualname` symref (`SymbolId.__str__`). Returns `None`
    if `ref` is not Python, the module fails to import, the qualname does
    not resolve to a callable, or any annotation cannot be evaluated --
    never raises.
    """
    parsed_ref = _parse_python_ref(ref)
    if parsed_ref is None:
        return None
    path_str, qualname = parsed_ref

    module = _import_ref_module(root, path_str)
    if module is None:
        return None
    target = _resolve_callable(module, qualname)
    if target is None:
        return None

    hints = _resolve_hints(target, ref)
    if hints is None:
        return None
    return _annotated_types_for_target(target, hints, ref)


def _annotated_types_for_target(
    target: Callable[..., object], hints: dict[str, type], ref: str
) -> tuple[type, ...] | None:
    """`target`'s inspectable signature, resolved into annotated param
    types via `hints`; `None` if `target` has no inspectable signature."""
    try:
        sig = inspect.signature(target)
    except (TypeError, ValueError) as exc:
        _log.warning(
            "resolve_param_types: %s has no inspectable signature: %s", ref, exc
        )
        return None
    return _annotated_param_types(sig, hints)


def _parse_python_ref(ref: str) -> tuple[str, str] | None:
    """Split `ref` into `(path_str, qualname)`, or `None` if malformed or
    not a Python target."""
    try:
        path_str, qualname = ref.split("::", 1)
    except ValueError:
        _log.warning("resolve_param_types: malformed ref %r", ref)
        return None
    if not path_str.endswith(".py"):
        _log.debug("resolve_param_types: %s is not a Python target", ref)
        return None
    return path_str, qualname


def _resolve_callable(module: object, qualname: str) -> Callable[..., object] | None:
    """The callable `module.qualname` resolves to, or `None` (with a
    warning) if it does not resolve to a callable."""
    target = _resolve_attr(module, qualname)
    if target is None or not callable(target):
        _log.warning(
            "resolve_param_types: %s has no callable %s",
            getattr(module, "__name__", module),
            qualname,
        )
        return None
    return target


def _resolve_hints(target: Callable[..., object], ref: str) -> dict[str, type] | None:
    """`typing.get_type_hints(target)`, or `None` (with a warning) if
    hints cannot be resolved."""
    try:
        return typing.get_type_hints(target)
    except Exception as exc:  # noqa: BLE001 - forward refs/missing imports fail arbitrarily
        _log.warning("resolve_param_types: %s hints unresolvable: %s", ref, exc)
        return None


def _import_ref_module(root: Path, path_str: str) -> object | None:
    """Import the module backing source file `path_str`, temporarily adding
    `root/src` to `sys.path` if needed; `None` on any derivation/import failure."""
    module_name = _module_name(path_str)
    if module_name is None:
        _log.warning(
            "resolve_param_types: could not derive module name from %s", path_str
        )
        return None

    src_dir = str(root / "src")
    added = src_dir not in sys.path
    if added:
        sys.path.insert(0, src_dir)
    try:
        return importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001 - best-effort introspection, never crashes
        _log.warning("resolve_param_types: could not import %s: %s", module_name, exc)
        return None
    finally:
        if added and src_dir in sys.path:
            sys.path.remove(src_dir)


def _annotated_param_types(
    sig: inspect.Signature, hints: dict[str, type]
) -> tuple[type, ...]:
    """The resolved annotation types of `sig`'s non-self/cls parameters that
    have one."""
    types: list[type] = []
    for name in sig.parameters:
        if name in _SELF_PARAMS:
            continue
        annotation = hints.get(name)
        if annotation is not None:
            types.append(annotation)
    return tuple(types)


__all__ = ["resolve_param_types"]
