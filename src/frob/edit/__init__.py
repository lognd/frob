"""
frob edit -- symbol-level file editing with a staging layer.

Staging model (safe for concurrent agents):
  frob edit FILE SYMBOL --replace   -> stage the edit (.frob/edits/<slug>/SYMBOL.json)
  frob edit FILE --commit           -> apply all staged patches atomically
  frob edit FILE --status           -> show what is staged
  frob edit FILE SYMBOL --immediate -> old single-shot behaviour (lock + write now)

Agents write to different patch files (no overlap). The commit step acquires
an exclusive lock, re-parses the file fresh, applies patches one by one
(re-parsing between each to absorb line-number shifts), writes once via
temp+rename, then clears patches.
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import os
import time
from pathlib import Path

from pydantic import BaseModel
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.ast import python as _py
from frob.ast.common import child_by_field
from frob.ast.common import text as ast_text


class EditError(ErrorSet):
    UnsupportedFile = "Only Python files are supported"
    ParseFailed = "Could not parse the file"
    SymbolNotFound = "Symbol not found in file"
    AmbiguousSymbol = "Multiple symbols match; use ClassName.method to disambiguate"
    CommitFailed = "Commit failed; patches left in place"
    NothingToCommit = "No staged patches for this file"


class IsolatedSymbol(BaseModel):
    model_config = {}

    path: str
    symbol: str
    start_line: int
    end_line: int
    source: str


class StagedPatch(BaseModel):
    model_config = {}

    symbol: str
    new_source: str
    staged_at: float = 0.0

    def to_patch_text(self) -> str:
        # Format: <staged_at>\n<symbol>\n<source>
        # Compact: one header line, one symbol line, then raw source
        return f"{self.staged_at}\n{self.symbol}\n{self.new_source}"

    @classmethod
    def from_patch_text(cls, text: str) -> "StagedPatch":
        first_nl = text.index("\n")
        second_nl = text.index("\n", first_nl + 1)
        staged_at = float(text[:first_nl])
        symbol = text[first_nl + 1 : second_nl]
        new_source = text[second_nl + 1 :]
        return cls(symbol=symbol, new_source=new_source, staged_at=staged_at)


class CommitResult(BaseModel):
    model_config = {}

    path: str
    applied: list[str]
    skipped: list[str]  # same-symbol conflicts; last-mtime wins


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def isolate(path: Path, symbol: str) -> Result[IsolatedSymbol, EditError]:
    """Extract a symbol's source and line range without modifying the file."""
    if path.suffix.lower() != ".py":
        return Err(EditError.UnsupportedFile)
    try:
        src_bytes, tree = _py.parse_file(path)
    except Exception:
        return Err(EditError.ParseFailed)

    src_text = src_bytes.decode("utf-8", errors="replace")
    lines = src_text.splitlines(keepends=True)
    return _locate(tree, lines, path, symbol)


def stage(path: Path, symbol: str, new_source: str, *, project_root: Path | None = None) -> Result[Path, EditError]:
    """
    Stage a replacement for symbol without touching the source file.

    Writes .frob/edits/<file-slug>/<symbol>.json.  Multiple agents can call
    this concurrently for different symbols -- no lock required.
    """
    if path.suffix.lower() != ".py":
        return Err(EditError.UnsupportedFile)

    patch_dir = _patch_dir(path, project_root)
    patch_dir.mkdir(parents=True, exist_ok=True)

    safe_name = symbol.replace("/", "_").replace("\\", "_")
    patch_file = patch_dir / f"{safe_name}.patch"

    patch = StagedPatch(symbol=symbol, new_source=new_source, staged_at=time.time())
    patch_file.write_text(patch.to_patch_text(), encoding="utf-8")
    return Ok(patch_file)


def commit(path: Path, *, project_root: Path | None = None) -> Result[CommitResult, EditError]:
    """
    Apply all staged patches for path atomically.

    Steps (all under an exclusive lock on path):
      1. Load patch files sorted by staged_at (oldest first).
      2. Detect same-symbol duplicates -- keep newest, log skipped.
      3. Re-parse file; apply patches one at a time, re-parsing after each.
      4. Write result via temp file + os.replace (atomic on same filesystem).
      5. Remove patch files.
    """
    patch_dir = _patch_dir(path, project_root)
    patches = _load_patches(patch_dir)
    if not patches:
        return Err(EditError.NothingToCommit)

    # Deduplicate by symbol: keep the patch with the highest staged_at
    by_symbol: dict[str, StagedPatch] = {}
    skipped: list[str] = []
    for p in sorted(patches, key=lambda x: x[1].staged_at):
        sym = p[1].symbol
        if sym in by_symbol:
            skipped.append(sym)
        by_symbol[sym] = p[1]
    ordered = list(by_symbol.values())

    lock_path = path.with_suffix(path.suffix + ".froblock")
    try:
        with _exclusive_lock(lock_path):
            content = path.read_text(encoding="utf-8")
            for patch in ordered:
                result = _apply_patch_to_content(content, path, patch)
                if result.is_err:
                    return Err(result.danger_err)
                content = result.danger_ok

            # Atomic write
            tmp = path.with_suffix(path.suffix + ".frob_tmp")
            tmp.write_text(content, encoding="utf-8")
            os.replace(tmp, path)
    except Exception as exc:
        return Err(EditError.CommitFailed)

    # Clear patches only after successful write
    for pfile in patch_dir.glob("*.patch"):
        pfile.unlink(missing_ok=True)
    try:
        patch_dir.rmdir()
    except OSError:
        pass

    return Ok(CommitResult(
        path=str(path),
        applied=[p.symbol for p in ordered],
        skipped=skipped,
    ))


