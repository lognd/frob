"""WEBSEC326-334: auth-event/log-hygiene and outbound/server resource-
limit findings (T-5332, the T-5143 config/headers/supply-chain leaf's
logging+timeouts+resource-limits corpus -- docs/modules/webapp-websec-
logging-limits.md).

Same posture as `_websec_bounds.py`/`_websec_headers_log.py`: TEXT-REGEX
over tracked source files, short-circuiting to `()` when
`frob.webapp._detect.detect_frameworks` reports no web framework at all
(T-5302's contract every WEBSEC/COMPLY/A11Y/SEO/WEBPERF family already
follows). The `requests.*(...)`-call scan and the "body-parser call
missing an options key" scan below deliberately reuse the SAME call-
site/options-object shape `frob.webapp._websec_bounds` established for
WEBSEC121 (SSRF-adjacent redirect-following) and WEBSEC124 (JSON-bomb
body-parser limit) -- this module keeps its own tiny private regex
copies rather than importing those private helpers, the same "no cross-
module private imports" posture `_websec_headers_log.py`'s own docstring
documents (its private helpers are not part of its public surface).

NINE RULE IDS (T-5301's reserved `WEBSEC326`-`WEBSEC334` block; the
ticket body's fuller corpus -- log-retention policy and an outbound
egress allowlist, both config-posture checks with no single reliable
static shape across frameworks -- has no id left in this nine-id
reservation and is filed as follow-up scope, see the Done report; the
WebSocket origin/WSS rule stays owned by `_websec_headers_log.
websec_headers_log_findings` (WEBSEC122, T-5141-4) and is never
reimplemented here):

- WEBSEC326: auth-event audit logging -- a Python function whose name
  matches a login/logout/authenticate/password-reset shape has no
  logger call anywhere in its body (ASVS 5.0 V16.3.1/V16.3.2).
- WEBSEC327: log metadata completeness / UTC timestamps -- a logger
  call embeds `datetime.now()` (naive local time) rather than
  `utcnow()`/`timezone.utc`.
- WEBSEC328: PII in logs -- a logger call's message embeds a PII
  field-name-denylist token (ssn, social_security, credit_card,
  passport, date_of_birth/dob) as a literal or interpolated name.
- WEBSEC329: request body size limit missing -- an Express
  `bodyParser.json(...)`/`express.json(...)` call with no `limit` key
  in its options object (or no options object at all).
- WEBSEC330: outbound HTTP client timeout missing -- a
  `requests.get/post/put/delete/request(...)` call with no `timeout=`
  keyword argument.
- WEBSEC331: server request timeout missing -- an `app.run(...)`/
  `uvicorn.run(...)` server-start call with no `timeout`/
  `timeout_keep_alive` keyword argument.
- WEBSEC332: GraphQL introspection/depth limit missing -- an
  `ApolloServer(...)`/`GraphQLView.as_view(...)`/`graphene.Schema(...)`
  construction with no `introspection`/`validation_rules`/
  `depth_limit` reference anywhere in the same file.
- WEBSEC333: least-functionality -- a debug/test route path literal
  (`/debug`, `/__debug__`, `/test`) registered on a route decorator/
  call, or `debug=True` passed to a server-start call.
- WEBSEC334: client storage not cleared on logout -- a JS/TS
  logout/signOut handler function with no `localStorage`/
  `sessionStorage` clear/removeItem call anywhere in its body.

Each is WARN-tier at first turn-on, the same T-0688/T-0973 promotion
posture every sibling WEBSEC family follows.

WIRING: exposes the T-5308 `websec_findings(root, frameworks) ->
tuple[Violation, ...]` module-level hook, so `frob.gates._taint_gate.
taint_gate`'s `pkgutil`-based discovery picks this module up with no
`_taint_gate.py` edit.
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

__all__ = [
    "WebsecLoggingLimitsFinding",
    "websec_findings",
    "websec_logging_limits_findings",
]


# frob:doc docs/modules/webapp-websec-logging-limits.md#public-api
@dataclass(frozen=True)
class WebsecLoggingLimitsFinding:
    """One WEBSEC326-334 finding: an auth-event/log-hygiene gap or a
    missing outbound/server/body resource limit.

    frob:ticket T-5332
    """

    rule: str
    file: str
    line: int
    message: str


def _tracked_files(root: Path, *suffixes: str) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `suffixes`, root-relative
    POSIX paths, `()` on any git failure -- same tracked-file-scan shape
    every sibling `_websec_*` module uses.

    frob:ticket T-5332
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning(
            "websec_logging_limits: git ls-files failed: %s", spawned.danger_err
        )
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("websec_logging_limits: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(suffixes)
    )


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable.

    frob:ticket T-5332
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _line_of(text: str, offset: int) -> int:
    """1-based line number of char `offset` in `text`.

    frob:ticket T-5332
    """
    return text.count("\n", 0, offset) + 1


# --------------------------------------------------------------------------
# WEBSEC326: auth-event audit logging
# --------------------------------------------------------------------------

_AUTH_EVENT_NAME_RE = re.compile(
    r"^(login|logout|authenticate|sign_?in|sign_?out|reset_password|"
    r"password_reset|change_password)$",
    re.IGNORECASE,
)
_LOGGER_CALL_RE = re.compile(r"\b(log|logger)\.\w+\(")


def _auth_logging_findings(path: Path, root: Path) -> list[WebsecLoggingLimitsFinding]:
    """WEBSEC326: a Python auth-event function (login/logout/
    authenticate/password-reset shape) with no logger call anywhere in
    its own body.

    frob:ticket T-5332
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text:
        return []
    try:
        tree = ast.parse(text, filename=rel_path)
    except SyntaxError as exc:
        _log.debug("websec_logging_limits: skipping unparseable %s: %s", rel_path, exc)
        return []

    findings: list[WebsecLoggingLimitsFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _AUTH_EVENT_NAME_RE.match(node.name):
            continue
        body_source = ast.unparse(node)
        if _LOGGER_CALL_RE.search(body_source):
            continue
        findings.append(
            WebsecLoggingLimitsFinding(
                rule="WEBSEC326",
                file=rel_path,
                line=node.lineno,
                message=(
                    f"WEBSEC326: {rel_path}:{node.lineno} def "
                    f"{node.name}(...) is an auth-event handler with no "
                    f"logger call in its body -- ASVS 5.0 V16.3.1/V16.3.2 "
                    f"require auth events to be audit-logged. Add a "
                    f"logger.info/warning call, or `frob:waive WEBSEC326 "
                    f'reason="..."` with a real justification'
                ),
            )
        )
    return findings


# --------------------------------------------------------------------------
# WEBSEC327: log metadata completeness / UTC timestamps
# --------------------------------------------------------------------------

_LOG_NAIVE_NOW_RE = re.compile(r"\b(log|logger)\.\w+\([^)]*\bdatetime\.now\(\)[^)]*\)")


def _log_timestamp_findings(
    text: str, rel_path: str
) -> list[WebsecLoggingLimitsFinding]:
    """WEBSEC327: a logger call embeds `datetime.now()` (naive local
    time) rather than a UTC-shaped timestamp.

    frob:ticket T-5332
    """
    findings: list[WebsecLoggingLimitsFinding] = []
    for match in _LOG_NAIVE_NOW_RE.finditer(text):
        line = _line_of(text, match.start())
        findings.append(
            WebsecLoggingLimitsFinding(
                rule="WEBSEC327",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC327: {rel_path}:{line} a log call embeds "
                    f"datetime.now() (naive local time) -- log metadata "
                    f"must carry a UTC timestamp. Use "
                    f"datetime.now(timezone.utc)/datetime.utcnow(), or "
                    f'`frob:waive WEBSEC327 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


# --------------------------------------------------------------------------
# WEBSEC328: PII in logs
# --------------------------------------------------------------------------

#: PII field-name denylist -- extends T-5143-3's secret-pattern reuse
#: posture with a PII-specific token set rather than a credential shape.
_PII_FIELD_RE = re.compile(
    r"\b(ssn|social_security|credit_card|creditcard|passport|"
    r"date_of_birth|dob)\b",
    re.IGNORECASE,
)
_LOG_CALL_FULL_RE = re.compile(r"\b(?:log|logger)\.\w+\(([^)]*)\)")


def _pii_log_findings(text: str, rel_path: str) -> list[WebsecLoggingLimitsFinding]:
    """WEBSEC328: a logger call's message embeds a PII field-name-
    denylist token.

    frob:ticket T-5332
    """
    findings: list[WebsecLoggingLimitsFinding] = []
    for match in _LOG_CALL_FULL_RE.finditer(text):
        args = match.group(1)
        pii_match = _PII_FIELD_RE.search(args)
        if not pii_match:
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecLoggingLimitsFinding(
                rule="WEBSEC328",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC328: {rel_path}:{line} a log call embeds a "
                    f"PII field ({pii_match.group(0)!r}) -- PII must not "
                    f"reach logs in the clear. Redact/hash the value "
                    f'first, or `frob:waive WEBSEC328 reason="..."` with '
                    f"a real justification"
                ),
            )
        )
    return findings


# --------------------------------------------------------------------------
# WEBSEC329: request body size limit missing
# --------------------------------------------------------------------------

_BODY_PARSER_CALL_RE = re.compile(
    r"\b(?:bodyParser\.json|express\.json)\s*\(\s*(\{[^}]*\})?\s*\)"
)


def _body_size_limit_findings(
    text: str, rel_path: str
) -> list[WebsecLoggingLimitsFinding]:
    """WEBSEC329: an Express `bodyParser.json(...)`/`express.json(...)`
    call with no `limit` key in its options object -- request body size
    limit missing. Same call-site/options-object shape
    `frob.webapp._websec_bounds._json_bomb_findings` uses for WEBSEC124
    (a distinct concern -- resource exhaustion vs. an explicit size
    ceiling -- kept as its own rule id here).

    frob:ticket T-5332
    """
    if "bodyParser.json" not in text and "express.json" not in text:
        return []
    findings: list[WebsecLoggingLimitsFinding] = []
    for match in _BODY_PARSER_CALL_RE.finditer(text):
        options = match.group(1) or ""
        if "limit" in options:
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecLoggingLimitsFinding(
                rule="WEBSEC329",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC329: {rel_path}:{line} JSON body parser "
                    f"configured with no `limit` option -- unbounded "
                    f"request body size. Pass a `limit` option, or "
                    f'`frob:waive WEBSEC329 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


# --------------------------------------------------------------------------
# WEBSEC330: outbound HTTP client timeout missing
# --------------------------------------------------------------------------

_REQUESTS_CALL_RE = re.compile(
    r"requests\.(?:get|post|put|delete|request)\(\s*([^)]*)\)"
)


def _outbound_timeout_findings(
    text: str, rel_path: str
) -> list[WebsecLoggingLimitsFinding]:
    """WEBSEC330: a `requests.get/post/put/delete/request(...)` call
    with no `timeout=` keyword argument.

    frob:ticket T-5332
    """
    findings: list[WebsecLoggingLimitsFinding] = []
    for match in _REQUESTS_CALL_RE.finditer(text):
        args = match.group(1)
        if "timeout" in args:
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecLoggingLimitsFinding(
                rule="WEBSEC330",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC330: {rel_path}:{line} an outbound HTTP call "
                    f"has no timeout= keyword argument -- a hung "
                    f"upstream can exhaust worker threads (CWE-400). "
                    f"Pass timeout=, or `frob:waive WEBSEC330 "
                    f'reason="..."` with a real justification'
                ),
            )
        )
    return findings


