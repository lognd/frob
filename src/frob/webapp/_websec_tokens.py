"""WEBSEC209-216: JWT and OAuth token checks
(docs/modules/webapp-websec-jwt-oauth.md, T-5352), the T-5140 web-app
epic's JWT/OAuth-token leaf: call-argument and config-file evidence
around `jwt.decode`/`jsonwebtoken.verify` and an OAuth
authorization-code flow, rather than a request-derived taint flow.

Same posture as the rest of the `_websec_*` family: TEXT-REGEX over
tracked source/config files (the ticket body's own "AST lint on
jwt.decode/jsonwebtoken.verify call-argument presence" is approximated
as a call-site regex here, the same idiom `_websec_headers_log`/
`_websec_debug_config` already use for JS/TS evidence -- `frob.lang`'s
identifier walker has no javascript/typescript entry yet, T-3232), gated
on `frob.webapp._detect.detect_frameworks` reporting at least one web
framework (T-5302's contract), and discovered by
`frob.gates._taint_gate`'s pkgutil hook (T-5308) via this module's
`websec_findings(root, frameworks)` -- no `_taint_gate.py`/
`gates/__init__.py` edit needed.

EIGHT RULE IDS used of the reserved `WEBSEC209`-`WEBSEC217` nine-id
block (T-5301-shaped reservation); `WEBSEC217` is left unimplemented --
see the T-5352 Done report for the follow-up ticket id:

- WEBSEC209: `jwt.decode`/`jsonwebtoken.verify` explicitly disables
  exp/nbf validation (`verify_exp`/`verify_nbf` set `False`, or
  `ignoreExpiration`/`ignoreNotBefore` set `true`).
- WEBSEC210: a `jwt.decode`/`jsonwebtoken.verify` call site with no
  `audience`/`aud` argument at all -- no `aud` check means a token
  minted for a different service is accepted here.
- WEBSEC211: a `jwt.decode`/`jsonwebtoken.verify` call site with no
  `issuer`/`iss` argument at all -- no `iss` check, the token-type/
  issuer confusion shape.
- WEBSEC212: refresh-token config with rotation disabled (Django REST
  Framework SimpleJWT's `ROTATE_REFRESH_TOKENS: False`) or no absolute
  lifetime bound (`REFRESH_TOKEN_LIFETIME` absent from the same config
  block).
- WEBSEC213: a token is spliced into a URL query string or fragment
  (`?access_token=`/`?token=`/`#access_token=` string-built with a
  token-shaped variable) -- tokens in a URL leak via browser history,
  referrer headers and server access logs.
- WEBSEC214: an OAuth authorization-request URL built with no `state=`
  parameter -- CSRF on the OAuth flow.
- WEBSEC215: an OAuth client config with a wildcard/prefix-shaped
  `redirect_uri` (`redirect_uri: "*"` or a trailing-wildcard glob)
  instead of an exact match.
- WEBSEC216: an OAuth authorization-code request (`response_type=code`)
  with no `code_challenge` parameter -- PKCE not used.

Secrets-committed findings are SEC001-003's job, not duplicated here
(the ticket body's own cross-reference).

Each fires WARN-tier at first turn-on, the same T-0688/T-0973 promotion
posture every other brand-new WEBSEC family in this repo follows.
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
    "WebsecTokenFinding",
    "websec_findings",
    "websec_token_findings",
]


# frob:doc docs/modules/webapp-websec-jwt-oauth.md#public-api
# frob:ticket T-5352
@dataclass(frozen=True)
class WebsecTokenFinding:
    """One WEBSEC209-216 finding: a JWT validation gap or an OAuth
    authorization-code-flow config/call-argument weakness.

    frob:ticket T-5352
    """

    rule: str
    file: str
    line: int
    message: str


_JWT_CALL_RE = re.compile(r"\b(?:jwt\.decode|jwt\.verify)\s*\(([^;]*?)\)", re.DOTALL)

_EXP_NBF_DISABLED_RE = re.compile(
    r"""verify_exp["']?\s*[:=]\s*False|verify_nbf["']?\s*[:=]\s*False|"""
    r"""ignoreExpiration\s*:\s*true|ignoreNotBefore\s*:\s*true""",
    re.IGNORECASE,
)

