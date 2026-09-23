"""WEBSEC117-122: response-header/URL/log injection and WebSocket origin
enforcement (docs/modules/webapp-websec-headers-log.md, T-5308, the
`T-5140` web-app epic's header/URL/log-injection leaf, blocked on and
downstream of T-5307's `frob.webapp._websec_sinks` DOM/template XSS sink
family this module sits alongside).

Same posture as `_websec_sinks.py`: TEXT-REGEX over tracked source files,
short-circuiting to `()` when `frob.webapp._detect.detect_frameworks`
reports no web framework at all (T-5302's contract every WEBSEC/COMPLY/
A11Y/SEO/WEBPERF family already follows), and reusing that module's
tracked-file-scan/read-text helper shapes rather than re-implementing
them (this module intentionally keeps its own tiny private copies since
`_websec_sinks` private helpers are not part of its public surface --
see `docs/modules/webapp-websec-injection.md`'s own "no cross-module
private imports" posture, `_tracked_files`/`_read_text` here are one-line
mirrors, not a new abstraction).

SIX RULE IDS (T-5301's reserved `WEBSEC117`-`WEBSEC122` block; the ticket
body's fuller corpus -- HTML injection in transactional email, field
over-exposure via `jsonify(model.__dict__)` -- has no id left in this
six-id reservation and is filed as follow-up scope, see the Done report):

- WEBSEC117: CRLF/response-header injection -- `response.setHeader(...)`/
  `res.setHeader(...)`/`.headers[...] = ...` assigned a request-derived,
  unsanitized value with no CR/LF-stripping encoder in between (ASVS 5.0
  V13.2.1-shaped, CWE-113).
- WEBSEC118: URL-building injection -- a URL string built by concatenating
  or f-string-interpolating request-derived data with no
  `urlencode`/`quote` call and no scheme allowlist check (CWE-601-
  adjacent open-redirect/SSRF-seeding shape).
- WEBSEC119: log injection -- a logger call whose message embeds
  request-derived data via f-string/concatenation with no CR/LF-stripping
  encoder (`%r`/`repr`/`quote`) in between (ASVS 5.0 V7.2-shaped,
  CWE-117).
- WEBSEC120: `Content-Disposition`/filename header built from a
  request-derived value with no RFC 6266 percent-encoding
  (`quote`/`urlencode`) applied first.
- WEBSEC121: backend follows a redirect from a request-derived URL
  (`requests.get/post/request(<request-derived url>, ...)` with
  `allow_redirects` left at its library default `True`) -- SSRF-adjacent.
- WEBSEC122: WebSocket origin-check/WSS-only enforcement (ASVS 5.0
  V4.4.1/V4.4.2) -- this leaf is the canonical owner of the WebSocket-
  origin rule id (T-5143-5 cross-references this id rather than
  reimplementing it): a `new WebSocket("ws://...")` literal insecure
  scheme, or a WebSocket connection handler with no `origin` reference
  anywhere in the same file.

Each is WARN-tier at first turn-on, the same T-0688/T-0973 promotion
posture `taint_gate`/`opaque_gate`/T-5307's `websec_sink_findings`
already follow for a brand-new structural rule.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from frob.findings import Severity, Violation
from frob.gitio import run_argv
from frob.logging import get_logger
from frob.webapp._detect import FrameworkKind, detect_frameworks

_log = get_logger(__name__)

__all__ = [
    "WebsecHeaderLogFinding",
    "websec_findings",
    "websec_headers_log_findings",
]


# frob:doc docs/modules/webapp-websec-headers-log.md#public-api
@dataclass(frozen=True)
class WebsecHeaderLogFinding:
    """One WEBSEC117-122 finding: an unsanitized request-derived value
    reaching a response-header/URL/log/WebSocket sink.

    frob:ticket T-5308
    """

    rule: str
    file: str
    line: int
    message: str


#: Call/expression fragments that indicate the captured expression has
#: already been through a CR/LF-stripping or percent-encoding hop --
#: clears an otherwise-tainted match, same "textual proxy" posture
#: `_websec_sinks._SANITIZER_NAME_RE` uses.
_ENCODED_RE = re.compile(
    r"(urlencode|quote|shlex\.quote|repr\(|%r|sanitize|escape|strip\(\s*\)|"
    r"replace\(\s*[\"']\\r|replace\(\s*[\"']\\n)",
    re.IGNORECASE,
)

#: Request-derived source expressions this module treats as attacker-
#: influenced: Flask/Django-shaped `request.*` and generic `req.*`
#: (Express/FastAPI-shaped) accessors.
_SOURCE_RE = re.compile(
    r"\b(request|req)\.(args|form|values|GET|POST|"
    r"headers|json|data|query_params|params|query|body)"
)

_HEADER_SET_RE = re.compile(
    r"(?:response|res)\.set(?:_header|Header)\(\s*[^,]+,\s*([^)]+)\)"
)
_HEADER_ITEM_RE = re.compile(r"\.headers\[[^\]]+\]\s*=\s*(.+)")

_URL_BUILD_RE = re.compile(
    r"""["']https?://["']\s*\+\s*([^\s,;)]+)|f["'][^"']*https?://[^"']*\{([^}]+)\}"""
)

