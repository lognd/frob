from __future__ import annotations

from pathlib import Path

from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.ast import cpp as _cpp
from frob.ast import python as _py


class StubError(ErrorSet):
    UnsupportedLanguage = "No stub adapter registered for this file extension"
    TargetNotFound = "The requested target was not found in the parsed tree"
    ParseFailed = "tree-sitter could not parse the file"


_PY_EXTS = {".py"}
_CPP_EXTS = _cpp.ALL_EXTS


def stub_file_multi(path: Path, targets: list[str]) -> Result[str, StubError]:
    """Stub all functions except those in `targets` (all revealed simultaneously)."""
    if not targets:
        return Err(StubError.TargetNotFound)
    if len(targets) == 1:
        return stub_file(path, targets[0])

    ext = path.suffix.lower()
    if ext not in _PY_EXTS:
        return Err(StubError.UnsupportedLanguage)

    src, tree = _py.parse_file(path)
    for t in targets:
        if not _target_exists_py(tree, t):
            return Err(StubError.TargetNotFound)

    return Ok(_py.emit_stub_multi(src, tree, targets))


def stub_file(path: Path, target: str) -> Result[str, StubError]:
    ext = path.suffix.lower()

    if ext in _PY_EXTS:
        src, tree = _py.parse_file(path)
        return _emit_py(src, tree, target)
    elif ext in _CPP_EXTS:
        src, tree = _cpp.parse_file(path)
        return _emit_cpp(src, tree, target)
    else:
        return Err(StubError.UnsupportedLanguage)


def _emit_py(src: bytes, tree, target: str) -> Result[str, StubError]:
    if not _target_exists_py(tree, target):
        return Err(StubError.TargetNotFound)
    return Ok(_py.emit_stub(src, tree, target))


def _emit_cpp(src: bytes, tree, target: str) -> Result[str, StubError]:
    names = _cpp.get_all_functions(tree)
    if target not in names:
        return Err(StubError.TargetNotFound)
    return Ok(_cpp.emit_stub(src, tree, target))


def _target_exists_py(tree, target: str) -> bool:
    parts = target.split(".", 1)
    if len(parts) == 2:
        class_name, method_name = parts
        class_node = _py.find_class_node(tree, class_name)
        if class_node is None:
            return False
        return _py.find_function_node(class_node, method_name) is not None
    else:
        if _py.find_function_node(tree.root_node, target) is not None:
            return True
        return _py.find_class_node(tree, target) is not None