_AUDIENCE_KWARG_RE = re.compile(r"""\b(?:audience|aud)\s*[:=]""")
_ISSUER_KWARG_RE = re.compile(r"""\b(?:issuer|iss)\s*[:=]""")

_ROTATE_REFRESH_FALSE_RE = re.compile(r"""ROTATE_REFRESH_TOKENS["']?\s*[:=]\s*False""")
_SIMPLE_JWT_BLOCK_RE = re.compile(r"SIMPLE_JWT\s*=\s*\{(.*?)\n\}", re.DOTALL)
_REFRESH_TOKEN_LIFETIME_RE = re.compile(r"REFRESH_TOKEN_LIFETIME")

_TOKEN_IN_URL_RE = re.compile(
    r"""["'][^"'\n]*[?#](?:access_)?token=["']?\s*\+|"""
    r"""f["'][^"'\n]*[?#](?:access_)?token=\{"""
)

_OAUTH_AUTHORIZE_URL_RE = re.compile(
    r"""["'][^"'\n]*response_type=code[^"'\n]*["']|"""
    r"""f["'][^"'\n]*response_type=code[^"'\n]*["']""",
    re.IGNORECASE,
)
_STATE_PARAM_RE = re.compile(r"""[?&]state=""", re.IGNORECASE)
_CODE_CHALLENGE_PARAM_RE = re.compile(r"""[?&]code_challenge=""", re.IGNORECASE)

_REDIRECT_URI_WILDCARD_RE = re.compile(
    r"""redirect_uri["']?\s*[:=]\s*["'][^"'\n]*\*[^"'\n]*["']""", re.IGNORECASE
)


def _tracked_files(root: Path, *suffixes: str) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `suffixes`, root-relative
    POSIX paths, `()` on any git failure -- mirrors
    `_websec_headers_log._tracked_files`'s own tracked-file-scan shape.

    frob:ticket T-5352
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("websec_tokens: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("websec_tokens: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(suffixes)
    )


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable.

    frob:ticket T-5352
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _line_of(text: str, offset: int) -> int:
    """1-based line number of char `offset` in `text`.

    frob:ticket T-5352
    """
    return text.count("\n", 0, offset) + 1


def _jwt_call_findings(root: Path) -> list[WebsecTokenFinding]:
    """WEBSEC209-211: exp/nbf disabled, missing `audience`, missing
    `issuer`, at each `jwt.decode`/`jwt.verify` call site.

    frob:ticket T-5352
    """
    findings: list[WebsecTokenFinding] = []
    for rel in _tracked_files(root, ".py", ".js", ".jsx", ".ts", ".tsx"):
        text = _read_text(root / rel)
        for match in _JWT_CALL_RE.finditer(text):
            args = match.group(1)
            line = _line_of(text, match.start())
            if _EXP_NBF_DISABLED_RE.search(args):
                findings.append(
                    WebsecTokenFinding(
                        rule="WEBSEC209",
                        file=rel,
                        line=line,
                        message=(
                            f"WEBSEC209: {rel}:{line} exp/nbf validation is "
                            f"explicitly disabled on this JWT decode/verify "
                            f"call -- an expired or not-yet-valid token is "
                            f"accepted. Remove the override, or `frob:waive "
                            f'WEBSEC209 reason="..."` with a real '
                            f"justification"
                        ),
                    )
                )
            if not _AUDIENCE_KWARG_RE.search(args):
                findings.append(
                    WebsecTokenFinding(
                        rule="WEBSEC210",
                        file=rel,
                        line=line,
                        message=(
                            f"WEBSEC210: {rel}:{line} this JWT decode/verify "
                            f"call passes no audience/aud argument -- a "
                            f"token minted for a different service is "
                            f"accepted here. Pass audience=..., or "
                            f'`frob:waive WEBSEC210 reason="..."` with a '
                            f"real justification"
                        ),
                    )
                )
            if not _ISSUER_KWARG_RE.search(args):
                findings.append(
                    WebsecTokenFinding(
                        rule="WEBSEC211",
                        file=rel,
                        line=line,
                        message=(
                            f"WEBSEC211: {rel}:{line} this JWT decode/verify "
                            f"call passes no issuer/iss argument -- "
                            f"token-type/issuer confusion (a token from a "
                            f"different issuer is accepted). Pass "
                            f"issuer=..., or `frob:waive WEBSEC211 reason="
                            f'"..."` with a real justification'
                        ),
                    )
                )
    return findings