def status(path: Path, *, project_root: Path | None = None) -> list[StagedPatch]:
    """Return all staged patches for path, sorted by staged_at."""
    patch_dir = _patch_dir(path, project_root)
    return [p for _, p in sorted(_load_patches(patch_dir), key=lambda x: x[1].staged_at)]


def replace(path: Path, symbol: str, new_source: str) -> Result[None, EditError]:
    """
    Immediate single-shot replace (lock + write now).  Safe for single-agent
    use; not safe for concurrent agents editing the same file.
    Use stage() + commit() for concurrent workloads.
    """
    lock_path = path.with_suffix(path.suffix + ".froblock")
    try:
        with _exclusive_lock(lock_path):
            # Re-parse under the lock so line numbers are always fresh
            result = isolate(path, symbol)
            if result.is_err:
                return Err(result.danger_err)
            iso = result.danger_ok

            src = path.read_text(encoding="utf-8")
            lines = src.splitlines(keepends=True)
            new_lines = _normalise_source(new_source)
            merged = lines[: iso.start_line - 1] + new_lines + lines[iso.end_line :]

            tmp = path.with_suffix(path.suffix + ".frob_tmp")
            tmp.write_text("".join(merged), encoding="utf-8")
            os.replace(tmp, path)
    except EditError as exc:
        return Err(exc)  # type: ignore[arg-type]
    except Exception:
        return Err(EditError.CommitFailed)
    return Ok(None)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _patch_dir(path: Path, project_root: Path | None) -> Path:
    root = project_root or _find_project_root(path)
    slug = hashlib.sha1(str(path.resolve()).encode()).hexdigest()[:12]
    return root / ".frob" / "edits" / slug


def _find_project_root(path: Path) -> Path:
    """Walk up to find pyproject.toml / Cargo.toml / CMakeLists.txt, else use cwd."""
    sentinels = {"pyproject.toml", "Cargo.toml", "CMakeLists.txt", ".git"}
    current = path.resolve().parent
    for parent in [current, *current.parents]:
        if any((parent / s).exists() for s in sentinels):
            return parent
    return Path.cwd()


def _load_patches(patch_dir: Path) -> list[tuple[Path, StagedPatch]]:
    if not patch_dir.exists():
        return []
    results = []
    for pfile in patch_dir.glob("*.patch"):
        try:
            results.append((pfile, StagedPatch.from_patch_text(pfile.read_text(encoding="utf-8"))))
        except Exception:
            continue
    return results


def _apply_patch_to_content(content: str, path: Path, patch: StagedPatch) -> Result[str, EditError]:
    """Apply one patch to in-memory content; re-parses to get fresh line numbers."""
    try:
        import tree_sitter_python as tspython
        from tree_sitter import Language, Parser
        tree = Parser(Language(tspython.language())).parse(content.encode("utf-8"))
    except Exception:
        return Err(EditError.ParseFailed)

    lines = content.splitlines(keepends=True)
    loc = _locate(tree, lines, path, patch.symbol)
    if loc.is_err:
        return Err(loc.danger_err)
    iso = loc.danger_ok

    new_lines = _normalise_source(patch.new_source)
    merged = lines[: iso.start_line - 1] + new_lines + lines[iso.end_line :]
    return Ok("".join(merged))


def _normalise_source(src: str) -> list[str]:
    lines = src.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    return lines


@contextlib.contextmanager
def _exclusive_lock(lock_path: Path):
    lock_path.touch()
    fh = lock_path.open("r")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()


def _locate(tree, lines, path: Path, symbol: str) -> Result[IsolatedSymbol, EditError]:
    parts = symbol.split(".", 1)
    if len(parts) == 2:
        return _find_method(tree, lines, path, symbol, parts[0], parts[1])
    return _find_top_level(tree, lines, path, symbol)


def _find_top_level(tree, lines, path, symbol) -> Result[IsolatedSymbol, EditError]:
    matches = []
    for node in tree.root_node.children:
        if node.type in ("function_definition", "class_definition", "decorated_definition"):
            name_node = _get_name(node)
            if name_node and ast_text(name_node) == symbol:
                matches.append(node)
    if not matches:
        return Err(EditError.SymbolNotFound)
    if len(matches) > 1:
        return Err(EditError.AmbiguousSymbol)
    node = matches[0]
    start = node.start_point[0]
    end = node.end_point[0]
    return Ok(IsolatedSymbol(
        path=str(path),
        symbol=symbol,
        start_line=start + 1,
        end_line=end + 1,
        source="".join(lines[start : end + 1]),
    ))


def _find_method(tree, lines, path, full_symbol, class_name, method_name) -> Result[IsolatedSymbol, EditError]:
    for node in tree.root_node.children:
        if node.type == "class_definition":
            name_node = child_by_field(node, "name")
            if name_node and ast_text(name_node) == class_name:
                body = child_by_field(node, "body")
                if body:
                    for child in body.named_children:
                        if child.type == "function_definition":
                            mn = child_by_field(child, "name")
                            if mn and ast_text(mn) == method_name:
                                start = child.start_point[0]
                                end = child.end_point[0]
                                return Ok(IsolatedSymbol(
                                    path=str(path),
                                    symbol=full_symbol,
                                    start_line=start + 1,
                                    end_line=end + 1,
                                    source="".join(lines[start : end + 1]),
                                ))
    return Err(EditError.SymbolNotFound)


def _get_name(node):
    if node.type == "decorated_definition":
        for child in node.named_children:
            if child.type in ("function_definition", "class_definition"):
                return child_by_field(child, "name")
        return None
    return child_by_field(node, "name")
