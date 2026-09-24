"""WEBSEC301-309: config/headers rule-id wiring for
`frob.webapp._websec_headers.lint_response_headers` (docs/modules/
webapp-websec-headers-rules.md, T-5326, the `T-5143`/T-5140 web-app epic's
config/headers leaf, blocked_by=['T-5325']).

T-5325's `_websec_headers.py` is the response-header EVIDENCE engine (it
scans nginx/Caddy config and Django/helmet app code for
`HeaderFinding`s over its own `REQUIRED_HEADERS`); its `lint_response_headers`
carries a `frob:waive WIRE001 reason="engine only; T-5326 wires the gate
rule ids"` naming THIS ticket as the module that maps those results onto
concrete WEBSEC rule ids. This module is that wiring: it calls
`lint_response_headers` and never re-implements the nginx/Caddy/Django/
helmet parsing it already owns.

NINE RULE IDS (T-5301's reserved `WEBSEC301`-`WEBSEC309` block, the
ticket body's ASVS-5.0-shaped corpus):

- WEBSEC301: HSTS max-age >= 31536000 (V3.4.1/V3.7.4) -- wraps the
  substrate's `Strict-Transport-Security` `HeaderFinding` (MISSING/
  ADVISORY both fire directly); when PRESENT, this module additionally
  re-reads the evidence file's `max-age=` value and fires if it is
  absent or below the one-year floor -- a check `_websec_headers.py`
  never attempts (it only checks the header NAME is set, not its value).
- WEBSEC302: CSP with a nonce (V3.4.3) -- wraps the substrate's
  `Content-Security-Policy` `HeaderFinding`; MISSING/ADVISORY fire
  directly, PRESENT additionally requires a `nonce-` fragment in the
  evidence file, else fires (CSP present but not nonce-based).
- WEBSEC303: `X-Content-Type-Options: nosniff` (V3.4.4) -- a direct
  passthrough of the substrate's `HeaderFinding` (MISSING/ADVISORY).
- WEBSEC304: `Referrer-Policy` (V3.4.5) -- a direct passthrough of the
  substrate's `HeaderFinding` (MISSING/ADVISORY).
- WEBSEC305: `Permissions-Policy` -- NOT in the substrate's
  `REQUIRED_HEADERS`; this module keeps its own tiny tracked-file
  text-scan for the header name (same "own tiny private copy, not a
  cross-module private import" posture `_websec_headers_log.py`'s module
  docstring documents), gated on the same framework-detection contract.
- WEBSEC306: COOP/COEP/CORP (`Cross-Origin-Opener-Policy`/
  `-Embedder-Policy`/`-Resource-Policy`) -- same own-tiny-scan posture as
  WEBSEC305, any one of the three counts as evidence.
- WEBSEC307: CORS wildcard origin (V3.4.2) -- fires when
  `Access-Control-Allow-Origin: *` is found (a fixed/allowlisted origin
  is the ASVS-required shape; the wildcard is the violating one).
- WEBSEC308: CORS-preflight reliance for sensitive functionality
  (V3.5.1/V3.5.2) -- a proxy for "preflight is the only protection": a
  wildcard `Access-Control-Allow-Origin` co-occurring with
  `Access-Control-Allow-Credentials: true` in the same file (a known
  real-world CORS misconfiguration class, not a full request-authz
  trace -- disclosed as a v1 heuristic, not a claim of completeness).
- WEBSEC309: `Cache-Control: no-store` on authenticated responses
  (V14.3.2) -- the canonical owner of this rule id (T-5147-6/WEBPERF
  server-network blocks on this leaf rather than reimplementing the
  authenticated-route detection); a proxy heuristic: a file referencing
  an authenticated-route marker (`login_required`, `request.user`,
  `req.session`, `@jwt_required`) with no `Cache-Control` /`no-store`
  anywhere in the same file.

FRAMEWORK GATING (T-5302): same short-circuit posture every WEBSEC/
COMPLY/A11Y/SEO/WEBPERF family uses -- `frob.webapp._detect.
detect_frameworks(root)` empty means no scan at all (the substrate call
for WEBSEC301-304 short-circuits internally via `no_evidence`-shaped
ADVISORY output already, but WEBSEC305-309's own text scans are
independently gated here since they never call the substrate).

WIRING: `websec_findings(root, frameworks) -> tuple[Violation, ...]` is
`frob.gates._taint_gate.taint_gate`'s pkgutil-discovery hook (T-5311) --
any `frob.webapp._websec_*` module exposing it is auto-folded into the
gate's scan, so this leaf needs no `_taint_gate.py` edit. WARN-tier at
first turn-on (T-0688/T-0973 promotion posture, same as every sibling
WEBSEC family).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from frob.findings import Severity, Violation
from frob.gitio import run_argv
from frob.logging import get_logger
from frob.webapp._detect import FrameworkKind, detect_frameworks
from frob.webapp._websec_headers import (
    HeaderFinding,
    HeaderStatus,
    lint_response_headers,
)

_log = get_logger(__name__)

__all__ = [
    "WebsecHeaderRuleFinding",
    "websec_findings",
    "websec_headers_rules_findings",
]

_HSTS_MAX_AGE_FLOOR = 31536000

_MAX_AGE_RE = re.compile(r"max-age\s*=\s*(\d+)")
_NONCE_RE = re.compile(r"nonce-", re.IGNORECASE)

_PERMISSIONS_POLICY_RE = re.compile(r"Permissions-Policy", re.IGNORECASE)
_COOP_COEP_CORP_RE = re.compile(
    r"Cross-Origin-(?:Opener|Embedder|Resource)-Policy", re.IGNORECASE
)
_ACAO_WILDCARD_RE = re.compile(
    r"""Access-Control-Allow-Origin["']?\]?\s*[:=,]\s*["']?\*""", re.IGNORECASE
)
_ACAC_TRUE_RE = re.compile(
    r"""Access-Control-Allow-Credentials["']?\]?\s*[:=,]\s*["']?true""",
    re.IGNORECASE,
)
_AUTH_ROUTE_MARKER_RE = re.compile(
    r"login_required|request\.user|req\.session|jwt_required", re.IGNORECASE
)
_CACHE_CONTROL_NO_STORE_RE = re.compile(
    r"Cache-Control[^\n]{0,80}no-store", re.IGNORECASE
)

