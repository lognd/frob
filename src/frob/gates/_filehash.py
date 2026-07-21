"""Shared source-tree hashing for gate stamps (docs/modules/gates.md).

`frob.gates._coverage.stamp_coverage` and `frob.gates._baseline.stamp_baseline`
both need "content-hash every tracked source file under root" to detect
staleness against `.frob/coverage-stamp` and `.frob/baseline` respectively.
The two stamps stay independent artifacts (different payloads, different
consumers), but the walk+hash body underneath them was a byte-identical
copy-paste (T-0364/T-0374) -- this module is the one home for it. Kept
private (leading-underscore names, no `__all__`) since it is an internal
implementation detail of the two stamp modules, not a standalone gate.
"""

from __future__ import annotations

from pathlib import Path

from frob.excludes import walk_pruned
from frob.graph import _content_hash as _graph_content_hash

_SOURCE_EXTS = (".py", ".ts", ".tsx", ".rs", ".c", ".h", ".cpp")


def _sha_of(path: Path) -> str | None:
    """Sha256 hex of `path`'s bytes, `None` if unreadable.

    Delegates to `frob.graph`'s content hasher -- same sha256-over-bytes
    primitive `build_graph`'s incremental cache uses, so gate stamps and
    the graph cache never diverge on what "unchanged" means.
    """
    return _graph_content_hash(path)


def _collect_file_hashes(root: Path) -> dict[str, str]:
    """Content-hash every tracked source file under `root` (excluded dirs pruned)."""
    file_hashes: dict[str, str] = {}
    for path in walk_pruned(root):
        if path.suffix not in _SOURCE_EXTS:
            continue
        digest = _sha_of(path)
        if digest is not None:
            file_hashes[str(path.relative_to(root).as_posix())] = digest
    return file_hashes