# --------------------------------------------------------------------------
# WEBSEC331: server request timeout missing (config)
# --------------------------------------------------------------------------

_SERVER_RUN_CALL_RE = re.compile(r"\b(?:app\.run|uvicorn\.run)\(\s*([^)]*)\)")


def _server_timeout_findings(
    text: str, rel_path: str
) -> list[WebsecLoggingLimitsFinding]:
    """WEBSEC331: an `app.run(...)`/`uvicorn.run(...)` server-start call
    with no `timeout`/`timeout_keep_alive` keyword argument.

    frob:ticket T-5332
    """
    findings: list[WebsecLoggingLimitsFinding] = []
    for match in _SERVER_RUN_CALL_RE.finditer(text):
        args = match.group(1)
        if "timeout" in args:
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecLoggingLimitsFinding(
                rule="WEBSEC331",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC331: {rel_path}:{line} a server-start call "
                    f"has no request timeout configured -- a slow client "
                    f"can hold a worker open indefinitely (CWE-400). "
                    f"Pass timeout/timeout_keep_alive, or `frob:waive "
                    f'WEBSEC331 reason="..."` with a real justification'
                ),
            )
        )
    return findings


# --------------------------------------------------------------------------
# WEBSEC332: GraphQL introspection/depth limit missing (config)
# --------------------------------------------------------------------------

