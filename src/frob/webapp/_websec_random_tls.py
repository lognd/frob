"""WEBSEC226-230: randomness and TLS verification (docs/modules/webapp-
websec-random-tls.md, T-5354, the T-5140 web-app epic's randomness/TLS
leaf).

Same posture as every WEBSEC family in this epic: framework-gated
(short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
reports no web framework, T-5302's own contract), and folded into
`frob.gates._taint_gate.taint_gate` via the `websec_findings(root,
frameworks)` pkgutil-discovery hook (T-5308) rather than a second gate
registration.

FIVE RULE IDS (T-5301's reserved `WEBSEC226`-`WEBSEC230` block), all
TEXT-REGEX/text-window scans over tracked source files -- the same
disclosed-gap "textual proxy, not resolved data-flow" posture every
text-regex WEBSEC family in this epic carries:

- WEBSEC226: insecure randomness for a security-sensitive value --
  `random.random()`/`random.randint(`/`Math.random()` assigned to a
  variable whose name looks like a token/session-id/API-key/CSRF-token
  (name-based heuristic on the assignment target, the same PERF-family
  lexical-smell precedent the ticket body cites).
- WEBSEC227: TLS verification disabled -- `requests`-shaped
  `verify=False`, `rejectUnauthorized: false`, or a literal `http://`
  URL passed straight to an outbound HTTP client call.
- WEBSEC228: no minimum TLS version configured -- an `ssl.SSLContext(`/
  `ssl.wrap_socket(`/Node `https.createServer(`/`tls.createServer(`
  call with no `minimum_version`/`ssl_version`/`minVersion` keyword in
  the same text window.
- WEBSEC229: certificate pinning (mobile-only, config advisory) -- a
  mobile HTTP client indicator (`URLSession(`/`AFHTTPSessionManager`/
  `OkHttpClient`) in a `.swift`/`.m`/`.java`/`.kt` file, with no
  pinning-library keyword (`CertificatePinner`/`NSPinnedDomains`/
  `TrustKit`/`kSecTrustedPeerCertificates`) anywhere in the tracked
  file set. Advisory: a monorepo mixing a detected web framework with a
  mobile client is the only shape this module ever scans (T-5302's
  framework gate applies file-set-wide, not per-file), so this rule
  only fires in that specific monorepo shape -- documented, not
  silently narrowed.
- WEBSEC230: credential-stuffing rate-limit missing -- a login-shaped
  handler (name containing "login"/"sign_in") with no rate-limit
  indicator (`limiter`/`rate_limit`/`throttle`/`RateLimit`) anywhere in
  the same file. Cross-references T-5144-2's own rate-limit rule rather
  than reimplementing generic rate-limit detection.

HSTS is deliberately OUT of scope here -- it is owned by T-5143-2's
response-header-lint substrate (`frob.webapp._websec_headers`, WEBSEC3xx
family); this leaf blocks on that substrate rather than reimplementing
header parsing.

Each is WARN-tier at first turn-on, the T-0688/T-0973 promotion posture
every WEBSEC family in this epic follows.
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
    "WebsecRandomTlsFinding",
    "websec_findings",
    "websec_random_tls_findings",
]


# frob:doc docs/modules/webapp-websec-random-tls.md#public-api
@dataclass(frozen=True)
class WebsecRandomTlsFinding:
    """One WEBSEC226-230 finding: an insecure-randomness or TLS-
    verification/config hardening gap.

    frob:ticket T-5354
    """

    rule: str
    file: str
    line: int
    message: str


#: Assignment-target name fragments this scan treats as "this value is
#: security-sensitive" -- a name-based heuristic, the same PERF-family
#: lexical-smell precedent the ticket body cites, not a taint-tracked
#: value.
_SENSITIVE_NAME_RE = r"\w*(?:token|session_id|sessionid|api_key|apikey|csrf)\w*"

_INSECURE_RANDOM_ASSIGN_RE = re.compile(
    rf"""({_SENSITIVE_NAME_RE})\s*=\s*[^\n;]*\b(random\.random\(\)|random\.randint\(|Math\.random\(\))""",
    re.IGNORECASE,
)

_TLS_VERIFY_DISABLED_RE = re.compile(
    r"verify\s*=\s*False|rejectUnauthorized\s*:\s*false|"
    r"""(?:requests\.\w+|fetch|axios\.\w+)\(\s*["']http://[^"']*api[^"']*["']""",
    re.IGNORECASE,
)

_TLS_CONTEXT_CREATE_RE = re.compile(
    r"ssl\.SSLContext\(|ssl\.wrap_socket\(|https\.createServer\(|tls\.createServer\("
)
_TLS_MIN_VERSION_RE = re.compile(
    r"minimum_version|ssl_version|minVersion", re.IGNORECASE
)
_TLS_CONTEXT_WINDOW_CHARS = 300

_MOBILE_CLIENT_RE = re.compile(r"URLSession\(|AFHTTPSessionManager|OkHttpClient")
_CERT_PINNING_KEYWORD_RE = re.compile(
    r"CertificatePinner|NSPinnedDomains|TrustKit|kSecTrustedPeerCertificates"
)

_LOGIN_HANDLER_RE = re.compile(
    r"""def\s+\w*(login|sign_in)\w*\s*\(|function\s+\w*(login|sign_in)\w*\s*\(""",
    re.IGNORECASE,
)
_RATE_LIMIT_RE = re.compile(r"limiter|rate_limit|throttle|RateLimit", re.IGNORECASE)


def _tracked_files(root: Path, *suffixes: str) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `suffixes` (all files when
    `suffixes` is empty), root-relative POSIX paths, `()` on any git
    failure -- mirrors `_websec_headers_log._tracked_files`'s own
    tracked-file-scan shape.

    frob:ticket T-5354
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("websec_random_tls: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("websec_random_tls: git ls-files exited %d", result.returncode)
        return ()
    lines = tuple(line for line in result.stdout.splitlines() if line.strip())
    if not suffixes:
        return lines
    return tuple(line for line in lines if line.endswith(suffixes))


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable.

    frob:ticket T-5354
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _line_of(text: str, offset: int) -> int:
    """1-based line number of char `offset` in `text`.

    frob:ticket T-5354
    """
    return text.count("\n", 0, offset) + 1


def _insecure_random_findings(text: str, rel_path: str) -> list[WebsecRandomTlsFinding]:
    """WEBSEC226: insecure randomness for a security-sensitive value.

    frob:ticket T-5354
    """
    findings: list[WebsecRandomTlsFinding] = []
    for match in _INSECURE_RANDOM_ASSIGN_RE.finditer(text):
        name = match.group(1)
        line = _line_of(text, match.start())
        findings.append(
            WebsecRandomTlsFinding(
                rule="WEBSEC226",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC226: {rel_path}:{line} {name!r} looks "
                    f"security-sensitive but is assigned from a "
                    f"non-cryptographic random source "
                    f"({match.group(2)!r}) -- predictable/guessable "
                    f"value. Use secrets.token_urlsafe()/crypto."
                    f"randomBytes() instead, or "
                    f'`frob:waive WEBSEC226 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _tls_verify_disabled_findings(
    text: str, rel_path: str
) -> list[WebsecRandomTlsFinding]:
    """WEBSEC227: TLS verification disabled.

    frob:ticket T-5354
    """
    findings: list[WebsecRandomTlsFinding] = []
    for match in _TLS_VERIFY_DISABLED_RE.finditer(text):
        line = _line_of(text, match.start())
        findings.append(
            WebsecRandomTlsFinding(
                rule="WEBSEC227",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC227: {rel_path}:{line} TLS certificate "
                    f"verification is disabled or a plaintext http:// "
                    f"URL is used for an outbound API call -- "
                    f"MITM-exposed. Enable verification/use https://, "
                    f'or `frob:waive WEBSEC227 reason="..."` with a '
                    f"real justification"
                ),
            )
        )
    return findings


def _tls_min_version_findings(text: str, rel_path: str) -> list[WebsecRandomTlsFinding]:
    """WEBSEC228: no minimum TLS version configured.

    frob:ticket T-5354
    """
    findings: list[WebsecRandomTlsFinding] = []
    for match in _TLS_CONTEXT_CREATE_RE.finditer(text):
        window = text[match.end() : match.end() + _TLS_CONTEXT_WINDOW_CHARS]
        if _TLS_MIN_VERSION_RE.search(window):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecRandomTlsFinding(
                rule="WEBSEC228",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC228: {rel_path}:{line} a TLS context/server "
                    f"is created with no minimum TLS version configured "
                    f"-- an outdated protocol version can be "
                    f"negotiated. Set minimum_version/ssl_version/"
                    f'minVersion, or `frob:waive WEBSEC228 reason="..."` '
                    f"with a real justification"
                ),
            )
        )
    return findings


def _handler_shape_findings(path: Path, root: Path) -> list[WebsecRandomTlsFinding]:
    """Every WEBSEC226/227/228 finding in one tracked source file.

    frob:ticket T-5354
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text:
        return []
    findings: list[WebsecRandomTlsFinding] = []
    findings.extend(_insecure_random_findings(text, rel_path))
    findings.extend(_tls_verify_disabled_findings(text, rel_path))
    findings.extend(_tls_min_version_findings(text, rel_path))
    return findings


def _no_rate_limit_findings(path: Path, root: Path) -> list[WebsecRandomTlsFinding]:
    """WEBSEC230: a login-shaped handler with no rate-limit indicator
    anywhere in the same file.

    frob:ticket T-5354
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text:
        return []
    login_match = _LOGIN_HANDLER_RE.search(text)
    if login_match is None:
        return []
    if _RATE_LIMIT_RE.search(text):
        return []
    line = _line_of(text, login_match.start())
    return [
        WebsecRandomTlsFinding(
            rule="WEBSEC230",
            file=rel_path,
            line=line,
            message=(
                f"WEBSEC230: {rel_path}:{line} a login handler exists "
                f"but this file has no rate-limit indicator anywhere -- "
                f"credential-stuffing exposed (cross-references "
                f"T-5144-2's rate-limit rule rather than reimplementing "
                f"it). Wire a rate limiter, or `frob:waive WEBSEC230 "
                f'reason="..."` with a real justification'
            ),
        )
    ]


def _cert_pinning_findings(
    tracked: frozenset[str], root: Path
) -> list[WebsecRandomTlsFinding]:
    """WEBSEC229: a mobile HTTP client indicator with no pinning-library
    keyword anywhere in the tracked file set (mobile-only, config
    advisory).

    frob:ticket T-5354
    """
    mobile_files = [
        rel for rel in sorted(tracked) if rel.endswith((".swift", ".m", ".java", ".kt"))
    ]
    if not mobile_files:
        return []
    all_text = "\n".join(_read_text(root / rel) for rel in mobile_files)
    if _CERT_PINNING_KEYWORD_RE.search(all_text):
        return []
    findings: list[WebsecRandomTlsFinding] = []
    for rel in mobile_files:
        text = _read_text(root / rel)
        match = _MOBILE_CLIENT_RE.search(text)
        if match is None:
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecRandomTlsFinding(
                rule="WEBSEC229",
                file=rel,
                line=line,
                message=(
                    f"WEBSEC229: {rel}:{line} a mobile HTTP client is "
                    f"used ({match.group(0)!r}) but no certificate-"
                    f"pinning library keyword was found anywhere in the "
                    f"tracked mobile source (advisory: MITM-exposed on "
                    f"a compromised CA). Wire TrustKit/"
                    f"CertificatePinner/NSPinnedDomains, or `frob:waive "
                    f'WEBSEC229 reason="..."` with a real justification'
                ),
            )
        )
        break
    return findings


