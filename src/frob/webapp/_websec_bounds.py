"""WEBSEC123-125: resource-exhaustion input-bounds (T-5311, extends the
T-5140 web-app-lint epic's WEBSEC family -- docs/modules/webapp-websec-
bounds.md).

Three corpus items from the T-5141 leaf's reserved WEBSEC123-125 rule-id
block (`frob.gates._waive._KNOWN_GATE_RULES`, T-5301):

- WEBSEC123: unbounded input length -- a Pydantic/Zod/class-validator
  schema field with no `max_length`/`maxLength`/`maxItems` bound.
- WEBSEC124: a resource-exhaustion parser/body config -- an XML parser
  instantiated without `resolve_entities=False`/`defusedxml` (entity-bomb/
  XXE), or a JSON body-parser call with no size/depth `limit` option
  (JSON bomb / unbounded nesting).
- WEBSEC125: unbounded recursion on user-controlled input -- a recursive
  function with no depth/counter guard anywhere in its body.

A fourth corpus item (28, business-logic step-skipping) is DYNAMIC-only
per the T-5141 corpus -- it is not a static-AST-detectable shape, so it
ships as a `frob:tests` obligation in this leaf's Done report rather
than a rule here (see that report for the exact wording).

FRAMEWORK GATING (T-5302): same short-circuit posture every WEBSEC/
COMPLY/A11Y/SEO/WEBPERF family uses -- `frob.webapp._detect.
detect_frameworks(root)` empty means no scan at all. This module never
re-implements framework sniffing (T-5302's own contract).

WIRING: folded into `frob.gates._taint_gate.taint_gate` alongside T-5307's
`websec_sink_findings`, the same "extend the one taint gate call site,
not a second gate registration" posture that leaf's own docstring
documents -- both families are cheap, framework-gated static scans with
identical `Violation` shape. WARN-tier at first turn-on (T-0688/T-0973
promotion posture).
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.webapp._detect import detect_frameworks

_log = get_logger(__name__)

__all__ = ["WebsecBoundsFinding", "websec_bounds_findings"]


# frob:doc docs/modules/webapp-websec-bounds.md#public-api
@dataclass(frozen=True)
class WebsecBoundsFinding:
    """One WEBSEC123-125 finding: a resource-exhaustion input-bounds gap
    (unbounded length, entity/JSON bomb, unbounded recursion).

    frob:ticket T-5311
    """

    rule: str
    file: str
    line: int
    message: str


def _tracked_files(root: Path, *suffixes: str) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `suffixes`, root-relative
    POSIX paths, `()` on any git failure -- same tracked-file-scan shape
    `frob.webapp._websec_sinks._tracked_files` already uses.

    frob:ticket T-5311
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("websec_bounds: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("websec_bounds: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(suffixes)
    )


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable.

    frob:ticket T-5311
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


# --------------------------------------------------------------------------
# WEBSEC123: unbounded input length
# --------------------------------------------------------------------------

#: pydantic/typing annotations this module treats as "length-bearing" --
#: only these shapes are ever missing a max_length/max_items bound.
_LENGTH_BEARING_ANNOTATIONS = re.compile(r"^(str|list|List|List\[.*\]|list\[.*\])$")

_LENGTH_KEYWORDS = frozenset({"max_length", "max_items", "maxItems", "maxLength"})


def _pydantic_field_findings(path: Path, root: Path) -> list[WebsecBoundsFinding]:
    """WEBSEC123 findings: a pydantic `BaseModel` field annotated `str`/
    `list[...]` whose `Field(...)`/`constr(...)`/`conlist(...)` value has
    no `max_length`/`max_items` keyword.

    frob:ticket T-5311
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text or "BaseModel" not in text:
        return []
    try:
        tree = ast.parse(text, filename=rel_path)
    except SyntaxError as exc:
        _log.debug("websec_bounds: skipping unparseable %s: %s", rel_path, exc)
        return []

    findings: list[WebsecBoundsFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        base_names = [ast.unparse(base) for base in node.bases]
        if not any("BaseModel" in base for base in base_names):
            continue
        for stmt in node.body:
            if not isinstance(stmt, ast.AnnAssign) or stmt.value is None:
                continue
            annotation = ast.unparse(stmt.annotation)
            if not _LENGTH_BEARING_ANNOTATIONS.match(annotation.strip()):
                continue
            call = stmt.value
            if not isinstance(call, ast.Call):
                continue
            call_name = ast.unparse(call.func)
            if not any(name in call_name for name in ("Field", "constr", "conlist")):
                continue
            keyword_names = {kw.arg for kw in call.keywords if kw.arg is not None}
            if keyword_names & _LENGTH_KEYWORDS:
                continue
            field_name = getattr(stmt.target, "id", "<field>")
            line = stmt.lineno
            findings.append(
                WebsecBoundsFinding(
                    rule="WEBSEC123",
                    file=rel_path,
                    line=line,
                    message=(
                        f"WEBSEC123: {rel_path}:{line} field {field_name!r} "
                        f"({annotation}) has no max_length/max_items bound -- "
                        f"unbounded input length lets attacker-controlled "
                        f"input exhaust memory/CPU (resource exhaustion) -- "
                        f"add max_length=/max_items= to the {call_name}(...) "
                        f'call, or `frob:waive WEBSEC123 reason="..."` with '
                        f"a real justification"
                    ),
                )
            )
    return findings


_ZOD_STRING_RE = re.compile(
    r"z\s*\.\s*(string|array)\s*\([^)]*\)((?:\s*\.\s*\w+\([^)]*\))*)"
)
_CLASS_VALIDATOR_LENGTH_DECORATORS = ("@MaxLength(", "@ArrayMaxSize(", "@Max(")
_CLASS_VALIDATOR_UNBOUNDED_DECORATORS = ("@IsString(", "@IsArray(")


def _zod_findings(path: Path, root: Path) -> list[WebsecBoundsFinding]:
    """WEBSEC123 findings: a Zod `z.string()`/`z.array(...)` schema chain
    with no `.max(...)` call anywhere in the same chain.

    frob:ticket T-5311
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text or "z.string" not in text and "z.array" not in text:
        return []
    findings: list[WebsecBoundsFinding] = []
    for match in _ZOD_STRING_RE.finditer(text):
        kind, chain = match.group(1), match.group(2)
        if ".max(" in chain:
            continue
        line = text.count("\n", 0, match.start()) + 1
        findings.append(
            WebsecBoundsFinding(
                rule="WEBSEC123",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC123: {rel_path}:{line} z.{kind}(...) has no "
                    f".max(...) bound -- unbounded input length lets "
                    f"attacker-controlled input exhaust memory/CPU -- add "
                    f"a .max(...) call, or `frob:waive WEBSEC123 reason="
                    f'"..."` with a real justification'
                ),
            )
        )
    return findings


def _class_validator_findings(path: Path, root: Path) -> list[WebsecBoundsFinding]:
    """WEBSEC123 findings: a `@IsString()`/`@IsArray()` class-validator
    property decorator with no `@MaxLength(...)`/`@ArrayMaxSize(...)`
    decorator within the same decorator stack (looked up within 5 lines
    above the property declaration).

    frob:ticket T-5311
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text or "@IsString(" not in text and "@IsArray(" not in text:
        return []
    lines = text.splitlines()
    findings: list[WebsecBoundsFinding] = []
    for idx, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if not any(
            stripped.startswith(d) for d in _CLASS_VALIDATOR_UNBOUNDED_DECORATORS
        ):
            continue
        window = lines[max(0, idx - 5) : idx + 2]
        if any(
            any(d in wline for d in _CLASS_VALIDATOR_LENGTH_DECORATORS)
            for wline in window
        ):
            continue
        line = idx + 1
        findings.append(
            WebsecBoundsFinding(
                rule="WEBSEC123",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC123: {rel_path}:{line} {stripped} has no "
                    f"@MaxLength(...)/@ArrayMaxSize(...) bound -- unbounded "
                    f"input length lets attacker-controlled input exhaust "
                    f"memory/CPU -- add a length bound decorator, or "
                    f'`frob:waive WEBSEC123 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


# --------------------------------------------------------------------------
# WEBSEC124: XML entity bomb/XXE, JSON bomb/unbounded nesting depth
# --------------------------------------------------------------------------

_XML_PARSER_CALL_RE = re.compile(
    r"\b(?:etree\.(?:XMLParser|parse|fromstring)|ElementTree\.(?:XMLParser|parse|fromstring)|xml\.sax\.(?:make_parser|parse))\s*\("
)
_RESOLVE_ENTITIES_FALSE_RE = re.compile(r"resolve_entities\s*=\s*False")


def _xxe_findings(path: Path, root: Path) -> list[WebsecBoundsFinding]:
    """WEBSEC124 findings: an XML parser call in a file that never
    imports `defusedxml` and never passes `resolve_entities=False`.

    frob:ticket T-5311
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text:
        return []
    if "defusedxml" in text:
        return []
    findings: list[WebsecBoundsFinding] = []
    for match in _XML_PARSER_CALL_RE.finditer(text):
        # Look at the call's own line plus a couple following lines for a
        # resolve_entities=False keyword passed across a wrapped call.
        start_line = text.count("\n", 0, match.start())
        snippet = "\n".join(text.splitlines()[start_line : start_line + 3])
        if _RESOLVE_ENTITIES_FALSE_RE.search(snippet):
            continue
        line = start_line + 1
        findings.append(
            WebsecBoundsFinding(
                rule="WEBSEC124",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC124: {rel_path}:{line} XML parser instantiated "
                    f"without resolve_entities=False/defusedxml -- entity-"
                    f"bomb/XXE resource exhaustion (CWE-776/CWE-611) -- "
                    f"use defusedxml or pass resolve_entities=False, or "
                    f'`frob:waive WEBSEC124 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


_BODY_PARSER_CALL_RE = re.compile(
    r"\b(?:bodyParser\.json|express\.json)\s*\(\s*(\{[^}]*\})?\s*\)"
)


def _json_bomb_findings(path: Path, root: Path) -> list[WebsecBoundsFinding]:
    """WEBSEC124 findings: an Express `bodyParser.json(...)`/`express.
    json(...)` call with no `limit` key in its options object (or no
    options object at all) -- JSON bomb / unbounded nesting depth.

    frob:ticket T-5311
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text or ("bodyParser.json" not in text and "express.json" not in text):
        return []
    findings: list[WebsecBoundsFinding] = []
    for match in _BODY_PARSER_CALL_RE.finditer(text):
        options = match.group(1) or ""
        if "limit" in options:
            continue
        line = text.count("\n", 0, match.start()) + 1
        findings.append(
            WebsecBoundsFinding(
                rule="WEBSEC124",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC124: {rel_path}:{line} JSON body parser "
                    f"configured with no size/depth limit -- JSON bomb / "
                    f"unbounded nesting depth resource exhaustion (CWE-776) "
                    f"-- pass a `limit` option, or `frob:waive WEBSEC124 "
                    f'reason="..."` with a real justification'
                ),
            )
        )
    return findings


# --------------------------------------------------------------------------
# WEBSEC125: unbounded recursion on user-controlled input
# --------------------------------------------------------------------------

_DEPTH_GUARD_RE = re.compile(
    r"\b(depth|level|count|limit)\w*\s*(>=|<=|>|<|==)", re.IGNORECASE
)


def _py_recursion_findings(path: Path, root: Path) -> list[WebsecBoundsFinding]:
    """WEBSEC125 findings: a Python function that calls itself with no
    depth/count/limit guard comparison anywhere in its own body.

    frob:ticket T-5311
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text:
        return []
    try:
        tree = ast.parse(text, filename=rel_path)
    except SyntaxError as exc:
        _log.debug("websec_bounds: skipping unparseable %s: %s", rel_path, exc)
        return []

    findings: list[WebsecBoundsFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        calls_self = any(
            isinstance(call.func, ast.Name) and call.func.id == node.name
            for call in ast.walk(node)
            if isinstance(call, ast.Call)
        )
        if not calls_self:
            continue
        body_source = ast.unparse(node)
        if _DEPTH_GUARD_RE.search(body_source):
            continue
        line = node.lineno
        findings.append(
            WebsecBoundsFinding(
                rule="WEBSEC125",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC125: {rel_path}:{line} def {node.name}(...) "
                    f"recurses with no depth/count/limit guard -- unbounded "
                    f"recursion on user-controlled input can exhaust the "
                    f"call stack (CWE-674) -- add a depth parameter with a "
                    f"max-depth early return, or `frob:waive WEBSEC125 "
                    f'reason="..."` with a real justification'
                ),
            )
        )
    return findings


_JS_FUNCTION_DECL_RE = re.compile(r"function\s+(\w+)\s*\(")


def _js_recursion_findings(path: Path, root: Path) -> list[WebsecBoundsFinding]:
    """WEBSEC125 findings: a JS/TS named function declaration that calls
    itself with no depth/count/limit guard comparison anywhere in the
    file text following the declaration.

    frob:ticket T-5311
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text:
        return []
    findings: list[WebsecBoundsFinding] = []
    for match in _JS_FUNCTION_DECL_RE.finditer(text):
        name = match.group(1)
        start = match.end()
        # Find the matching closing brace by simple depth counting from the
        # first `{` after the signature -- a cheap proxy, not a real parser.
        brace_start = text.find("{", start)
        if brace_start == -1:
            continue
        depth = 0
        end = None
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end is None:
            continue
        body = text[brace_start:end]
        if f"{name}(" not in body[body.find("{") + 1 :]:
            continue
        if not re.search(rf"\b{re.escape(name)}\s*\(", body[1:]):
            continue
        if _DEPTH_GUARD_RE.search(body):
            continue
        line = text.count("\n", 0, match.start()) + 1
        findings.append(
            WebsecBoundsFinding(
                rule="WEBSEC125",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC125: {rel_path}:{line} function {name}(...) "
                    f"recurses with no depth/count/limit guard -- unbounded "
                    f"recursion on user-controlled input can exhaust the "
                    f"call stack (CWE-674) -- add a depth parameter with a "
                    f"max-depth early return, or `frob:waive WEBSEC125 "
                    f'reason="..."` with a real justification'
                ),
            )
        )
    return findings


# frob:doc docs/modules/webapp-websec-bounds.md#public-api
# frob:ticket T-5311
def websec_bounds_findings(root: Path) -> tuple[WebsecBoundsFinding, ...]:
    """WEBSEC123-125: every resource-exhaustion input-bounds finding under
    `root` (unbounded input length, XML/JSON bomb, unbounded recursion).

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all (T-5302's own contract), the same
    posture `frob.webapp._websec_sinks.websec_sink_findings` (T-5307)
    already follows.

    frob:ticket T-5311
    """
    root = Path(root)
    if not detect_frameworks(root):
        _log.debug("websec_bounds: no framework detected at %s, skipping scan", root)
        return ()

    findings: list[WebsecBoundsFinding] = []

    for rel in _tracked_files(root, ".py"):
        abs_path = root / rel
        findings.extend(_pydantic_field_findings(abs_path, root))
        findings.extend(_xxe_findings(abs_path, root))
        findings.extend(_py_recursion_findings(abs_path, root))
    for rel in _tracked_files(root, ".js", ".jsx", ".ts", ".tsx"):
        abs_path = root / rel
        findings.extend(_zod_findings(abs_path, root))
        findings.extend(_class_validator_findings(abs_path, root))
        findings.extend(_json_bomb_findings(abs_path, root))
        findings.extend(_js_recursion_findings(abs_path, root))

    _log.info("websec_bounds: %d finding(s) under %s", len(findings), root)
    return tuple(findings)