_GRAPHQL_SETUP_RE = re.compile(
    r"\b(ApolloServer|GraphQLView\.as_view|graphene\.Schema)\s*\("
)
_GRAPHQL_GUARD_RE = re.compile(
    r"introspection|validation_rules|depth_limit", re.IGNORECASE
)


def _graphql_findings(text: str, rel_path: str) -> list[WebsecLoggingLimitsFinding]:
    """WEBSEC332: a GraphQL server construction with no introspection/
    depth-limit reference anywhere in the same file.

    frob:ticket T-5332
    """
    match = _GRAPHQL_SETUP_RE.search(text)
    if not match:
        return []
    if _GRAPHQL_GUARD_RE.search(text):
        return []
    line = _line_of(text, match.start())
    return [
        WebsecLoggingLimitsFinding(
            rule="WEBSEC332",
            file=rel_path,
            line=line,
            message=(
                f"WEBSEC332: {rel_path}:{line} a GraphQL server is "
                f"constructed with no introspection/depth-limit "
                f"reference anywhere in the file -- introspection and "
                f"unbounded query depth are enabled by default. Disable "
                f"introspection in production and add a depth-limit "
                f'validation rule, or `frob:waive WEBSEC332 reason="..."` '
                f"with a real justification"
            ),
        )
    ]


