from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.lang import LangError, RawSymbol, SymbolKind, extract_imports, parse_file


# frob:doc docs/outline.md#public-api
class OutlineError(ErrorSet):
    UnsupportedLanguage = "No outline adapter for this file extension"
    ParseFailed = "tree-sitter could not parse the file"


# frob:doc docs/outline.md#public-api
class FunctionOutline(BaseModel):
    name: str
    signature: str
    line: int
    doc: str = ""


# frob:doc docs/outline.md#public-api
class ClassOutline(BaseModel):
    name: str
    line: int
    methods: list[FunctionOutline]


# frob:doc docs/outline.md#public-api
class ModuleOutline(BaseModel):
    path: str
    lines: int
    imports: list[str]
    functions: list[FunctionOutline]
    classes: list[ClassOutline]

    def as_text(self, include_private: bool = False) -> str:
        # frob:doc docs/outline.md#public-api
        parts = [f"{self.path}  ({self.lines} lines)"]
        if self.imports:
            parts.append(f"  imports: {', '.join(self.imports)}")

        hidden_fns = 0
        for fn in self.functions:
            if not include_private and fn.name.startswith("_"):
                hidden_fns += 1
                continue
            line = f"  {fn.signature}  [L{fn.line}]"
            if fn.doc:
                line += f"  -- {fn.doc}"
            parts.append(line)

        hidden_methods = 0
        for cls in self.classes:
            if not include_private and cls.name.startswith("_"):
                hidden_fns += 1
                continue
            parts.append(f"  class {cls.name}  [L{cls.line}]")
            for m in cls.methods:
                if not include_private and m.name.startswith("_"):
                    hidden_methods += 1
                    continue
                line = f"    {m.signature}  [L{m.line}]"
                if m.doc:
                    line += f"  -- {m.doc}"
                parts.append(line)

        total_hidden = hidden_fns + hidden_methods
        if total_hidden > 0:
            parts.append(f"  [{total_hidden} private -- use --all to show]")

        return "\n".join(parts)

    def as_json(self) -> str:
        # frob:doc docs/outline.md#public-api
        return self.model_dump_json(indent=2)


_PY_EXTS = {".py"}
_CPP_EXTS = {".c", ".cc", ".cpp", ".cxx", ".c++", ".h", ".hpp", ".hxx", ".h++"}


# frob:doc docs/outline.md#public-api
def outline_file(path: Path) -> Result[ModuleOutline, OutlineError]:
    try:
        display = path.relative_to(Path.cwd())
    except ValueError:
        display = path

    ext = path.suffix.lower()
    if ext not in _PY_EXTS and ext not in _CPP_EXTS:
        return Err(OutlineError.UnsupportedLanguage)

    parsed_result = parse_file(path)
    if parsed_result.is_err:
        err = parsed_result.danger_err
        if err == LangError.UnsupportedLanguage:
            return Err(OutlineError.UnsupportedLanguage)
        return Err(OutlineError.ParseFailed)
    parsed = parsed_result.danger_ok

    imports_result = extract_imports(path)
    raw_imports = imports_result.danger_ok if imports_result.is_ok else ()
    imports = _dedupe_imports(raw_imports, ext)

    try:
        lines = path.read_bytes().count(b"\n") + 1
    except OSError:
        return Err(OutlineError.ParseFailed)

    functions, classes = _outline_symbols(parsed.symbols)

    return Ok(
        ModuleOutline(
            path=str(display),
            lines=lines,
            imports=imports,
            functions=functions,
            classes=classes,
        )
    )


def _dedupe_imports(raw_imports: tuple[str, ...], ext: str) -> list[str]:
    """Old outline behavior: python's first dotted segment, cpp's raw include text."""
    out: list[str] = []
    for spec in raw_imports:
        name = spec.split(".")[0] if ext in _PY_EXTS else spec
        if name not in out:
            out.append(name)
    return out