_LOG_CALL_RE = re.compile(
    r"""logger\.\w+\(\s*(?:f["'][^"']*\{([^}]+)\}[^)]*|[^)]*\+\s*([^)]+))\)"""
)

_CONTENT_DISPOSITION_RE = re.compile(
    r"""Content-Disposition[^\n]*filename[^\n]*\{([^}]+)\}|"""
    r"""attachment_filename\s*=\s*([^\s,)]+)"""
)

_REQUESTS_CALL_RE = re.compile(
    r"requests\.(?:get|post|request)\(\s*([^\s,)]+)([^)]*)\)"
)

_WS_INSECURE_SCHEME_RE = re.compile(r"new\s+WebSocket\(\s*[\"']ws://")
_WS_HANDLER_RE = re.compile(r"websocket|WebSocket", re.IGNORECASE)


def _tracked_files(root: Path, *suffixes: str) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `suffixes`, root-relative
    POSIX paths, `()` on any git failure -- mirrors `_websec_sinks.
    _tracked_files`'s own tracked-file-scan shape.

    frob:ticket T-5308
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("websec_headers_log: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("websec_headers_log: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(suffixes)
    )


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable.

    frob:ticket T-5308
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _is_tainted(expr: str) -> bool:
    """True if `expr` references a request-derived source and has not
    already been through a recognized encode/sanitize hop.

    frob:ticket T-5308
    """
    return bool(_SOURCE_RE.search(expr)) and not _ENCODED_RE.search(expr)


def _line_of(text: str, offset: int) -> int:
    """1-based line number of byte/char `offset` in `text`.

    frob:ticket T-5308
    """
    return text.count("\n", 0, offset) + 1


def _header_findings(text: str, rel_path: str) -> list[WebsecHeaderLogFinding]:
    """WEBSEC117: CRLF/response-header injection.

    frob:ticket T-5308
    """
    findings: list[WebsecHeaderLogFinding] = []
    for pattern in (_HEADER_SET_RE, _HEADER_ITEM_RE):
        for match in pattern.finditer(text):
            expr = match.group(1).strip()
            if not _is_tainted(expr):
                continue
            line = _line_of(text, match.start())
            findings.append(
                WebsecHeaderLogFinding(
                    rule="WEBSEC117",
                    file=rel_path,
                    line=line,
                    message=(
                        f"WEBSEC117: {rel_path}:{line} a response header is "
                        f"set from unvalidated request-derived data "
                        f"({expr!r}) -- CRLF/header injection (CWE-113). "
                        f"Strip CR/LF or percent-encode the value first, "
                        f'or `frob:waive WEBSEC117 reason="..."` with a '
                        f"real justification"
                    ),
                )
            )
    return findings


def _url_build_findings(text: str, rel_path: str) -> list[WebsecHeaderLogFinding]:
    """WEBSEC118: URL-building injection.

    frob:ticket T-5308
    """
    findings: list[WebsecHeaderLogFinding] = []
    for match in _URL_BUILD_RE.finditer(text):
        expr = (match.group(1) or match.group(2) or "").strip()
        if not _is_tainted(expr):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecHeaderLogFinding(
                rule="WEBSEC118",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC118: {rel_path}:{line} a URL is built by "
                    f"splicing unvalidated request-derived data "
                    f"({expr!r}) with no urlencode/scheme allowlist "
                    f"check -- URL-building injection. Pass the value "
                    f"through urlencode/quote and validate the scheme "
                    f'first, or `frob:waive WEBSEC118 reason="..."` with '
                    f"a real justification"
                ),
            )
        )
    return findings


def _log_injection_findings(text: str, rel_path: str) -> list[WebsecHeaderLogFinding]:
    """WEBSEC119: log injection.

    frob:ticket T-5308
    """
    findings: list[WebsecHeaderLogFinding] = []
    for match in _LOG_CALL_RE.finditer(text):
        expr = (match.group(1) or match.group(2) or "").strip()
        if not _is_tainted(expr):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecHeaderLogFinding(
                rule="WEBSEC119",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC119: {rel_path}:{line} a log message embeds "
                    f"unvalidated request-derived data ({expr!r}) with no "
                    f"CR/LF-stripping encoder -- log injection (CWE-117). "
                    f"Use %r/repr()/a sanitizing encoder first, or "
                    f'`frob:waive WEBSEC119 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _content_disposition_findings(
    text: str, rel_path: str
) -> list[WebsecHeaderLogFinding]:
    """WEBSEC120: `Content-Disposition`/filename header encoding
    (RFC 6266).

    frob:ticket T-5308
    """
    findings: list[WebsecHeaderLogFinding] = []
    for match in _CONTENT_DISPOSITION_RE.finditer(text):
        expr = (match.group(1) or match.group(2) or "").strip()
        if not _is_tainted(expr):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecHeaderLogFinding(
                rule="WEBSEC120",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC120: {rel_path}:{line} a Content-Disposition/"
                    f"filename header is built from unvalidated "
                    f"request-derived data ({expr!r}) with no RFC 6266 "
                    f"percent-encoding -- header injection/path-confusion "
                    f"risk. Percent-encode the filename first, or "
                    f'`frob:waive WEBSEC120 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _ssrf_redirect_findings(text: str, rel_path: str) -> list[WebsecHeaderLogFinding]:
    """WEBSEC121: backend follows a redirect from a request-derived URL.

    frob:ticket T-5308
    """
    findings: list[WebsecHeaderLogFinding] = []
    for match in _REQUESTS_CALL_RE.finditer(text):
        url_expr = match.group(1).strip()
        rest = match.group(2) or ""
        if not _is_tainted(url_expr):
            continue
        if re.search(r"allow_redirects\s*=\s*False", rest):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecHeaderLogFinding(
                rule="WEBSEC121",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC121: {rel_path}:{line} an outbound HTTP call "
                    f"uses a request-derived URL ({url_expr!r}) and does "
                    f"not disable redirect-following -- SSRF-adjacent "
                    f"(the backend can be made to fetch/follow an "
                    f"attacker-chosen internal URL). Pass "
                    f"allow_redirects=False and validate the target "
                    f'first, or `frob:waive WEBSEC121 reason="..."` with '
                    f"a real justification"
                ),
            )
        )
    return findings


