# frob:waive INV006 preset="split-carried-prose"
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.lang import (
    LangError,
    RawSymbol,
    SymbolKind,
    extract_imports,
    parse_file,
    supported_extensions,
)


# frob:doc docs/commands/outline.md#public-api
class OutlineError(ErrorSet):
    UnsupportedLanguage = "No outline adapter for this file extension"
    ParseFailed = "tree-sitter could not parse the file"


# frob:doc docs/commands/outline.md#public-api
class FunctionOutline(BaseModel):
    name: str
    signature: str
    line: int
    doc: str = ""


# frob:doc docs/commands/outline.md#public-api
class ClassOutline(BaseModel):
    name: str
    line: int
    methods: list[FunctionOutline]


# frob:doc docs/commands/outline.md#public-api
class ModuleOutline(BaseModel):
    path: str
    lines: int
    imports: list[str]
    functions: list[FunctionOutline]
    classes: list[ClassOutline]

    def _functions_as_text(self, include_private: bool) -> tuple[list[str], int]:
        """Function lines plus the count hidden for privacy."""
        parts: list[str] = []
        hidden = 0
        for fn in self.functions:
            if not include_private and fn.name.startswith("_"):
                hidden += 1
                continue
            line = f"  {fn.signature}  [L{fn.line}]"
            if fn.doc:
                line += f"  -- {fn.doc}"
            parts.append(line)
        return parts, hidden

    def _classes_as_text(self, include_private: bool) -> tuple[list[str], int, int]:
        """Class/method lines, count of hidden classes, and count of hidden methods."""
        parts: list[str] = []
        hidden_classes = 0
        hidden_methods = 0
        for cls in self.classes:
            if not include_private and cls.name.startswith("_"):
                hidden_classes += 1
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
        return parts, hidden_classes, hidden_methods

    # frob:ticket T-0588
    # frob:tests tests/unit/test_outline.py::test_py_outline_as_text
    def as_text(self, include_private: bool = False) -> str:
        # frob:doc docs/commands/outline.md#public-api
        parts = [f"{self.path}  ({self.lines} lines)"]
        if self.imports:
            parts.append(f"  imports: {', '.join(self.imports)}")

        fn_parts, hidden_fns = self._functions_as_text(include_private)
        parts.extend(fn_parts)

        cls_parts, hidden_classes, hidden_methods = self._classes_as_text(
            include_private
        )
        parts.extend(cls_parts)

        total_hidden = hidden_fns + hidden_classes + hidden_methods
        if total_hidden > 0:
            parts.append(f"  [{total_hidden} private -- use --all to show]")

        return "\n".join(parts)

    # frob:ticket T-0588
    # frob:tests tests/unit/test_outline.py::test_py_outline_as_json
    def as_json(self) -> str:
        # frob:doc docs/commands/outline.md#public-api
        return self.model_dump_json(indent=2)


_PY_EXTS = {".py"}
_CPP_EXTS = {".c", ".cc", ".cpp", ".cxx", ".c++", ".h", ".hpp", ".hxx", ".h++"}
# `.strata` has no import syntax `extract_imports` understands (T-0077's
# docstring) -- outline still supports it as a third bucket (T-0129) so its
# symbols show up; `_dedupe_imports` sees an always-empty `raw_imports` for
# it and the cpp-style branch is a no-op.
_STRATA_EXTS = frozenset({".strata"})
# `.rs` is frob.lang's rust grammar (T-0238); rust has no `extract_imports`
# walker registered in `frob.lang._extract._IMPORT_WALKERS`, so
# `_parse_for_outline` picks up an always-empty `raw_imports` tuple for it
# the same way `.strata` does, but through the ordinary `extract_imports`
# call rather than a dedicated skip branch -- `.rs` files simply carry no
# outline imports.
_RUST_EXTS = frozenset({".rs"})
# `.strata` and `.rs` are drawn from `frob.lang.supported_extensions()`
# (T-0129, T-0238) rather than a fresh literal, since that is its single
# source of truth; `_PY_EXTS`/`_CPP_EXTS` predate T-0077/T-0129 and
# intentionally carry a couple of cpp extensions (.c++/.hxx/.h++) frob.lang's
# grammar table does not, so they are kept as explicit local buckets rather
# than narrowed to frob.lang's set.
_OUTLINE_EXTS = (
    frozenset(_PY_EXTS)
    | frozenset(_CPP_EXTS)
    | (_STRATA_EXTS & supported_extensions())
    | (_RUST_EXTS & supported_extensions())
)