# --------------------------------------------------------------------------
# WEBSEC333: least-functionality -- debug/test routes in prod
# --------------------------------------------------------------------------

_DEBUG_ROUTE_RE = re.compile(r"""["'](/(?:debug|__debug__|test)[/"']?[^"']*)["']""")
_DEBUG_TRUE_RE = re.compile(r"\bdebug\s*=\s*True\b")


def _debug_route_findings(text: str, rel_path: str) -> list[WebsecLoggingLimitsFinding]:
    """WEBSEC333: a debug/test route path literal, or `debug=True`
    passed to a server-start call -- least-functionality violation (a
    debug/test surface reachable in a production route table).

    frob:ticket T-5332
    """
    findings: list[WebsecLoggingLimitsFinding] = []
    for match in _DEBUG_ROUTE_RE.finditer(text):
        line = _line_of(text, match.start())
        findings.append(
            WebsecLoggingLimitsFinding(
                rule="WEBSEC333",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC333: {rel_path}:{line} a debug/test route "
                    f"path ({match.group(1)!r}) is registered -- "
                    f"least-functionality requires debug/test routes "
                    f"stay out of the production route table. Remove it "
                    f"or guard it behind an env check, or `frob:waive "
                    f'WEBSEC333 reason="..."` with a real justification'
                ),
            )
        )
    for match in _DEBUG_TRUE_RE.finditer(text):
        line = _line_of(text, match.start())
        findings.append(
            WebsecLoggingLimitsFinding(
                rule="WEBSEC333",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC333: {rel_path}:{line} debug=True is passed "
                    f"to a server-start call -- a debug server exposes "
                    f"stack traces/an interactive debugger in production. "
                    f"Guard it behind an env check, or `frob:waive "
                    f'WEBSEC333 reason="..."` with a real justification'
                ),
            )
        )
    return findings


# --------------------------------------------------------------------------
# WEBSEC334: client storage not cleared on logout
# --------------------------------------------------------------------------

_LOGOUT_FUNCTION_RE = re.compile(
    r"\bfunction\s+(logout|signOut|sign_out)\s*\(|"
    r"\bconst\s+(logout|signOut|sign_out)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>"
)
_STORAGE_CLEAR_RE = re.compile(r"(localStorage|sessionStorage)\.(clear|removeItem)\(")