def _refresh_token_config_findings(root: Path) -> list[WebsecTokenFinding]:
    """WEBSEC212: refresh-token rotation disabled or no absolute TTL
    bound in a Django SimpleJWT `SIMPLE_JWT` settings block.

    frob:ticket T-5352
    """
    findings: list[WebsecTokenFinding] = []
    for rel in _tracked_files(root, "settings.py"):
        text = _read_text(root / rel)
        block_match = _SIMPLE_JWT_BLOCK_RE.search(text)
        if block_match is None:
            continue
        block = block_match.group(1)
        line = _line_of(text, block_match.start())
        if _ROTATE_REFRESH_FALSE_RE.search(block):
            findings.append(
                WebsecTokenFinding(
                    rule="WEBSEC212",
                    file=rel,
                    line=line,
                    message=(
                        f"WEBSEC212: {rel}:{line} ROTATE_REFRESH_TOKENS is "
                        f"False -- a stolen refresh token stays valid "
                        f"indefinitely instead of being rotated on use. "
                        f"Set it True, or `frob:waive WEBSEC212 reason="
                        f'"..."` with a real justification'
                    ),
                )
            )
        elif _REFRESH_TOKEN_LIFETIME_RE.search(block) is None:
            findings.append(
                WebsecTokenFinding(
                    rule="WEBSEC212",
                    file=rel,
                    line=line,
                    message=(
                        f"WEBSEC212: {rel}:{line} SIMPLE_JWT sets no "
                        f"REFRESH_TOKEN_LIFETIME -- no absolute TTL bound "
                        f"on a refresh token. Add one, or `frob:waive "
                        f'WEBSEC212 reason="..."` with a real '
                        f"justification"
                    ),
                )
            )
    return findings


def _token_in_url_findings(root: Path) -> list[WebsecTokenFinding]:
    """WEBSEC213: a token is spliced into a URL query string or
    fragment.

    frob:ticket T-5352
    """
    findings: list[WebsecTokenFinding] = []
    for rel in _tracked_files(root, ".py", ".js", ".jsx", ".ts", ".tsx"):
        text = _read_text(root / rel)
        match = _TOKEN_IN_URL_RE.search(text)
        if match is None:
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecTokenFinding(
                rule="WEBSEC213",
                file=rel,
                line=line,
                message=(
                    f"WEBSEC213: {rel}:{line} a token is spliced into a "
                    f"URL query string or fragment -- it leaks via "
                    f"browser history, the Referer header and server "
                    f"access logs. Pass it in an Authorization header or "
                    f"a POST body instead, or `frob:waive WEBSEC213 "
                    f'reason="..."` with a real justification'
                ),
            )
        )
    return findings