def _build_classes(
    symbols: tuple[RawSymbol, ...],
) -> tuple[dict[str, ClassOutline], list[str]]:
    """Top-level classes keyed by name, plus their source order."""
    classes: dict[str, ClassOutline] = {}
    class_order: list[str] = []
    for sym in symbols:
        if sym.kind == SymbolKind.CLASS and "." not in sym.qualname:
            classes[sym.qualname] = ClassOutline(
                name=sym.qualname, line=sym.span[0], methods=[]
            )
            class_order.append(sym.qualname)
    return classes, class_order


def _assign_functions(
    symbols: tuple[RawSymbol, ...], classes: dict[str, ClassOutline]
) -> list[FunctionOutline]:
    """Collect free functions; attach methods to their owning class in `classes`."""
    functions: list[FunctionOutline] = []
    for sym in symbols:
        if sym.kind == SymbolKind.FUNCTION:
            functions.append(_function_outline(sym))
        elif sym.kind == SymbolKind.METHOD and "." in sym.qualname:
            owner, _, name = sym.qualname.rpartition(".")
            cls = classes.get(owner)
            if cls is not None:
                cls.methods.append(_function_outline(sym, name=name))
    return functions


def _outline_symbols(
    symbols: tuple[RawSymbol, ...],
) -> tuple[list[FunctionOutline], list[ClassOutline]]:
    """Rebuild the old function/class(+methods) tree from flat qualname symbols."""
    classes, class_order = _build_classes(symbols)
    functions = _assign_functions(symbols, classes)
    return functions, [classes[name] for name in class_order]


def _function_outline(sym: RawSymbol, name: str | None = None) -> FunctionOutline:
    display_name = name if name is not None else sym.qualname
    return FunctionOutline(
        name=display_name,
        signature=_signature_from_tokens(display_name, sym.sig_tokens),
        line=sym.span[0],
        doc=_first_doc_line(sym.doc_text),
    )


def _signature_from_tokens(name: str, sig_tokens: tuple[str, ...]) -> str:
    """Reconstruct `name(params) -> ret` from the leaf-token stream.

    `sig_tokens` is the same normalized token sequence `frob.graph` hashes --
    reusing it here (instead of re-deriving a signature string a second way)
    is what keeps outline and graph agreeing on what a symbol's "shape" is.
    """
    # Find matching parens for the parameter list, then anything after the
    # closing paren (skipping a leading "->" ) is the return annotation.
    try:
        open_idx = sig_tokens.index("(")
    except ValueError:
        return f"{name}()"
    depth = 0
    close_idx = None
    for i in range(open_idx, len(sig_tokens)):
        if sig_tokens[i] == "(":
            depth += 1
        elif sig_tokens[i] == ")":
            depth -= 1
            if depth == 0:
                close_idx = i
                break
    if close_idx is None:
        return f"{name}()"

    params = "".join(_spaced(sig_tokens[open_idx + 1 : close_idx]))
    ret = ""
    tail = sig_tokens[close_idx + 1 :]
    if tail and tail[0] == "->":
        ret_tokens = tail[1:]
        # Stop the return annotation at the signature's closing colon, if any.
        if ret_tokens and ret_tokens[-1] == ":":
            ret_tokens = ret_tokens[:-1]
        ret = " -> " + "".join(_spaced(ret_tokens))
    return f"{name}({params}){ret}"


_NO_SPACE_BEFORE = {",", ")", ":", "]", "."}
_NO_SPACE_AFTER = {"(", "[", "."}


def _spaced(tokens: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    prev: str | None = None
    for tok in tokens:
        if out and prev not in _NO_SPACE_AFTER and tok not in _NO_SPACE_BEFORE:
            out.append(" ")
        out.append(tok)
        prev = tok
    return out


def _first_doc_line(doc_text: str) -> str:
    """First sentence (or first 80 chars) of a collapsed-whitespace docstring."""
    if not doc_text:
        return ""
    idx = doc_text.find(".")
    if 0 < idx < 80:
        return doc_text[: idx + 1]
    return doc_text[:80]