def _client_storage_findings(
    text: str, rel_path: str
) -> list[WebsecLoggingLimitsFinding]:
    """WEBSEC334: a JS/TS logout/signOut handler function with no
    `localStorage`/`sessionStorage` clear/removeItem call anywhere in
    its own body -- same brace-matching body-extraction shape
    `frob.webapp._websec_bounds._js_recursion_findings` uses for
    WEBSEC125.

    frob:ticket T-5332
    """
    findings: list[WebsecLoggingLimitsFinding] = []
    for match in _LOGOUT_FUNCTION_RE.finditer(text):
        name = match.group(1) or match.group(2)
        brace_start = text.find("{", match.end())
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
        if _STORAGE_CLEAR_RE.search(body):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecLoggingLimitsFinding(
                rule="WEBSEC334",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC334: {rel_path}:{line} function {name}(...) "
                    f"is a logout handler with no localStorage/"
                    f"sessionStorage clear/removeItem call in its body -- "
                    f"stale client-side session data survives logout. "
                    f"Clear client storage on logout, or `frob:waive "
                    f'WEBSEC334 reason="..."` with a real justification'
                ),
            )
        )
    return findings


def _py_file_findings(path: Path, root: Path) -> list[WebsecLoggingLimitsFinding]:
    """Every Python-source WEBSEC326-334 finding in one file.

    frob:ticket T-5332
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text:
        return []
    findings: list[WebsecLoggingLimitsFinding] = []
    findings.extend(_auth_logging_findings(path, root))
    findings.extend(_log_timestamp_findings(text, rel_path))
    findings.extend(_pii_log_findings(text, rel_path))
    findings.extend(_outbound_timeout_findings(text, rel_path))
    findings.extend(_server_timeout_findings(text, rel_path))
    findings.extend(_debug_route_findings(text, rel_path))
    return findings


def _js_file_findings(path: Path, root: Path) -> list[WebsecLoggingLimitsFinding]:
    """Every JS/TS-source WEBSEC326-334 finding in one file.

    frob:ticket T-5332
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text:
        return []
    findings: list[WebsecLoggingLimitsFinding] = []
    findings.extend(_pii_log_findings(text, rel_path))
    findings.extend(_body_size_limit_findings(text, rel_path))
    findings.extend(_graphql_findings(text, rel_path))
    findings.extend(_debug_route_findings(text, rel_path))
    findings.extend(_client_storage_findings(text, rel_path))
    return findings


# frob:doc docs/modules/webapp-websec-logging-limits.md#public-api
# frob:ticket T-5332
def websec_logging_limits_findings(
    root: Path,
) -> tuple[WebsecLoggingLimitsFinding, ...]:
    """WEBSEC326-334: every auth-event/log-hygiene or outbound/server/
    body resource-limit finding under `root`.

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all (T-5302's own contract, same
    posture every sibling WEBSEC family follows).

    frob:ticket T-5332
    """
    root = Path(root)
    if not detect_frameworks(root):
        _log.debug(
            "websec_logging_limits: no framework detected at %s, skipping scan", root
        )
        return ()

    findings: list[WebsecLoggingLimitsFinding] = []
    for rel in _tracked_files(root, ".py"):
        findings.extend(_py_file_findings(root / rel, root))
    for rel in _tracked_files(root, ".js", ".jsx", ".ts", ".tsx"):
        findings.extend(_js_file_findings(root / rel, root))

    _log.info("websec_logging_limits: %d finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/webapp-websec-logging-limits.md#public-api
# frob:ticket T-5332
def websec_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """T-5308's `taint_gate` module-discovery hook: every
    `frob.webapp._websec_*` module exposing a module-level
    `websec_findings(root, frameworks) -> tuple[Violation, ...]` is
    auto-discovered and folded into `taint_gate`'s scan, so this WEBSEC
    family never needs its own `_taint_gate.py` edit. `frameworks` is
    the caller's own already-computed `detect_frameworks(root)` result
    (avoids a second detect call per discovered module) -- an empty set
    short-circuits to `()` exactly like `websec_logging_limits_findings`'s
    own direct-call contract.

    frob:ticket T-5332
    """
    if not frameworks:
        _log.debug(
            "websec_logging_limits: no framework detected at %s, skipping scan (hook)",
            root,
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
        for finding in websec_logging_limits_findings(root)
    )
