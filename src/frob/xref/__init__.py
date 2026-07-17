from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.lang import RawSymbol, SymbolKind, iter_identifiers, parse_file


# frob:doc docs/xref.md#public-api
class XrefError(ErrorSet):
    NoFilesFound = "No source files found under the given path"


# frob:doc docs/xref.md#public-api
class Definition(BaseModel):
    file: str
    line: int


# frob:doc docs/xref.md#public-api
class Usage(BaseModel):
    file: str
    line: int
    context: str


# frob:doc docs/xref.md#public-api
class XrefResult(BaseModel):
    symbol: str
    definition: Definition | None
    usages: list[Usage]

    def as_text(self, cross_file: bool = False) -> str:
        # frob:doc docs/xref.md#public-api
        parts = [self.symbol]
        if self.definition:
            parts.append(f"  defined:  {self.definition.file}:{self.definition.line}")
        else:
            parts.append("  defined:  (not found)")

        usages = self.usages
        if cross_file and self.definition:
            def_file = self.definition.file
            usages = [u for u in usages if u.file != def_file]

        if usages:
            skipped = len(self.usages) - len(usages)
            label = "used by (cross-file):" if cross_file else "used by:"
            parts.append(f"  {label}")
            for u in usages:
                parts.append(f"    {u.file}:{u.line:<6} {u.context.strip()}")
            if skipped:
                parts.append(
                    f"    [{skipped} same-file usages hidden"
                    " -- omit --cross-file to show]"
                )
        else:
            parts.append("  used by: (none found)")
        return "\n".join(parts)

    def as_json(self) -> str:
        # frob:doc docs/xref.md#public-api
        return self.model_dump_json(indent=2)


_PY_EXTS = {".py"}
_CPP_EXTS = {".c", ".cc", ".cpp", ".cxx", ".c++", ".h", ".hpp", ".hxx", ".h++"}
_SOURCE_EXTS = _PY_EXTS | _CPP_EXTS
_LANG_EXTS = {"python": _PY_EXTS, "c": _CPP_EXTS, "cpp": _CPP_EXTS}


# frob:doc docs/xref.md#public-api
def xref(
    symbol: str,
    root: Path,
    lang: str | None = None,
) -> Result[XrefResult, XrefError]:
    files = _collect_source_files(root, lang)
    if not files:
        return Err(XrefError.NoFilesFound)

    definition: Definition | None = None
    usages: list[Usage] = []

    for path in files:
        ext = path.suffix.lower()
        try:
            rel = str(path.relative_to(root)) if root.is_dir() else path.name
        except ValueError:
            rel = str(path)

        if ext in _SOURCE_EXTS:
            defn, file_usages = _search_parsed(path, symbol, rel)
        else:
            src_lines = path.read_bytes().decode(errors="replace").splitlines()
            defn, file_usages = _search_text(src_lines, symbol, rel)

        if defn and definition is None:
            definition = defn
        usages.extend(file_usages)

    return Ok(XrefResult(symbol=symbol, definition=definition, usages=usages))


def _collect_source_files(root: Path, lang: str | None) -> list[Path]:
    if lang == "python":
        exts = _PY_EXTS
    elif lang in ("cpp", "c"):
        exts = _CPP_EXTS
    else:
        exts = _SOURCE_EXTS

    if root.is_file():
        return [root] if root.suffix.lower() in exts else []

    results: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in exts:
            # Use resolved parts to avoid false-positives from ".." traversal
            try:
                rel_parts = path.resolve().relative_to(root.resolve()).parts
            except ValueError:
                rel_parts = path.parts
            if not any(p.startswith(".") or p == "__pycache__" for p in rel_parts):
                results.append(path)
    return results


_DEFINITION_KINDS = (SymbolKind.FUNCTION, SymbolKind.CLASS, SymbolKind.METHOD)


def _definition_symbols(symbols: tuple[RawSymbol, ...]) -> tuple[RawSymbol, ...]:
    return tuple(sym for sym in symbols if sym.kind in _DEFINITION_KINDS)


def _search_parsed(
    path: Path, symbol: str, rel: str
) -> tuple[Definition | None, list[Usage]]:
    src_lines = path.read_bytes().decode(errors="replace").splitlines()

    definition: Definition | None = None
    parsed_result = parse_file(path)
    if parsed_result.is_ok:
        for sym in _definition_symbols(parsed_result.danger_ok.symbols):
            _, _, name = sym.qualname.rpartition(".")
            if name == symbol:
                definition = Definition(file=rel, line=sym.span[0])
                break

    usages: list[Usage] = []
    ids_result = iter_identifiers(path)
    if ids_result.is_ok:
        def_line = definition.line if definition else None
        for name, line in ids_result.danger_ok:
            if name != symbol:
                continue
            if def_line is not None and line == def_line:
                # Same line as the matching declaration -- almost certainly
                # the declaration's own name token, not a usage of it.
                continue
            ctx = src_lines[line - 1] if line <= len(src_lines) else ""
            usages.append(Usage(file=rel, line=line, context=ctx))

    return definition, usages


def _search_text(
    src_lines: list[str], symbol: str, rel: str
) -> tuple[Definition | None, list[Usage]]:
    usages: list[Usage] = []
    for i, line in enumerate(src_lines, 1):
        if symbol in line:
            usages.append(Usage(file=rel, line=i, context=line))
    return None, usages
