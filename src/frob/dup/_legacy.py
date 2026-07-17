"""Legacy Type-1/Type-2 duplicate scan (pre-smart-dup, docs/dup.md).

Kept verbatim behind `find_duplicates` for `frob check`'s dup stage and the
`frob dup` CLI (`frob.app.dup_runner`), neither of which has been
re-platformed onto the rung pipeline yet. New code should prefer
`frob.dup.find_clones` (docs/dup.md's smart pipeline); this module is the
compatibility shim that keeps the existing entry point working.

Parses through `frob.lang.raw_tree` (one grammar-loading mechanism, per
docs/lang.md). The per-language fingerprinting/iteration helpers live in the
cohesive `_legacy_py`/`_legacy_cpp` submodules (with shared node/hash
helpers in `_legacy_common`); this module owns the models, the file
scanners, and the clone-grouping entry point.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from tree_sitter import Node
from typani import ErrorSet

from frob.dup._legacy_common import _child, _sha16
from frob.dup._legacy_cpp import (
    _collect_locals_cpp,
    _iter_functions_cpp,
    _serialize_cpp_body,
)
from frob.dup._legacy_py import (
    _collect_locals_py,
    _iter_functions_py,
    _serialize_py_body,
)
from frob.logging import get_logger

_log = get_logger(__name__)

_PY_EXTS = {".py"}
_CPP_EXTS = {".cpp", ".cc", ".cxx", ".h", ".hpp"}


# ---------------------------------------------------------------------------
# Errors and data models
# ---------------------------------------------------------------------------


# frob:doc docs/dup.md#legacy-scanner
class DupError(ErrorSet):
    ParseFailed = "failed to parse file"


# frob:doc docs/dup.md#legacy-scanner
class CodeFragment(BaseModel):
    file: str
    start_line: int
    end_line: int
    symbol: str


# frob:doc docs/dup.md#legacy-scanner
class CloneGroup(BaseModel):
    clone_type: Literal["exact", "renamed"]
    size_lines: int
    fragments: list[CodeFragment]


# frob:doc docs/dup.md#legacy-scanner
class DupResult(BaseModel):
    root: str
    groups: list[CloneGroup]

    @property
    def total_clones(self) -> int:
        # frob:doc docs/dup.md#legacy-scanner
        return sum(len(g.fragments) for g in self.groups)

    def as_text(self) -> str:
        # frob:doc docs/dup.md#legacy-scanner
        if not self.groups:
            return "no duplicates found"
        n_groups = len(self.groups)
        n_frags = self.total_clones
        lines: list[str] = [
            f"{n_groups} duplicate group{'s' if n_groups != 1 else ''}, "
            f"{n_frags} fragment{'s' if n_frags != 1 else ''}",
            "",
        ]
        for i, g in enumerate(self.groups, 1):
            lines.append(
                f"Group {i} ({g.clone_type},"
                f" {g.size_lines} line{'s' if g.size_lines != 1 else ''}):"
            )
            max_loc = max(
                len(f"{frag.file}:{frag.start_line}-{frag.end_line}")
                for frag in g.fragments
            )
            for frag in g.fragments:
                loc = f"{frag.file}:{frag.start_line}-{frag.end_line}"
                padding = " " * (max_loc - len(loc) + 2)
                lines.append(f"  {loc}{padding}{frag.symbol}")
        return "\n".join(lines)

    def as_json(self) -> str:
        # frob:doc docs/dup.md#legacy-scanner
        return json.dumps(self.model_dump(), indent=2)


# ---------------------------------------------------------------------------
# File scanning
# ---------------------------------------------------------------------------


def _index_function(
    func_node: Node,
    symbol: str,
    rel: str,
    src: bytes,
    min_lines: int,
    exact_map: dict[str, list[CodeFragment]],
    renamed_map: dict[str, list[CodeFragment]],
    collect_locals: Callable[[Node], set[str]],
    serialize_body: Callable[[Node, set[str]], str],
) -> None:
    """Fingerprint one function body into the exact/renamed hash maps.

    Exact hash is the whitespace-stripped original text; renamed hash is the
    alpha-renamed serialized body. Bodies below `min_lines` are skipped.
    """
    body = _child(func_node, "body")
    if body is None:
        return
    start_line = body.start_point[0] + 1
    end_line = body.end_point[0] + 1
    if end_line - start_line + 1 < min_lines:
        return

    frag = CodeFragment(
        file=rel, start_line=start_line, end_line=end_line, symbol=symbol
    )
    body_bytes = src[body.start_byte : body.end_byte]
    exact_text = b"\n".join(line.strip() for line in body_bytes.splitlines())
    exact_map[_sha16(exact_text.decode(errors="replace"))].append(frag)

    locals_ = collect_locals(func_node)
    renamed_map[_sha16(serialize_body(body, locals_))].append(frag)


def _scan_py_file(
    path: Path,
    root: Path,
    min_lines: int,
    exact_map: dict[str, list[CodeFragment]],
    renamed_map: dict[str, list[CodeFragment]],
) -> None:
    from frob.lang import raw_tree

    parsed = raw_tree(path)
    if parsed.is_err:
        _log.warning("parse failed for %s: %s", path, parsed.err)
        return
    tree, src, _language = parsed.danger_ok
    rel = str(path.relative_to(root))
    for func_node, symbol in _iter_functions_py(tree.root_node):
        _index_function(
            func_node,
            symbol,
            rel,
            src,
            min_lines,
            exact_map,
            renamed_map,
            _collect_locals_py,
            _serialize_py_body,
        )


def _scan_cpp_file(
    path: Path,
    root: Path,
    min_lines: int,
    exact_map: dict[str, list[CodeFragment]],
    renamed_map: dict[str, list[CodeFragment]],
) -> None:
    from frob.lang import raw_tree

    parsed = raw_tree(path)
    if parsed.is_err:
        _log.warning("parse failed for %s: %s", path, parsed.err)
        return
    tree, src, _language = parsed.danger_ok
    rel = str(path.relative_to(root))
    for func_node, symbol in _iter_functions_cpp(tree.root_node):
        _index_function(
            func_node,
            symbol,
            rel,
            src,
            min_lines,
            exact_map,
            renamed_map,
            _collect_locals_cpp,
            _serialize_cpp_body,
        )


# ---------------------------------------------------------------------------
# Grouping and main entry point
# ---------------------------------------------------------------------------


def _scan_tree(
    root: Path,
    min_lines: int,
    exact_map: dict[str, list[CodeFragment]],
    renamed_map: dict[str, list[CodeFragment]],
) -> None:
    """Scan every python/C++ file under `root` into the two hash maps."""
    for path in _walk(root):
        ext = path.suffix.lower()
        if ext in _PY_EXTS:
            _scan_py_file(path, root, min_lines, exact_map, renamed_map)
        elif ext in _CPP_EXTS:
            _scan_cpp_file(path, root, min_lines, exact_map, renamed_map)


def _exact_groups(exact_map: dict[str, list[CodeFragment]]) -> list[CloneGroup]:
    """Type-1 (exact) groups: hash buckets holding 2+ identical fragments."""
    groups: list[CloneGroup] = []
    for frags in exact_map.values():
        if len(frags) < 2:
            continue
        size = max(f.end_line - f.start_line + 1 for f in frags)
        groups.append(CloneGroup(clone_type="exact", size_lines=size, fragments=frags))
    return groups


def _renamed_groups(
    renamed_map: dict[str, list[CodeFragment]], exact_groups: list[CloneGroup]
) -> list[CloneGroup]:
    """Type-2 (renamed) groups: renamed-hash buckets with 2+ fragments that
    are not already wholly covered by a single exact group."""
    exact_key_sets = [
        {(ef.file, ef.start_line) for ef in eg.fragments} for eg in exact_groups
    ]
    groups: list[CloneGroup] = []
    for frags in renamed_map.values():
        if len(frags) < 2:
            continue
        key_set = {(f.file, f.start_line) for f in frags}
        if any(key_set <= eks for eks in exact_key_sets):
            continue
        size = max(f.end_line - f.start_line + 1 for f in frags)
        groups.append(
            CloneGroup(clone_type="renamed", size_lines=size, fragments=frags)
        )
    return groups


# frob:doc docs/dup.md#legacy-scanner
def find_duplicates(root: Path, min_lines: int = 6) -> DupResult:
    """Scan root recursively for duplicate function bodies."""
    from frob.logging.quiet import quiet_stdout_logs

    exact_map: dict[str, list[CodeFragment]] = defaultdict(list)
    renamed_map: dict[str, list[CodeFragment]] = defaultdict(list)

    # frob.lang.raw_tree logs at INFO/DEBUG per parse; CLI callers piping
    # `--json` need that off stdout, same reasoning as frob.logging.quiet.
    with quiet_stdout_logs():
        _scan_tree(root, min_lines, exact_map, renamed_map)

    exact_groups = _exact_groups(exact_map)
    renamed_groups = _renamed_groups(renamed_map, exact_groups)
    groups = sorted(
        exact_groups + renamed_groups, key=lambda g: g.size_lines, reverse=True
    )
    return DupResult(root=str(root), groups=groups)


def _walk(root: Path):
    """Yield all files under root, honoring built-in skips and [graph] exclude."""
    # frob:ticket T-0026
    from frob.excludes import is_excluded, is_skipped_dir, load_exclude_globs

    exclude_globs = load_exclude_globs(root)
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        if any(is_skipped_dir(part) for part in rel.parts):
            continue
        if exclude_globs and is_excluded(rel.as_posix(), exclude_globs):
            continue
        yield path