def _websocket_findings(text: str, rel_path: str) -> list[WebsecHeaderLogFinding]:
    """WEBSEC122: WebSocket origin-check + WSS-only enforcement.

    frob:ticket T-5308
    """
    findings: list[WebsecHeaderLogFinding] = []
    for match in _WS_INSECURE_SCHEME_RE.finditer(text):
        line = _line_of(text, match.start())
        findings.append(
            WebsecHeaderLogFinding(
                rule="WEBSEC122",
                file=rel_path,
                line=line,
                message=(
                    f'WEBSEC122: {rel_path}:{line} new WebSocket("ws://'
                    f'...") uses the insecure ws:// scheme -- ASVS 5.0 '
                    f"V4.4.2 requires WSS-only. Use wss:// instead, or "
                    f'`frob:waive WEBSEC122 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    handler_match = _WS_HANDLER_RE.search(text)
    if handler_match and "origin" not in text.lower():
        line = _line_of(text, handler_match.start())
        findings.append(
            WebsecHeaderLogFinding(
                rule="WEBSEC122",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC122: {rel_path}:{line} a WebSocket connection "
                    f"handler has no Origin check anywhere in the file -- "
                    f"ASVS 5.0 V4.4.1 requires validating the Origin "
                    f"header on every WebSocket handshake. Add an origin "
                    f"allowlist check, or `frob:waive WEBSEC122 reason="
                    f'"..."` with a real justification'
                ),
            )
        )
    return findings


def _file_findings(path: Path, root: Path) -> list[WebsecHeaderLogFinding]:
    """Every WEBSEC117-122 finding in one file.

    frob:ticket T-5308
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text:
        return []
    findings: list[WebsecHeaderLogFinding] = []
    findings.extend(_header_findings(text, rel_path))
    findings.extend(_url_build_findings(text, rel_path))
    findings.extend(_log_injection_findings(text, rel_path))
    findings.extend(_content_disposition_findings(text, rel_path))
    findings.extend(_ssrf_redirect_findings(text, rel_path))
    findings.extend(_websocket_findings(text, rel_path))
    return findings


# frob:doc docs/modules/webapp-websec-headers-log.md#public-api
# frob:ticket T-5308
def websec_headers_log_findings(root: Path) -> tuple[WebsecHeaderLogFinding, ...]:
    """WEBSEC117-122: every header/URL/log-injection or WebSocket
    origin/WSS-enforcement finding under `root`.

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all (T-5302's own contract, same posture
    `websec_sink_findings` already follows).

    frob:ticket T-5308
    """
    root = Path(root)
    if not detect_frameworks(root):
        _log.debug(
            "websec_headers_log: no framework detected at %s, skipping scan", root
        )
        return ()

    findings: list[WebsecHeaderLogFinding] = []
    for rel in _tracked_files(root, ".py", ".js", ".jsx", ".ts", ".tsx"):
        findings.extend(_file_findings(root / rel, root))

    _log.info("websec_headers_log: %d finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/webapp-websec-headers-log.md#public-api
# frob:ticket T-5308
def websec_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """T-5311's `taint_gate` module-discovery hook: every
    `frob.webapp._websec_*` module exposing a module-level
    `websec_findings(root, frameworks) -> tuple[Violation, ...]` is
    auto-discovered and folded into `taint_gate`'s scan, so a new WEBSEC
    family never needs its own `gates/__init__.py`/`_taint_gate.py`
    edit. `frameworks` is the caller's own already-computed
    `detect_frameworks(root)` result (avoids a second detect call per
    discovered module) -- an empty set short-circuits to `()` exactly
    like `websec_headers_log_findings`'s own direct-call contract.

    frob:ticket T-5308
    """
    if not frameworks:
        _log.debug(
            "websec_headers_log: no framework detected at %s, skipping scan (hook)",
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
        for finding in websec_headers_log_findings(root)
    )