# frob:doc docs/modules/webapp-websec-random-tls.md#public-api
# frob:ticket T-5354
def websec_random_tls_findings(root: Path) -> tuple[WebsecRandomTlsFinding, ...]:
    """WEBSEC226-230: every insecure-randomness/TLS-verification/TLS-
    config/cert-pinning/rate-limit finding under `root`.

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all (T-5302's own contract, the same
    posture every WEBSEC family in this epic follows).

    frob:ticket T-5354
    """
    root = Path(root)
    if not detect_frameworks(root):
        _log.debug(
            "websec_random_tls: no framework detected at %s, skipping scan", root
        )
        return ()

    tracked = frozenset(
        _tracked_files(root, ".py", ".js", ".jsx", ".ts", ".tsx", ".rb")
    )
    findings: list[WebsecRandomTlsFinding] = []
    for rel in sorted(tracked):
        findings.extend(_handler_shape_findings(root / rel, root))
        findings.extend(_no_rate_limit_findings(root / rel, root))
    findings.extend(_cert_pinning_findings(frozenset(_tracked_files(root)), root))

    _log.info("websec_random_tls: %d finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/webapp-websec-random-tls.md#public-api
# frob:ticket T-5354
def websec_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """T-5308's `taint_gate` module-discovery hook: every
    `frob.webapp._websec_*` module exposing a module-level
    `websec_findings(root, frameworks) -> tuple[Violation, ...]` is
    auto-discovered and folded into `taint_gate`'s scan, so this new
    WEBSEC family never needs its own `gates/__init__.py`/`_taint_gate.py`
    edit. `frameworks` is the caller's own already-computed
    `detect_frameworks(root)` result (avoids a second detect call per
    discovered module) -- an empty set short-circuits to `()` exactly
    like `websec_random_tls_findings`'s own direct-call contract.

    frob:ticket T-5354
    """
    if not frameworks:
        _log.debug(
            "websec_random_tls: no framework detected at %s, skipping scan (hook)",
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
        for finding in websec_random_tls_findings(root)
    )