_SCAN_EXTENSIONS = (".conf", ".py", ".js", ".jsx", ".ts", ".tsx")
_SCAN_NAMES = ("nginx.conf", "Caddyfile")


# frob:doc docs/modules/webapp-websec-headers-rules.md#public-api
# frob:tests \
# tests/unit/test_websec_headers_rules.py::test_websec_headers_rules_findings_fixture[websec301_positive-WEBSEC301-True] kind="unit"  # noqa: E501
@dataclass(frozen=True)
class WebsecHeaderRuleFinding:
    """One WEBSEC301-309 finding: a config/headers rule id, the file and
    line the evidence (or its absence) came from, and a human message.

    frob:ticket T-5326
    """

    rule: str
    file: str
    line: int
    message: str


def _tracked_files(root: Path) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `_SCAN_EXTENSIONS`/
    `_SCAN_NAMES`, root-relative POSIX paths, `()` on any git failure --
    mirrors `_websec_headers_log._tracked_files`'s own tracked-file-scan
    shape (an intentional own tiny copy, not a cross-module private
    import; see this module's docstring).

    frob:ticket T-5326
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning(
            "websec_headers_rules: git ls-files failed: %s", spawned.danger_err
        )
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("websec_headers_rules: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip()
        and (line.endswith(_SCAN_EXTENSIONS) or Path(line).name in _SCAN_NAMES)
    )


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable.

    frob:ticket T-5326
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _finding_from_header(
    rule: str, finding: HeaderFinding, root: Path
) -> WebsecHeaderRuleFinding | None:
    """MISSING/ADVISORY substrate statuses become a `rule` finding
    directly (using the substrate's own path/line/message when present);
    PRESENT reports nothing at this step (value-level checks for
    WEBSEC301/WEBSEC302 layer on top of this in their own callers).

    frob:ticket T-5326
    """
    if finding.status == HeaderStatus.PRESENT:
        return None
    file = finding.path.relative_to(root).as_posix() if finding.path else "<repo>"
    line = finding.line or 1
    return WebsecHeaderRuleFinding(
        rule=rule,
        file=file,
        line=line,
        message=f"{rule}: {finding.message}",
    )


def _hsts_findings(
    findings_by_header: dict[str, HeaderFinding], root: Path
) -> list[WebsecHeaderRuleFinding]:
    """WEBSEC301: HSTS max-age >= 31536000.

    frob:ticket T-5326
    """
    finding = findings_by_header.get("Strict-Transport-Security")
    if finding is None:
        return []
    base = _finding_from_header("WEBSEC301", finding, root)
    if base is not None:
        return [base]
    assert finding.path is not None and finding.line is not None
    text = _read_text(finding.path)
    match = _MAX_AGE_RE.search(text)
    if match is not None and int(match.group(1)) >= _HSTS_MAX_AGE_FLOOR:
        return []
    file = finding.path.relative_to(root).as_posix()
    return [
        WebsecHeaderRuleFinding(
            rule="WEBSEC301",
            file=file,
            line=finding.line,
            message=(
                "WEBSEC301: Strict-Transport-Security is set but its "
                "max-age is missing or below the one-year floor "
                f"({_HSTS_MAX_AGE_FLOOR}) -- ASVS 5.0 V3.4.1/V3.7.4. Set "
                f"max-age={_HSTS_MAX_AGE_FLOOR}, or `frob:waive WEBSEC301 "
                'reason="..."` with a real justification'
            ),
        )
    ]


def _csp_nonce_findings(
    findings_by_header: dict[str, HeaderFinding], root: Path
) -> list[WebsecHeaderRuleFinding]:
    """WEBSEC302: CSP with a nonce.

    frob:ticket T-5326
    """
    finding = findings_by_header.get("Content-Security-Policy")
    if finding is None:
        return []
    base = _finding_from_header("WEBSEC302", finding, root)
    if base is not None:
        return [base]
    assert finding.path is not None and finding.line is not None
    text = _read_text(finding.path)
    if _NONCE_RE.search(text):
        return []
    file = finding.path.relative_to(root).as_posix()
    return [
        WebsecHeaderRuleFinding(
            rule="WEBSEC302",
            file=file,
            line=finding.line,
            message=(
                "WEBSEC302: Content-Security-Policy is set but has no "
                "nonce- fragment -- ASVS 5.0 V3.4.3 wants a per-response "
                "nonce. Add a nonce- source, or `frob:waive WEBSEC302 "
                'reason="..."` with a real justification'
            ),
        )
    ]


def _passthrough_findings(
    rule: str, header: str, findings_by_header: dict[str, HeaderFinding], root: Path
) -> list[WebsecHeaderRuleFinding]:
    """WEBSEC303/WEBSEC304: a direct MISSING/ADVISORY passthrough of the
    substrate's own `HeaderFinding` for `header`.

    frob:ticket T-5326
    """
    finding = findings_by_header.get(header)
    if finding is None:
        return []
    base = _finding_from_header(rule, finding, root)
    return [base] if base is not None else []


def _text_presence_findings(
    root: Path, rule: str, pattern: re.Pattern[str], label: str
) -> list[WebsecHeaderRuleFinding]:
    """WEBSEC305/WEBSEC306: fires once, at the repo root, when no tracked
    config/app file matches `pattern` anywhere -- headers outside the
    substrate's `REQUIRED_HEADERS`, so this module's own tiny text scan
    (not a re-implementation of `_websec_headers.py`'s nginx/Caddy/Django
    parser, just a presence check for a different header name).

    frob:ticket T-5326
    """
    for rel in _tracked_files(root):
        if pattern.search(_read_text(root / rel)):
            return []
    return [
        WebsecHeaderRuleFinding(
            rule=rule,
            file="<repo>",
            line=1,
            message=(
                f"{rule}: no in-repo evidence for {label} in any tracked "
                "nginx/Caddy config or app code -- confirm at your edge, "
                f'or `frob:waive {rule} reason="..."` with a real '
                "justification"
            ),
        )
    ]


def _cors_findings(root: Path) -> list[WebsecHeaderRuleFinding]:
    """WEBSEC307 (CORS wildcard origin) and WEBSEC308 (wildcard origin +
    Allow-Credentials: true -- preflight-reliance proxy).

    frob:ticket T-5326
    """
    findings: list[WebsecHeaderRuleFinding] = []
    for rel in _tracked_files(root):
        text = _read_text(root / rel)
        wildcard = _ACAO_WILDCARD_RE.search(text)
        if wildcard is None:
            continue
        line = text.count("\n", 0, wildcard.start()) + 1
        findings.append(
            WebsecHeaderRuleFinding(
                rule="WEBSEC307",
                file=rel,
                line=line,
                message=(
                    "WEBSEC307: Access-Control-Allow-Origin: * -- ASVS "
                    "5.0 V3.4.2 wants a fixed/allowlisted origin, not a "
                    "wildcard. Use a fixed origin, or `frob:waive "
                    'WEBSEC307 reason="..."` with a real justification'
                ),
            )
        )
        if _ACAC_TRUE_RE.search(text):
            findings.append(
                WebsecHeaderRuleFinding(
                    rule="WEBSEC308",
                    file=rel,
                    line=line,
                    message=(
                        "WEBSEC308: Access-Control-Allow-Origin: * with "
                        "Access-Control-Allow-Credentials: true -- relies "
                        "on the CORS preflight as the only protection for "
                        "sensitive functionality (ASVS 5.0 V3.5.1/"
                        "V3.5.2). Add a server-side authz check, or "
                        '`frob:waive WEBSEC308 reason="..."` with a real '
                        "justification"
                    ),
                )
            )
    return findings


def _cache_control_findings(root: Path) -> list[WebsecHeaderRuleFinding]:
    """WEBSEC309: Cache-Control: no-store on authenticated responses.

    frob:ticket T-5326
    """
    findings: list[WebsecHeaderRuleFinding] = []
    for rel in _tracked_files(root):
        text = _read_text(root / rel)
        auth_match = _AUTH_ROUTE_MARKER_RE.search(text)
        if auth_match is None:
            continue
        if _CACHE_CONTROL_NO_STORE_RE.search(text):
            continue
        line = text.count("\n", 0, auth_match.start()) + 1
        findings.append(
            WebsecHeaderRuleFinding(
                rule="WEBSEC309",
                file=rel,
                line=line,
                message=(
                    "WEBSEC309: an authenticated-route marker is present "
                    "with no Cache-Control: no-store anywhere in the "
                    "file -- ASVS 5.0 V14.3.2 wants authenticated "
                    "responses marked non-cacheable. Add "
                    "Cache-Control: no-store, or `frob:waive WEBSEC309 "
                    'reason="..."` with a real justification'
                ),
            )
        )
    return findings


# frob:doc docs/modules/webapp-websec-headers-rules.md#public-api
# frob:ticket T-5326
def websec_headers_rules_findings(root: Path) -> tuple[WebsecHeaderRuleFinding, ...]:
    """WEBSEC301-309: every config/headers finding under `root`.

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all (T-5302's own contract, same posture
    every sibling WEBSEC family follows).

    frob:ticket T-5326
    """
    root = Path(root)
    if not detect_frameworks(root):
        _log.debug(
            "websec_headers_rules: no framework detected at %s, skipping scan",
            root,
        )
        return ()

    lint_result = lint_response_headers(root)
    if lint_result.is_err:
        _log.warning(
            "websec_headers_rules: lint_response_headers failed for %s: %s",
            root,
            lint_result.danger_err,
        )
        findings_by_header: dict[str, HeaderFinding] = {}
    else:
        findings_by_header = {f.header: f for f in lint_result.danger_ok}

    findings: list[WebsecHeaderRuleFinding] = []
    findings.extend(_hsts_findings(findings_by_header, root))
    findings.extend(_csp_nonce_findings(findings_by_header, root))
    findings.extend(
        _passthrough_findings(
            "WEBSEC303", "X-Content-Type-Options", findings_by_header, root
        )
    )
    findings.extend(
        _passthrough_findings("WEBSEC304", "Referrer-Policy", findings_by_header, root)
    )
    findings.extend(
        _text_presence_findings(
            root, "WEBSEC305", _PERMISSIONS_POLICY_RE, "Permissions-Policy"
        )
    )
    findings.extend(
        _text_presence_findings(root, "WEBSEC306", _COOP_COEP_CORP_RE, "COOP/COEP/CORP")
    )
    findings.extend(_cors_findings(root))
    findings.extend(_cache_control_findings(root))

    _log.info("websec_headers_rules: %d finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/webapp-websec-headers-rules.md#public-api
# frob:ticket T-5326
def websec_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """T-5311's `taint_gate` module-discovery hook: every
    `frob.webapp._websec_*` module exposing a module-level
    `websec_findings(root, frameworks) -> tuple[Violation, ...]` is
    auto-discovered and folded into `taint_gate`'s scan, so this WEBSEC
    family needs no `gates/__init__.py`/`_taint_gate.py` edit.
    `frameworks` is the caller's own already-computed
    `detect_frameworks(root)` result (avoids a second detect call per
    discovered module) -- an empty set short-circuits to `()` exactly
    like `websec_headers_rules_findings`'s own direct-call contract.

    frob:ticket T-5326
    """
    if not frameworks:
        _log.debug(
            "websec_headers_rules: no framework detected at %s, skipping scan (hook)",
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
        for finding in websec_headers_rules_findings(root)
    )
