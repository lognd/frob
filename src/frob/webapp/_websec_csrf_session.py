"""WEBSEC201-208: CSRF and session lifecycle (docs/modules/webapp-websec-
csrf-session.md, T-5351, the T-5140 web-app epic's CSRF/session leaf).

Same posture as every WEBSEC family in this epic: framework-gated
(short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
reports no web framework, T-5302's own contract), and folded into
`frob.gates._taint_gate.taint_gate` via the `websec_findings(root,
frameworks)` pkgutil-discovery hook (T-5308) rather than a second gate
registration.

EIGHT RULE IDS (T-5301's reserved `WEBSEC201`-`WEBSEC208` block), split
exactly the way the ticket body itself splits them -- four "handler-
shape" rules read a route/controller file's own text, four "config"
rules read T-5349's normalized `SessionConfig`
(`frob.webapp._websec_session_config.read_session_config`) instead of
re-parsing the framework's session-config file:

Handler-shape (text-window scan over route/controller source, the same
disclosed-gap "textual proxy, not resolved data-flow" posture every
text-regex WEBSEC family in this epic carries):

- WEBSEC201: a state-changing GET route -- a GET-only route handler
  whose body calls a write-shaped method/verb (`.save(`/`.delete(`/
  `.destroy(`/`.update(`/`.create(`/an SQL DML keyword).
- WEBSEC204: a client-only session-validity check -- a handler compares
  a client-supplied cookie/header value directly against a literal or
  another client-supplied value, with no server-side session-store/DB
  lookup call anywhere in the same file.
- WEBSEC205: no session-id rotation on login -- a login-shaped handler
  (name containing "login"/"sign_in") sets session authentication state
  but the file has no session-rotation call anywhere
  (`cycle_key`/`regenerate`/`reset_session`/`session.regenerate`).
- WEBSEC208: logout with no server-side invalidation -- a logout-shaped
  handler (name containing "logout"/"sign_out") exists but the file has
  no session-invalidation call anywhere (`session.flush`/`session.
  clear`/`.destroy(`/`reset_session`/`cycle_key`).

Config (T-5349's `SessionConfig`, one `read_session_config` call per
scan, never re-parsed here):

- WEBSEC202: `csrf_middleware_present` is `False`.
- WEBSEC203: `samesite` is `None` or `"none"` (case-insensitive) -- no
  SameSite attribute stated, or explicitly disabled.
- WEBSEC206: `idle_timeout` is `None` -- no idle session timeout
  configured.
- WEBSEC207: `absolute_timeout` is `None` -- no absolute session
  lifetime configured.

A NINTH corpus item, "the static half of account-enumeration-via-
error-text" (distinguishable login/signup error messages leaking
whether an account exists), has no rule id left in this eight-id
reservation (`WEBSEC201`-`WEBSEC208`, T-5301) and is deliberately left
unimplemented here -- filed as follow-up scope (see the T-5351 Done
report for the ticket id), the same "no id left in the reservation"
posture `_websec_headers_log.py`/`_websec_xss.py` already document for
their own fuller ticket-body corpora.

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
from frob.webapp._websec_session_config import read_session_config

_log = get_logger(__name__)

__all__ = [
    "WebsecCsrfSessionFinding",
    "websec_csrf_session_findings",
    "websec_findings",
]


# frob:doc docs/modules/webapp-websec-csrf-session.md#public-api
@dataclass(frozen=True)
class WebsecCsrfSessionFinding:
    """One WEBSEC201-208 finding: a CSRF/session-lifecycle hardening gap
    in a route/controller file or a framework's session config.

    frob:ticket T-5351
    """

    rule: str
    file: str
    line: int
    message: str


#: Route-decorator/call shapes this scan recognizes as a GET-only route,
#: per framework family -- captures the route path for the message only.
_GET_ROUTE_RE = re.compile(
    r"""@app\.route\(\s*["']([^"']+)["']\s*(?:,\s*methods\s*=\s*\[\s*["']GET["']\s*\])?\s*\)|"""
    r"""app\.get\(\s*["']([^"']+)["']|"""
    r"""^\s*get\s+["']([^"']+)["']""",
    re.MULTILINE,
)

#: Write-shaped call/keyword this scan treats as "this handler mutates
#: state" -- a textual proxy, not a resolved data-flow (same disclosed
#: gap every text-regex WEBSEC family in this epic carries).
_WRITE_VERB_RE = re.compile(
    r"\.(save|delete|destroy|update|create)\(|"
    r"\b(INSERT|UPDATE|DELETE)\s+(?:INTO|FROM)?\b",
    re.IGNORECASE,
)

#: How far past a matched GET-route line this scan looks for a
#: write-verb call -- a fixed text window standing in for "this route
#: handler's own body" (no brace/indent-matching route-body isolation).
_HANDLER_WINDOW_CHARS = 400

_CLIENT_COOKIE_COMPARE_RE = re.compile(
    r"""(request\.cookies\.get\([^)]*\)|req\.cookies\.\w+)\s*==\s*"""
)
_SERVER_LOOKUP_RE = re.compile(
    r"Session\.query|SessionStore|redis|db\.session|session_store", re.IGNORECASE
)

_LOGIN_HANDLER_RE = re.compile(
    r"""def\s+\w*(login|sign_in)\w*\s*\(|function\s+\w*(login|sign_in)\w*\s*\(""",
    re.IGNORECASE,
)
_SESSION_AUTH_SET_RE = re.compile(
    r"""session\s*\[\s*["']user""" r"""|req\.session\.user\s*=|sign_in\("""
)
_ROTATION_RE = re.compile(
    r"cycle_key\(|\.regenerate\(|reset_session\(|session\.regenerate", re.IGNORECASE
)

_LOGOUT_HANDLER_RE = re.compile(
    r"""def\s+\w*(logout|sign_out)\w*\s*\(|function\s+\w*(logout|sign_out)\w*\s*\(""",
    re.IGNORECASE,
)
_INVALIDATION_RE = re.compile(
    r"session\.flush\(|session\.clear\(|\.destroy\(|reset_session\(|cycle_key\(",
    re.IGNORECASE,
)


def _tracked_files(root: Path, *suffixes: str) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `suffixes`, root-relative
    POSIX paths, `()` on any git failure -- mirrors `_websec_headers_log.
    _tracked_files`'s own tracked-file-scan shape.

    frob:ticket T-5351
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("websec_csrf_session: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("websec_csrf_session: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(suffixes)
    )


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable.

    frob:ticket T-5351
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _line_of(text: str, offset: int) -> int:
    """1-based line number of char `offset` in `text`.

    frob:ticket T-5351
    """
    return text.count("\n", 0, offset) + 1


def _state_changing_get_findings(
    text: str, rel_path: str
) -> list[WebsecCsrfSessionFinding]:
    """WEBSEC201: a GET-only route whose handler window calls a
    write-shaped method/verb.

    frob:ticket T-5351
    """
    findings: list[WebsecCsrfSessionFinding] = []
    for match in _GET_ROUTE_RE.finditer(text):
        route_path = next(g for g in match.groups() if g is not None)
        window = text[match.end() : match.end() + _HANDLER_WINDOW_CHARS]
        write_match = _WRITE_VERB_RE.search(window)
        if write_match is None:
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecCsrfSessionFinding(
                rule="WEBSEC201",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC201: {rel_path}:{line} GET route {route_path!r} "
                    f"appears to mutate state ({write_match.group(0)!r} in "
                    f"its handler) -- state-changing GET requests bypass "
                    f"CSRF protection and are cacheable/prefetchable. Use "
                    f"POST/PUT/DELETE for this action, or "
                    f'`frob:waive WEBSEC201 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _client_only_session_check_findings(
    text: str, rel_path: str
) -> list[WebsecCsrfSessionFinding]:
    """WEBSEC204: a client-supplied cookie/header value compared directly
    with no server-side session-store/DB lookup anywhere in the file.

    frob:ticket T-5351
    """
    findings: list[WebsecCsrfSessionFinding] = []
    if _SERVER_LOOKUP_RE.search(text):
        return findings
    for match in _CLIENT_COOKIE_COMPARE_RE.finditer(text):
        line = _line_of(text, match.start())
        findings.append(
            WebsecCsrfSessionFinding(
                rule="WEBSEC204",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC204: {rel_path}:{line} a client-supplied "
                    f"cookie/header value is compared directly with no "
                    f"server-side session-store/DB lookup anywhere in "
                    f"this file -- client-only session-validity check "
                    f"(forgeable). Validate against a server-side "
                    f"session store, or `frob:waive WEBSEC204 reason="
                    f'"..."` with a real justification'
                ),
            )
        )
    return findings


def _no_rotation_on_login_findings(
    text: str, rel_path: str
) -> list[WebsecCsrfSessionFinding]:
    """WEBSEC205: a login-shaped handler sets session auth state but the
    file has no session-rotation call anywhere.

    frob:ticket T-5351
    """
    login_match = _LOGIN_HANDLER_RE.search(text)
    if login_match is None:
        return []
    if not _SESSION_AUTH_SET_RE.search(text):
        return []
    if _ROTATION_RE.search(text):
        return []
    line = _line_of(text, login_match.start())
    return [
        WebsecCsrfSessionFinding(
            rule="WEBSEC205",
            file=rel_path,
            line=line,
            message=(
                f"WEBSEC205: {rel_path}:{line} a login handler sets "
                f"session authentication state but this file has no "
                f"session-id rotation call anywhere -- session fixation "
                f"risk. Call cycle_key()/regenerate() on successful "
                f'login, or `frob:waive WEBSEC205 reason="..."` with a '
                f"real justification"
            ),
        )
    ]


def _no_invalidation_on_logout_findings(
    text: str, rel_path: str
) -> list[WebsecCsrfSessionFinding]:
    """WEBSEC208: a logout-shaped handler exists but the file has no
    session-invalidation call anywhere.

    frob:ticket T-5351
    """
    logout_match = _LOGOUT_HANDLER_RE.search(text)
    if logout_match is None:
        return []
    if _INVALIDATION_RE.search(text):
        return []
    line = _line_of(text, logout_match.start())
    return [
        WebsecCsrfSessionFinding(
            rule="WEBSEC208",
            file=rel_path,
            line=line,
            message=(
                f"WEBSEC208: {rel_path}:{line} a logout handler exists "
                f"but this file has no server-side session-invalidation "
                f"call anywhere -- the session remains valid after "
                f"logout. Call session.flush()/session.destroy() on "
                f'logout, or `frob:waive WEBSEC208 reason="..."` with a '
                f"real justification"
            ),
        )
    ]


def _handler_shape_findings(path: Path, root: Path) -> list[WebsecCsrfSessionFinding]:
    """Every WEBSEC201/204/205/208 finding in one route/controller file.

    frob:ticket T-5351
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text:
        return []
    findings: list[WebsecCsrfSessionFinding] = []
    findings.extend(_state_changing_get_findings(text, rel_path))
    findings.extend(_client_only_session_check_findings(text, rel_path))
    findings.extend(_no_rotation_on_login_findings(text, rel_path))
    findings.extend(_no_invalidation_on_logout_findings(text, rel_path))
    return findings


def _config_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> list[WebsecCsrfSessionFinding]:
    """WEBSEC202/203/206/207: every config-shaped finding read out of
    T-5349's normalized `SessionConfig`, one `read_session_config` call
    per detected framework.

    frob:ticket T-5351
    """
    findings: list[WebsecCsrfSessionFinding] = []
    for framework in sorted(frameworks, key=lambda f: f.value):
        result = read_session_config(root, framework)
        if result.is_err:
            continue
        config = result.danger_ok
        rel_path = config.source_path.relative_to(root).as_posix()
        if not config.csrf_middleware_present:
            findings.append(
                WebsecCsrfSessionFinding(
                    rule="WEBSEC202",
                    file=rel_path,
                    line=1,
                    message=(
                        f"WEBSEC202: {rel_path}:1 no CSRF middleware is "
                        f"wired for {framework.value} -- state-changing "
                        f"requests are forgeable. Wire CSRF protection "
                        f"(CsrfViewMiddleware/CSRFProtect/csurf/"
                        f"protect_from_forgery), or "
                        f'`frob:waive WEBSEC202 reason="..."` with a '
                        f"real justification"
                    ),
                )
            )
        if config.samesite is None or config.samesite.lower() == "none":
            findings.append(
                WebsecCsrfSessionFinding(
                    rule="WEBSEC203",
                    file=rel_path,
                    line=1,
                    message=(
                        f"WEBSEC203: {rel_path}:1 the session cookie has "
                        f"no SameSite attribute stated (or it is "
                        f'explicitly "None") -- CSRF-adjacent, the '
                        f"cookie is sent on cross-site traffic. Set "
                        f"SameSite=Lax/Strict, or `frob:waive WEBSEC203 "
                        f'reason="..."` with a real justification'
                    ),
                )
            )
        if config.idle_timeout is None:
            findings.append(
                WebsecCsrfSessionFinding(
                    rule="WEBSEC206",
                    file=rel_path,
                    line=1,
                    message=(
                        f"WEBSEC206: {rel_path}:1 no idle session timeout "
                        f"is configured for {framework.value} -- a "
                        f"stolen/left-open session never expires from "
                        f"inactivity. Configure an idle timeout, or "
                        f'`frob:waive WEBSEC206 reason="..."` with a '
                        f"real justification"
                    ),
                )
            )
        if config.absolute_timeout is None:
            findings.append(
                WebsecCsrfSessionFinding(
                    rule="WEBSEC207",
                    file=rel_path,
                    line=1,
                    message=(
                        f"WEBSEC207: {rel_path}:1 no absolute session "
                        f"lifetime is configured for {framework.value} "
                        f"-- a session can be renewed indefinitely. "
                        f"Configure an absolute timeout, or `frob:waive "
                        f'WEBSEC207 reason="..."` with a real '
                        f"justification"
                    ),
                )
            )
    return findings


# frob:doc docs/modules/webapp-websec-csrf-session.md#public-api
# frob:ticket T-5351
def websec_csrf_session_findings(root: Path) -> tuple[WebsecCsrfSessionFinding, ...]:
    """WEBSEC201-208: every CSRF/session-lifecycle finding under `root`.

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all (T-5302's own contract, the same
    posture every WEBSEC family in this epic follows).

    frob:ticket T-5351
    """
    root = Path(root)
    frameworks = detect_frameworks(root)
    if not frameworks:
        _log.debug(
            "websec_csrf_session: no framework detected at %s, skipping scan", root
        )
        return ()

    findings: list[WebsecCsrfSessionFinding] = []
    for rel in _tracked_files(root, ".py", ".js", ".jsx", ".ts", ".tsx", ".rb"):
        findings.extend(_handler_shape_findings(root / rel, root))
    findings.extend(_config_findings(root, frameworks))

    _log.info("websec_csrf_session: %d finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/webapp-websec-csrf-session.md#public-api
# frob:ticket T-5351
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
    like `websec_csrf_session_findings`'s own direct-call contract.

    frob:ticket T-5351
    """
    if not frameworks:
        _log.debug(
            "websec_csrf_session: no framework detected at %s, skipping scan (hook)",
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
        for finding in websec_csrf_session_findings(root)
    )
