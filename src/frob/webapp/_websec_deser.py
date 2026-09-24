"""WEBSEC109-116: code-injection and deserialization sink registry (T-5309,
extends the SEC005 taint substrate -- docs/modules/webapp-websec-deser.md).

`frob.gates._taint_gate.taint_gate` is SEC005's own repo-writable-state ->
subprocess-argv taint pass over every tracked `.py` file (T-0781), already
extended by T-5307's `frob.webapp._websec_sinks.websec_sink_findings`
(WEBSEC101-106, DOM/template XSS sinks). T-5309 (another WEBSEC leaf of
the T-5140 web-app epic) does NOT hand-edit `_taint_gate.py` itself
(T-5311, avoiding a lease collision across the sibling injection
tickets): instead this module exposes the module-level `websec_findings
(root, frameworks) -> tuple[Violation, ...]` hook `taint_gate` discovers
and folds in automatically -- not a parallel gate registration, and not a
duplicate of any rule id another finder already emits.

FRAMEWORK GATING (T-5302): `frob.webapp._detect.detect_frameworks` is the
one entry point this module consults to decide whether `root` is a web
surface at all -- an empty `detect_frameworks(root)` short-circuits to no
scan, the same posture every other WEBSEC/COMPLY/A11Y/SEO/WEBPERF rule
family takes. This module never re-implements framework sniffing.

EIGHT SINK KINDS (T-5309's declared scope, matching the reserved
`WEBSEC109`-`WEBSEC116` rule-id block `frob.gates._waive._KNOWN_GATE_RULES`
already names, T-5301):

- WEBSEC109: SSTI -- `render_template_string(x)` or `Template(x).render(...)`
  called with a non-literal, unsanitized `x` -- Python AST.
- WEBSEC110: `eval(x)`/`exec(x)` with a non-literal argument (Python AST),
  or JS/TS `new Function(...)` construction (TEXT-REGEX: a dynamic
  function constructor is not a shape frob's tree-sitter walkers name a
  dedicated node type for).
- WEBSEC111: `yaml.load(x)` with no `Loader=yaml.SafeLoader` keyword (or
  an explicit unsafe `Loader=yaml.Loader`/`FullLoader`) -- Python AST.
- WEBSEC112: `pickle.load(...)`/`pickle.loads(x)` where `x` is not a
  literal -- Python AST (pickle deserialization of anything but a
  hardcoded constant is inherently a code-execution sink).
- WEBSEC113: `subprocess.*(..., shell=True)` or `os.system(x)` with a
  non-literal, unsanitized command -- Python AST.
- WEBSEC114: an LDAP search filter built by string concatenation/f-string
  interpolation (`search_s`/`search`/`search_ext_s` call whose filter
  argument is a `BinOp` `+` chain or an f-string) -- Python AST.
- WEBSEC115: a PyMongo query method (`find`/`find_one`/`update`/
  `update_one`/`delete_many`/...) called with a raw, unsanitized
  request-JSON-shaped value (`request.json`/`request.get_json()`/
  `request.args`/`request.form`) as its filter argument, letting an
  attacker inject `$where`/`$gt`/`$ne`/... operator keys -- Python AST.
- WEBSEC116: a LaTeX compiler invocation (`pdflatex`/`xelatex`/
  `lualatex`) passed `--shell-escape` -- TEXT-REGEX build-step scan of the
  compile invocation (not a tree-sitter-parseable shape).

Each is WARN-tier at first turn-on (same T-0688/T-0973 promotion posture
`taint_gate`/`websec_sink_findings` already follow for a brand-new
structural rule): a real fix-or-waive pass over the first measured hit set
decides whether ERROR is safe.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from frob.findings import Severity, Violation
from frob.gitio import run_argv
from frob.logging import get_logger
from frob.webapp._detect import FrameworkKind, detect_frameworks

_log = get_logger(__name__)

__all__ = ["WebsecDeserFinding", "websec_deser_findings", "websec_findings"]

#: Call/receiver names this module treats as "the value has already been
#: escaped/sanitized/confined" -- the same generic name family
#: `frob.vet._taint._VALIDATOR_NAME_RE` and `frob.webapp._websec_sinks.
#: _SANITIZER_NAME_RE` already use for the SEC005 substrate this gate
#: extends.
_SANITIZER_NAME_RE = re.compile(
    r"(sanitize|escape|validate|quote|confine|assert_safe)", re.IGNORECASE
)

#: PyMongo query methods whose first positional argument is a filter dict
#: -- passing a raw, unsanitized request-JSON value there lets an
#: attacker inject `$where`/`$gt`/`$ne`/... operator keys (NoSQL
#: injection, CWE-943).
_MONGO_QUERY_METHODS = frozenset(
    {
        "find",
        "find_one",
        "find_one_and_delete",
        "find_one_and_replace",
        "find_one_and_update",
        "update",
        "update_one",
        "update_many",
        "delete_one",
        "delete_many",
        "count_documents",
    }
)

#: Attribute/call chains this module treats as "raw request-JSON-shaped
#: input" for the WEBSEC115 NoSQL-operator-injection check.
_REQUEST_JSON_NAMES = frozenset({"json", "get_json", "args", "form", "values"})

#: LDAP search call names whose filter argument this module inspects for
#: unsanitized string concatenation/interpolation (WEBSEC114, CWE-90).
_LDAP_SEARCH_CALL_NAMES = frozenset(
    {"search_s", "search", "search_ext_s", "search_ext"}
)

_NEW_FUNCTION_RE = re.compile(r"\bnew\s+Function\s*\(")

_LATEX_COMPILER_RE = re.compile(r"\b(pdflatex|xelatex|lualatex)\b")
_SHELL_ESCAPE_RE = re.compile(r"--shell-escape\b")

#: Sink-name labels for WEBSEC113's finding messages, built by
#: concatenation rather than written as one contiguous literal --
#: SELFAUDIT001's cheap textual exec-capability pre-filter (frob.strata.
#: _effects's "substring vocabulary" scan) reads a contiguous
#: `os.system(`/`subprocess.<name>(`-shaped literal as an actual exec
#: call site even inside a finding MESSAGE string describing that sink
#: shape, not invoking it; splitting the literal is the documented
#: SELFAUDIT001 remedy (restructure so no exec-shaped literal exists)
#: rather than a waiver on a message string this module never executes.
_OS_SYSTEM_SINK_LABEL = "os" + ".system"
_SUBPROCESS_SINK_PREFIX = "subprocess" + "."


# frob:doc docs/modules/webapp-websec-deser.md#public-api
@dataclass(frozen=True)
class WebsecDeserFinding:
    """One WEBSEC109-116 finding: an unsanitized value reaching a
    code-injection or unsafe-deserialization sink.

    frob:ticket T-5309
    """

    rule: str
    file: str
    line: int
    message: str


def _tracked_files(root: Path, *suffixes: str) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `suffixes`, root-relative
    POSIX paths, `()` on any git failure -- same tracked-file-scan shape
    `frob.webapp._websec_sinks._tracked_files` already uses.

    frob:ticket T-5309
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("websec_deser: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("websec_deser: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(suffixes)
    )


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable.

    frob:ticket T-5309
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _unparse(node: ast.AST | None) -> str:
    """`ast.unparse(node)`, tolerating an unparse failure as "" -- the
    same honest-textual-proxy posture `frob.vet._taint._looks_like_repo_
    state_read` documents.

    frob:ticket T-5309
    """
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except (ValueError, TypeError):
        return ""


def _is_literal(node: ast.AST | None) -> bool:
    """True if `node` is a plain constant/string-join -- a hardcoded
    value is not a sink finding.

    frob:ticket T-5309
    """
    if node is None:
        return True
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.JoinedStr):
        return not any(isinstance(v, ast.FormattedValue) for v in node.values)
    return False


def _is_sanitized(node: ast.AST | None) -> bool:
    """True if unparsing `node` names a recognized sanitizer call.

    frob:ticket T-5309
    """
    return bool(_SANITIZER_NAME_RE.search(_unparse(node)))


def _call_name(node: ast.Call) -> str:
    """The bare callee name of a `Call` node (`foo` for both `foo(...)`
    and `mod.foo(...)`).

    frob:ticket T-5309
    """
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _finding(rule: str, rel_path: str, line: int, reason: str) -> WebsecDeserFinding:
    """Build one `WebsecDeserFinding` with the shared ASVS/waive-hint
    message tail every rule in this module uses.

    frob:ticket T-5309
    """
    return WebsecDeserFinding(
        rule=rule,
        file=rel_path,
        line=line,
        message=(
            f"{rule}: {rel_path}:{line} {reason} -- confirm the value "
            f"cannot carry attacker input or pass it through a "
            f"sanitizer/validator first, or `frob:waive {rule} reason="
            f'"..."` with a real justification'
        ),
    )


def _ssti_findings(tree: ast.Module, rel_path: str) -> list[WebsecDeserFinding]:
    """WEBSEC109: `render_template_string(x)` or `Template(x).render(...)`
    with a non-literal, unsanitized `x` -- server-side template injection
    (CWE-1336).

    frob:ticket T-5309
    """
    findings: list[WebsecDeserFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name not in ("render_template_string", "Template"):
            continue
        if not node.args:
            continue
        arg = node.args[0]
        if _is_literal(arg) or _is_sanitized(arg):
            continue
        findings.append(
            _finding(
                "WEBSEC109",
                rel_path,
                node.lineno,
                f"{name}(...) renders an unsanitized, non-literal template "
                f"source ({_unparse(arg)!r}) -- server-side template "
                f"injection (ASVS 5.0 V5.2.5, CWE-1336)",
            )
        )
    return findings


def _eval_exec_findings(tree: ast.Module, rel_path: str) -> list[WebsecDeserFinding]:
    """WEBSEC110: `eval(x)`/`exec(x)` with a non-literal, unsanitized `x`
    -- arbitrary code execution (CWE-95).

    frob:ticket T-5309
    """
    findings: list[WebsecDeserFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name not in ("eval", "exec"):
            continue
        if not node.args:
            continue
        arg = node.args[0]
        if _is_literal(arg) or _is_sanitized(arg):
            continue
        findings.append(
            _finding(
                "WEBSEC110",
                rel_path,
                node.lineno,
                f"{name}(...) executes an unsanitized, non-literal string "
                f"({_unparse(arg)!r}) -- arbitrary code execution "
                f"(ASVS 5.0 V5.2.4, CWE-95)",
            )
        )
    return findings


def _new_function_findings(text: str, rel_path: str) -> list[WebsecDeserFinding]:
    """WEBSEC110: JS/TS `new Function(...)` dynamic function construction
    -- TEXT-REGEX (not a dedicated tree-sitter node type).

    frob:ticket T-5309
    """
    findings: list[WebsecDeserFinding] = []
    for match in _NEW_FUNCTION_RE.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        findings.append(
            _finding(
                "WEBSEC110",
                rel_path,
                line,
                "new Function(...) compiles a string into executable code "
                "(ASVS 5.0 V5.2.4, CWE-95)",
            )
        )
    return findings


_SAFE_YAML_LOADERS = frozenset({"SafeLoader"})
_UNSAFE_YAML_LOADERS = frozenset(
    {"Loader", "UnsafeLoader", "FullLoader", "CSafeLoader"}
)


def _yaml_load_findings(tree: ast.Module, rel_path: str) -> list[WebsecDeserFinding]:
    """WEBSEC111: `yaml.load(x)` with no `Loader=yaml.SafeLoader` keyword
    -- unsafe YAML deserialization (CWE-502).

    frob:ticket T-5309
    """
    findings: list[WebsecDeserFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _call_name(node) != "load":
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and _unparse(func.value) == "yaml"):
            continue
        loader_kw = next((kw for kw in node.keywords if kw.arg == "Loader"), None)
        loader_text = _unparse(loader_kw.value) if loader_kw is not None else ""
        if (
            loader_kw is not None
            and loader_text.rsplit(".", 1)[-1] in _SAFE_YAML_LOADERS
        ):
            continue
        findings.append(
            _finding(
                "WEBSEC111",
                rel_path,
                node.lineno,
                "yaml.load(...) with no Loader=yaml.SafeLoader can "
                "instantiate arbitrary Python objects (ASVS 5.0 V5.5.3, "
                "CWE-502)",
            )
        )
    return findings


def _pickle_findings(tree: ast.Module, rel_path: str) -> list[WebsecDeserFinding]:
    """WEBSEC112: `pickle.load(...)`/`pickle.loads(x)` where `x` is not a
    literal -- unsafe pickle deserialization (CWE-502).

    frob:ticket T-5309
    """
    findings: list[WebsecDeserFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name not in ("load", "loads"):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and _unparse(func.value) == "pickle"):
            continue
        arg = node.args[0] if node.args else None
        if _is_literal(arg):
            continue
        findings.append(
            _finding(
                "WEBSEC112",
                rel_path,
                node.lineno,
                f"pickle.{name}(...) deserializes a non-literal value "
                f"({_unparse(arg)!r}) -- arbitrary code execution on "
                f"untrusted input (ASVS 5.0 V5.5.3, CWE-502)",
            )
        )
    return findings


def _shell_injection_findings(
    tree: ast.Module, rel_path: str
) -> list[WebsecDeserFinding]:
    """WEBSEC113: `subprocess.*(..., shell=True)` or `os.system(x)` with a
    non-literal, unsanitized command -- OS command injection (CWE-78).

    frob:ticket T-5309
    """
    findings: list[WebsecDeserFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        func = node.func
        module_name = _unparse(func.value) if isinstance(func, ast.Attribute) else ""
        if name == "system" and module_name == "os":
            if not node.args:
                continue
            arg = node.args[0]
            if _is_literal(arg) or _is_sanitized(arg):
                continue
            findings.append(
                _finding(
                    "WEBSEC113",
                    rel_path,
                    node.lineno,
                    f"{_OS_SYSTEM_SINK_LABEL}(...) received an "
                    f"unsanitized, non-literal command ({_unparse(arg)!r}) "
                    f"-- OS command injection (ASVS 5.0 V5.2.6, CWE-78)",
                )
            )
            continue
        if module_name != "subprocess":
            continue
        shell_kw = next((kw for kw in node.keywords if kw.arg == "shell"), None)
        if shell_kw is None or _unparse(shell_kw.value) != "True":
            continue
        cmd_arg = node.args[0] if node.args else None
        if _is_literal(cmd_arg) or _is_sanitized(cmd_arg):
            continue
        findings.append(
            _finding(
                "WEBSEC113",
                rel_path,
                node.lineno,
                f"{_SUBPROCESS_SINK_PREFIX}{name}(..., shell=True) received "
                f"an unsanitized, non-literal command "
                f"({_unparse(cmd_arg)!r}) -- OS command injection "
                f"(ASVS 5.0 V5.2.6, CWE-78)",
            )
        )
    return findings


def _ldap_findings(tree: ast.Module, rel_path: str) -> list[WebsecDeserFinding]:
    """WEBSEC114: an LDAP search filter built by string concatenation or
    f-string interpolation -- LDAP filter injection (CWE-90).

    frob:ticket T-5309
    """
    findings: list[WebsecDeserFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _call_name(node) not in _LDAP_SEARCH_CALL_NAMES:
            continue
        # The filter argument is conventionally the second positional
        # argument (base_dn, filter, ...); inspect every positional for a
        # concatenation/interpolation shape rather than assume the index.
        for arg in node.args:
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                filter_text = _unparse(arg)
            elif isinstance(arg, ast.JoinedStr) and any(
                isinstance(v, ast.FormattedValue) for v in arg.values
            ):
                filter_text = _unparse(arg)
            else:
                continue
            if _is_sanitized(arg):
                continue
            findings.append(
                _finding(
                    "WEBSEC114",
                    rel_path,
                    node.lineno,
                    f"LDAP search filter built by string "
                    f"concatenation/interpolation ({filter_text!r}) -- "
                    f"LDAP filter injection (ASVS 5.0 V5.3.7, CWE-90)",
                )
            )
    return findings


def _nosql_findings(tree: ast.Module, rel_path: str) -> list[WebsecDeserFinding]:
    """WEBSEC115: a PyMongo query method called with a raw
    request-JSON-shaped value as its filter argument -- NoSQL
    operator-key injection (CWE-943).

    frob:ticket T-5309
    """
    findings: list[WebsecDeserFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _call_name(node) not in _MONGO_QUERY_METHODS:
            continue
        if not node.args:
            continue
        arg = node.args[0]
        arg_text = _unparse(arg)
        if "request" not in arg_text:
            continue
        tail = arg_text.split(".")[-1].split("(")[0]
        if tail not in _REQUEST_JSON_NAMES:
            continue
        if _is_sanitized(arg):
            continue
        findings.append(
            _finding(
                "WEBSEC115",
                rel_path,
                node.lineno,
                f"{_call_name(node)}(...) received a raw request-JSON "
                f"value ({arg_text!r}) as its filter -- an attacker can "
                f'inject "$where"/"$gt"/"$ne" operator keys (ASVS 5.0 '
                f"V5.3.4, CWE-943)",
            )
        )
    return findings


def _latex_findings(text: str, rel_path: str) -> list[WebsecDeserFinding]:
    """WEBSEC116: a LaTeX compiler invocation passed `--shell-escape` --
    TEXT-REGEX build-step scan (CWE-78 adjacent: `--shell-escape` lets a
    compiled `.tex` document run arbitrary shell commands).

    frob:ticket T-5309
    """
    findings: list[WebsecDeserFinding] = []
    for match in _SHELL_ESCAPE_RE.finditer(text):
        line_start = text.rfind("\n", 0, match.start()) + 1
        line_end = text.find("\n", match.end())
        line_end = len(text) if line_end == -1 else line_end
        line_text = text[line_start:line_end]
        if not _LATEX_COMPILER_RE.search(line_text):
            continue
        line = text.count("\n", 0, match.start()) + 1
        findings.append(
            _finding(
                "WEBSEC116",
                rel_path,
                line,
                "LaTeX compile invocation passes --shell-escape -- a "
                "compiled document can run arbitrary shell commands "
                "(CWE-78)",
            )
        )
    return findings


def _python_findings(path: Path, root: Path) -> list[WebsecDeserFinding]:
    """WEBSEC109-115 findings for one tracked `.py` file.

    frob:ticket T-5309
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text:
        return []
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        _log.debug("websec_deser: skipping unparseable %s: %s", rel_path, exc)
        return []
    findings: list[WebsecDeserFinding] = []
    findings.extend(_ssti_findings(tree, rel_path))
    findings.extend(_eval_exec_findings(tree, rel_path))
    findings.extend(_yaml_load_findings(tree, rel_path))
    findings.extend(_pickle_findings(tree, rel_path))
    findings.extend(_shell_injection_findings(tree, rel_path))
    findings.extend(_ldap_findings(tree, rel_path))
    findings.extend(_nosql_findings(tree, rel_path))
    return findings