def _oauth_flow_findings(root: Path) -> list[WebsecTokenFinding]:
    """WEBSEC214/WEBSEC216: an OAuth authorization-code-flow URL built
    with no `state=`/`code_challenge=` parameter.

    frob:ticket T-5352
    """
    findings: list[WebsecTokenFinding] = []
    for rel in _tracked_files(root, ".py", ".js", ".jsx", ".ts", ".tsx"):
        text = _read_text(root / rel)
        for match in _OAUTH_AUTHORIZE_URL_RE.finditer(text):
            line_text = match.group(0)
            line = _line_of(text, match.start())
            if not _STATE_PARAM_RE.search(line_text):
                findings.append(
                    WebsecTokenFinding(
                        rule="WEBSEC214",
                        file=rel,
                        line=line,
                        message=(
                            f"WEBSEC214: {rel}:{line} an OAuth "
                            f"authorization request is built with no "
                            f"state= parameter -- CSRF on the OAuth "
                            f"flow. Add a per-request random state and "
                            f"verify it on callback, or `frob:waive "
                            f'WEBSEC214 reason="..."` with a real '
                            f"justification"
                        ),
                    )
                )
            if not _CODE_CHALLENGE_PARAM_RE.search(line_text):
                findings.append(
                    WebsecTokenFinding(
                        rule="WEBSEC216",
                        file=rel,
                        line=line,
                        message=(
                            f"WEBSEC216: {rel}:{line} an OAuth "
                            f"authorization-code request is built with "
                            f"no code_challenge= parameter -- PKCE is "
                            f"not used on the authorization-code flow. "
                            f"Add PKCE, or `frob:waive WEBSEC216 reason="
                            f'"..."` with a real justification'
                        ),
                    )
                )
    return findings


def _redirect_uri_findings(root: Path) -> list[WebsecTokenFinding]:
    """WEBSEC215: an OAuth client config with a wildcard/prefix-shaped
    `redirect_uri`.

    frob:ticket T-5352
    """
    findings: list[WebsecTokenFinding] = []
    for rel in _tracked_files(root, ".py", ".js", ".jsx", ".ts", ".tsx", ".json"):
        text = _read_text(root / rel)
        match = _REDIRECT_URI_WILDCARD_RE.search(text)
        if match is None:
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecTokenFinding(
                rule="WEBSEC215",
                file=rel,
                line=line,
                message=(
                    f"WEBSEC215: {rel}:{line} redirect_uri is a "
                    f"wildcard/prefix-shaped value, not an exact match "
                    f"-- an attacker-controlled redirect target can "
                    f"exfiltrate the authorization code/token. Register "
                    f"and match an exact redirect_uri, or `frob:waive "
                    f'WEBSEC215 reason="..."` with a real justification'
                ),
            )
        )
    return findings


# frob:doc docs/modules/webapp-websec-jwt-oauth.md#public-api
# frob:ticket T-5352
def websec_token_findings(root: Path) -> tuple[WebsecTokenFinding, ...]:
    """WEBSEC209-216: every JWT/OAuth token finding under `root`.

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all -- the same contract every
    WEBSEC/COMPLY/A11Y/SEO/WEBPERF family in this repo uses (T-5302).
    """
    root = Path(root)
    if not detect_frameworks(root):
        _log.debug("websec_tokens: no framework detected at %s, skipping scan", root)
        return ()

    findings: list[WebsecTokenFinding] = []
    findings.extend(_jwt_call_findings(root))
    findings.extend(_refresh_token_config_findings(root))
    findings.extend(_token_in_url_findings(root))
    findings.extend(_oauth_flow_findings(root))
    findings.extend(_redirect_uri_findings(root))

    _log.info("websec_tokens: %d finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/webapp-websec-jwt-oauth.md#public-api
# frob:ticket T-5352
def websec_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """`frob.gates._taint_gate.taint_gate`'s module-discovery hook
    (T-5308): every `frob.webapp._websec_*` module exposing a
    module-level `websec_findings(root, frameworks) -> tuple[Violation,
    ...]` is auto-discovered and folded into `taint_gate`'s scan, so
    this WEBSEC209-216 family never needs its own `gates/__init__.py`/
    `_taint_gate.py` edit. `frameworks` is the caller's own
    already-computed `detect_frameworks(root)` result (avoids a second
    detect call per discovered module) -- an empty set short-circuits
    to `()`, same contract as `websec_token_findings`.
    """
    if not frameworks:
        _log.debug(
            "websec_tokens: no framework detected at %s, skipping scan (hook)", root
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
        for finding in websec_token_findings(root)
    )