def _display_path(path: Path) -> Path:
    """`path` relative to the cwd when possible, else `path` unchanged."""
    try:
        return path.relative_to(Path.cwd())
    except Exception:
        return path


def _parse_for_outline(
    path: Path,
) -> Result[tuple, OutlineError]:
    """Parse `path` and its imports; a single `OutlineError` on either failure."""
    parsed_result = parse_file(path)
    if parsed_result.is_err:
        err = parsed_result.danger_err
        if err == LangError.UnsupportedLanguage:
            return Err(OutlineError.UnsupportedLanguage)
        return Err(OutlineError.ParseFailed)
    parsed = parsed_result.danger_ok

    # `extract_imports` is a tree-sitter-only escape hatch with no `.strata`
    # analogue (frob.lang docstring) -- skip the call for it rather than
    # inviting its "no grammar registered" warning on every strata file
    # (T-0129); `.strata` outlines simply carry no imports.
    if path.suffix.lower() in _STRATA_EXTS:
        return Ok((parsed, ()))

    imports_result = extract_imports(path)
    raw_imports = imports_result.danger_ok if imports_result.is_ok else ()
    return Ok((parsed, raw_imports))


# frob:doc docs/commands/outline.md#public-api
# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to _parse_for_outline's own call \
# graph (parse_file/extract_imports, cross-module Result-returning calls) and \
# _outline_symbols, a pure structural walk of already-parsed data; every \
# locally-visible fallible step is Result-checked or caught"
# frob:waive EXHAUST002 reason="T-1062: same resolver artifact as EXHAUST001 above"
def outline_file(path: Path) -> Result[ModuleOutline, OutlineError]:
    ext = path.suffix.lower()
    if ext not in _OUTLINE_EXTS:
        return Err(OutlineError.UnsupportedLanguage)

    parsed_pair = _parse_for_outline(path)
    if parsed_pair.is_err:
        return Err(parsed_pair.danger_err)
    parsed, raw_imports = parsed_pair.danger_ok
    imports = _dedupe_imports(raw_imports, ext)

    try:
        lines = path.read_bytes().count(b"\n") + 1
    except OSError:
        return Err(OutlineError.ParseFailed)

    functions, classes = _outline_symbols(parsed.symbols)

    return Ok(
        ModuleOutline(
            path=str(_display_path(path)),
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


def _find_matching_close_paren(
    sig_tokens: tuple[str, ...], open_idx: int
) -> int | None:
    """Index of the `)` that closes the `(` at `open_idx`, or `None` if unbalanced."""
    depth = 0
    for i in range(open_idx, len(sig_tokens)):
        if sig_tokens[i] == "(":
            depth += 1
        elif sig_tokens[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return None


def _return_annotation(tail: tuple[str, ...]) -> str:
    """The ` -> ret` suffix for a signature, given the tokens after its `)`."""
    if not tail or tail[0] != "->":
        return ""
    ret_tokens = tail[1:]
    # Stop the return annotation at the signature's closing colon, if any.
    if ret_tokens and ret_tokens[-1] == ":":
        ret_tokens = ret_tokens[:-1]
    return " -> " + "".join(_spaced(ret_tokens))


# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to _find_matching_close_ \
# paren/_spaced/_return_annotation, plain tuple/str token-walk helpers the resolver \
# cannot see through; the one real raise path (tuple.index) is caught below"
# frob:waive EXHAUST002 reason="T-1062: same resolver artifact as EXHAUST001 above"
# frob:waive PII012 reason="T-1062: 'token' here means a parsed leaf-token from \
# frob.graph's normalized token stream (sig_tokens), not a credential/auth token -- a \
# name-signature false positive, same class as frob.gates._docptr's existing PII012 \
# waiver for its own unrelated lexical-token vocabulary"
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
    close_idx = _find_matching_close_paren(sig_tokens, open_idx)
    if close_idx is None:
        return f"{name}()"

    params = "".join(_spaced(sig_tokens[open_idx + 1 : close_idx]))
    ret = _return_annotation(sig_tokens[close_idx + 1 :])
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