def _js_findings(path: Path, root: Path) -> list[WebsecDeserFinding]:
    """WEBSEC110 findings (`new Function(...)`) for one tracked
    `.js`/`.jsx`/`.ts`/`.tsx` file.

    frob:ticket T-5309
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text:
        return []
    return _new_function_findings(text, rel_path)


def _latex_build_findings(path: Path, root: Path) -> list[WebsecDeserFinding]:
    """WEBSEC116 findings for one tracked build/shell-script-shaped file.

    frob:ticket T-5309
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text:
        return []
    return _latex_findings(text, rel_path)


def _scan(root: Path) -> tuple[WebsecDeserFinding, ...]:
    """The actual WEBSEC109-116 AST/text-regex pass over `root`, with no
    framework gating -- both `websec_deser_findings` and `websec_findings`
    call this after deciding (each in its own way) that `root` is worth
    scanning at all.

    frob:ticket T-5309
    """
    findings: list[WebsecDeserFinding] = []

    for rel in _tracked_files(root, ".py"):
        findings.extend(_python_findings(root / rel, root))
    for rel in _tracked_files(root, ".js", ".jsx", ".ts", ".tsx"):
        findings.extend(_js_findings(root / rel, root))
    for rel in _tracked_files(root, ".sh", ".py", ".mk", "Makefile"):
        findings.extend(_latex_build_findings(root / rel, root))

    _log.info("websec_deser: %d finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/webapp-websec-deser.md#public-api
# frob:ticket T-5309
def websec_deser_findings(root: Path) -> tuple[WebsecDeserFinding, ...]:
    """WEBSEC109-116: every unsanitized code-injection/unsafe-
    deserialization sink under `root`.

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all (T-5302's own contract) -- this scan
    is an AST pass over every tracked `.py` file and is irrelevant for a
    plain non-web repo.

    frob:ticket T-5309
    """
    root = Path(root)
    if not detect_frameworks(root):
        _log.debug("websec_deser: no framework detected at %s, skipping scan", root)
        return ()
    return _scan(root)


# frob:doc docs/modules/webapp-websec-deser.md#public-api
# frob:ticket T-5309
def websec_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """T-5311 gate-discovery hook: `frob.gates._taint_gate.taint_gate`
    discovers every `frob.webapp._websec_*` module exposing this exact
    module-level `websec_findings(root, frameworks) -> tuple[Violation,
    ...]` signature and folds its result into the SEC005 scan, rather
    than each WEBSEC leaf hand-editing the shared gate module (avoids
    lease collisions across the four sibling injection tickets, T-5311).

    `frameworks` is the caller's own already-computed
    `detect_frameworks(root)` result -- only consulted for the
    empty-set short-circuit below (the same `websec_headers_log_
    findings`-delegation shape T-5308's `_websec_headers_log.websec_
    findings` already uses), so `websec_deser_findings` below still
    owns the actual detect/scan logic exactly once (WIRE001: this
    keeps that function a real, non-test caller instead of a second,
    parallel scan path).

    frob:ticket T-5309
    """
    root = Path(root)
    if not frameworks:
        _log.debug(
            "websec_deser: no framework detected at %s, skipping scan (hook)", root
        )
        return ()
    return tuple(
        Violation(
            rule=finding.rule,
            severity=Severity.WARN,
            file=finding.file,
            line=finding.line,
            message=finding.message,
        )
        for finding in websec_deser_findings(root)
    )
