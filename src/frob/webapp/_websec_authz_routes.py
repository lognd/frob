"""WEBSEC401-407: route-level authorization
(docs/modules/webapp-websec-authz-routes.md, T-5357), the T-5140
web-app epic's route-level-authz leaf: admin routes with no auth
decorator, front-end-only permission guards, IDOR/BOLA (reusing
T-5356's `frob.webapp._websec_authz_substrate` walker, never
re-implementing it), mass assignment, field-level over-exposure,
list-endpoint pagination (this rule is the canonical owner of
list-endpoint-pagination; T-5147-6's WEBPERF leaf blocks on this one
instead of reimplementing the check), and per-user rate limiting on
auth/expensive endpoints.

WEBSEC401 is `_websec_authz_substrate`'s own IDOR/BOLA heuristic
(T-5356): that module is a leaf layer with no `frob.gates` import of
its own, so it hands back its own `AuthzFinding` model and leaves the
`frob.lang.raw_tree` parse call and the `Violation` wrapping to its
caller -- this module is that caller. `frob.webapp` is allowed to
import `frob.lang` directly (T-5307's `_websec_sinks` already does,
`[arch.layering]` in `frob.toml`), so `_idor_bola_findings` below calls
`raw_tree`/`scan_python_handlers`/`scan_rails_controller` itself, the
same `raw_tree(path, expect_heterogeneous=True)` idiom
`_websec_sinks._js_findings` already uses.

WEBSEC402-407 are TEXT-REGEX over tracked source files, the same idiom
`_websec_headers_log`/`_websec_debug_config`/`_websec_tokens`/
`_websec_password` already use for JS/TS and file-scope evidence
(`frob.lang`'s identifier walker has no javascript/typescript entry
yet, T-3232). Gated on `frob.webapp._detect.detect_frameworks`
reporting at least one web framework (T-5302's contract), and
discovered by `frob.gates._taint_gate`'s pkgutil hook (T-5308) via this
module's `websec_findings(root, frameworks)` -- no `_taint_gate.py`/
`gates/__init__.py` edit needed.

SEVEN RULE IDS, filling the entire reserved `WEBSEC401`-`WEBSEC407`
block (T-5301-shaped reservation, no unused id this time):

- WEBSEC401: an IDOR/BOLA-shaped handler -- `_websec_authz_substrate`'s
  own ORM-lookup-with-no-owner-correlation heuristic (T-5356).
- WEBSEC402: an admin-path route (`/admin` in the route string) with no
  framework auth decorator/middleware (`@login_required`/
  `@permission_required`/`@admin_required`/Django's
  `permission_classes`) attached.
- WEBSEC403: a front-end React Router `<Route path="...admin...">`
  with no wrapping guard component (`Guard`/`Protected`/`Private`/
  `RequireAuth` in the surrounding element name) -- a client-side-only
  permission check with no visible server enforcement in the SAME file
  the route table lives in (text-regex proxy, not a cross-referenced
  server route-table walk -- see the module's "Known gaps" doc
  section).
- WEBSEC404: mass assignment -- `request.json`/`request.POST`/
  `req.body` passed whole (via `**`/directly) to an ORM `create`/
  `update` call, with no field allowlist in between.
- WEBSEC405: field-level over-exposure -- an ORM model's `__dict__`/
  `.__table__.columns` serialized whole into a JSON response
  (`jsonify(x.__dict__)`/`res.json(user)` shaped), with no explicit
  field list/serializer.
- WEBSEC406: list-endpoint pagination -- an ORM `.all()` call in a file
  with no `limit`/`paginate`/`page`/slice (`[:N]`) reference anywhere
  in that file.
- WEBSEC407: an auth/expensive endpoint (`/login`/`/reset-password`/
  `/export` in the route string) with no rate-limit decorator/call
  (`limiter`/`ratelimit`/`throttle`) anywhere in that file.

Each fires WARN-tier at first turn-on, the same T-0688/T-0973 promotion
posture every other brand-new WEBSEC family in this repo follows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from frob.findings import Severity, Violation
from frob.gitio import run_argv
from frob.lang import raw_tree
from frob.logging import get_logger
from frob.webapp._detect import FrameworkKind, detect_frameworks
from frob.webapp._websec_authz_substrate import (
    scan_python_handlers,
    scan_rails_controller,
)

_log = get_logger(__name__)

__all__ = [
    "WebsecAuthzRouteFinding",
    "websec_authz_route_findings",
    "websec_findings",
]


# frob:doc docs/modules/webapp-websec-authz-routes.md#public-api
# frob:ticket T-5357
@dataclass(frozen=True)
class WebsecAuthzRouteFinding:
    """One WEBSEC401-407 finding: a route-level authorization gap --
    missing owner correlation, missing auth/rate-limit decoration, a
    front-end-only guard, mass assignment, field over-exposure, or
    unbounded list pagination.

    frob:ticket T-5357
    """

    rule: str
    file: str
    line: int
    message: str


_ADMIN_ROUTE_DECORATOR_RE = re.compile(
    r"""@\w+\.(?:route|get|post|put|patch|delete)\s*\(\s*["'][^"']*admin[^"']*["']""",
    re.IGNORECASE,
)
_AUTH_DECORATOR_RE = re.compile(
    r"""login_required|permission_required|admin_required|permission_classes""",
    re.IGNORECASE,
)

_REACT_ADMIN_ROUTE_RE = re.compile(
    r"""<Route\b[^>]*path\s*=\s*["'][^"']*admin[^"']*["'][^>]*>""", re.IGNORECASE
)
_ROUTE_GUARD_RE = re.compile(r"""Guard|Protected|Private|RequireAuth""")

_MASS_ASSIGNMENT_RE = re.compile(
    r"""\.(?:create|update)\s*\(\s*\*\*\s*(?:request\.(?:json|POST|form)|req\.body)\b|"""
    r"""\.(?:create|update)\s*\(\s*(?:request\.(?:json|POST|form)|req\.body)\s*\)""",
    re.IGNORECASE,
)

_FIELD_OVEREXPOSURE_RE = re.compile(
    r"""jsonify\s*\(\s*\w+\.__dict__\s*\)|res\.json\s*\(\s*\w+\s*\)""", re.IGNORECASE
)

_ORM_ALL_RE = re.compile(r"""\.objects\.all\s*\(\s*\)|\.find\s*\(\s*\)""")
_PAGINATION_HINT_RE = re.compile(
    r"""\blimit\b|\bpaginate\b|\bpage\b|\[\s*:\s*\w+\s*\]""", re.IGNORECASE
)

_SENSITIVE_ROUTE_DECORATOR_RE = re.compile(
    r"""@\w+\.(?:route|get|post|put|patch|delete)\s*\(\s*["'][^"']*"""
    r"""(?:login|reset-password|export)[^"']*["']""",
    re.IGNORECASE,
)
_RATE_LIMIT_HINT_RE = re.compile(r"""limiter|ratelimit|throttle""", re.IGNORECASE)


def _tracked_files(root: Path, *suffixes: str) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `suffixes`, root-relative
    POSIX paths, `()` on any git failure -- mirrors
    `_websec_headers_log._tracked_files`'s own tracked-file-scan shape.

    frob:ticket T-5357
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("websec_authz_routes: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("websec_authz_routes: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(suffixes)
    )


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable.

    frob:ticket T-5357
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _line_of(text: str, offset: int) -> int:
    """1-based line number of char `offset` in `text`.

    frob:ticket T-5357
    """
    return text.count("\n", 0, offset) + 1


def _idor_bola_findings(root: Path) -> list[WebsecAuthzRouteFinding]:
    """WEBSEC401: reuse `_websec_authz_substrate`'s own IDOR/BOLA
    heuristic over every tracked `.py`/`.rb` file (T-5356's walker,
    never re-implemented here).

    frob:ticket T-5357
    """
    findings: list[WebsecAuthzRouteFinding] = []
    for rel in _tracked_files(root, ".py"):
        parsed = raw_tree(root / rel, expect_heterogeneous=True)
        if parsed.is_err:
            _log.debug(
                "websec_authz_routes: skipping unparseable %s: %s",
                rel,
                parsed.danger_err,
            )
            continue
        tree, source, language = parsed.danger_ok
        if language != "python":
            continue
        scanned = scan_python_handlers(rel, tree.root_node, source, language)
        if scanned.is_err:
            continue
        for hit in scanned.danger_ok:
            findings.append(
                WebsecAuthzRouteFinding(
                    rule="WEBSEC401",
                    file=hit.file,
                    line=hit.line,
                    message=(
                        f"WEBSEC401: {hit.file}:{hit.line} handler "
                        f"{hit.handler!r} fetches a record by an ORM "
                        f"lookup/filter with no correlation to the "
                        f"authenticated user's own identity anywhere in "
                        f"its body -- IDOR/BOLA (another user's record "
                        f"id is accepted as-is). Filter on "
                        f"current_user/request.user/g.user, or `frob:waive "
                        f'WEBSEC401 reason="..."` with a real '
                        f"justification"
                    ),
                )
            )
    for rel in _tracked_files(root, ".rb"):
        text = _read_text(root / rel)
        for hit in scan_rails_controller(rel, text):
            findings.append(
                WebsecAuthzRouteFinding(
                    rule="WEBSEC401",
                    file=hit.file,
                    line=hit.line,
                    message=(
                        f"WEBSEC401: {hit.file}:{hit.line} action "
                        f"{hit.handler!r} fetches a record by an ORM "
                        f"lookup/filter with no correlation to the "
                        f"authenticated user's own identity anywhere in "
                        f"its body -- IDOR/BOLA. Filter on "
                        f"current_user/request.user/g.user, or `frob:waive "
                        f'WEBSEC401 reason="..."` with a real '
                        f"justification"
                    ),
                )
            )
    return findings


def _admin_route_findings(root: Path) -> list[WebsecAuthzRouteFinding]:
    """WEBSEC402: an admin-path route decorator with no auth decorator
    anywhere in the same file.

    frob:ticket T-5357
    """
    findings: list[WebsecAuthzRouteFinding] = []
    for rel in _tracked_files(root, ".py"):
        text = _read_text(root / rel)
        match = _ADMIN_ROUTE_DECORATOR_RE.search(text)
        if match is None or _AUTH_DECORATOR_RE.search(text):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecAuthzRouteFinding(
                rule="WEBSEC402",
                file=rel,
                line=line,
                message=(
                    f"WEBSEC402: {rel}:{line} an admin-path route has no "
                    f"framework auth decorator/permission check anywhere "
                    f"in this file. Add login_required/"
                    f"permission_required, or `frob:waive WEBSEC402 "
                    f'reason="..."` with a real justification'
                ),
            )
        )
    return findings


def _frontend_guard_findings(root: Path) -> list[WebsecAuthzRouteFinding]:
    """WEBSEC403: a React Router admin-path `<Route>` with no wrapping
    guard component.

    frob:ticket T-5357
    """
    findings: list[WebsecAuthzRouteFinding] = []
    for rel in _tracked_files(root, ".jsx", ".tsx"):
        text = _read_text(root / rel)
        for match in _REACT_ADMIN_ROUTE_RE.finditer(text):
            if _ROUTE_GUARD_RE.search(match.group(0)):
                continue
            line = _line_of(text, match.start())
            findings.append(
                WebsecAuthzRouteFinding(
                    rule="WEBSEC403",
                    file=rel,
                    line=line,
                    message=(
                        f"WEBSEC403: {rel}:{line} an admin-path route has "
                        f"no wrapping guard component (Guard/Protected/"
                        f"Private/RequireAuth) -- a front-end-only "
                        f"permission check is easy to bypass without a "
                        f"matching server-side enforcement. Wrap it in an "
                        f"auth guard, or `frob:waive WEBSEC403 reason="
                        f'"..."` with a real justification'
                    ),
                )
            )
    return findings


def _mass_assignment_findings(root: Path) -> list[WebsecAuthzRouteFinding]:
    """WEBSEC404: `request.json`/`req.body` passed whole to an ORM
    create/update call.

    frob:ticket T-5357
    """
    findings: list[WebsecAuthzRouteFinding] = []
    for rel in _tracked_files(root, ".py", ".js", ".jsx", ".ts", ".tsx"):
        text = _read_text(root / rel)
        match = _MASS_ASSIGNMENT_RE.search(text)
        if match is None:
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecAuthzRouteFinding(
                rule="WEBSEC404",
                file=rel,
                line=line,
                message=(
                    f"WEBSEC404: {rel}:{line} the whole request body is "
                    f"passed to an ORM create/update call -- mass "
                    f"assignment (an attacker-controlled field like "
                    f"is_admin/role is accepted as-is). Allowlist the "
                    f"fields explicitly, or `frob:waive WEBSEC404 reason="
                    f'"..."` with a real justification'
                ),
            )
        )
    return findings


def _field_overexposure_findings(root: Path) -> list[WebsecAuthzRouteFinding]:
    """WEBSEC405: a full ORM model serialized whole into a JSON
    response.

    frob:ticket T-5357
    """
    findings: list[WebsecAuthzRouteFinding] = []
    for rel in _tracked_files(root, ".py", ".js", ".jsx", ".ts", ".tsx"):
        text = _read_text(root / rel)
        match = _FIELD_OVEREXPOSURE_RE.search(text)
        if match is None:
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecAuthzRouteFinding(
                rule="WEBSEC405",
                file=rel,
                line=line,
                message=(
                    f"WEBSEC405: {rel}:{line} a full model object is "
                    f"serialized into the response with no explicit "
                    f"field list -- field-level over-exposure (an "
                    f"internal-only field like password_hash leaks). Use "
                    f"an explicit serializer/field allowlist, or "
                    f'`frob:waive WEBSEC405 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _pagination_findings(root: Path) -> list[WebsecAuthzRouteFinding]:
    """WEBSEC406: an ORM `.all()`/`.find()` call in a file with no
    pagination hint anywhere.

    frob:ticket T-5357
    """
    findings: list[WebsecAuthzRouteFinding] = []
    for rel in _tracked_files(root, ".py", ".js", ".jsx", ".ts", ".tsx"):
        text = _read_text(root / rel)
        match = _ORM_ALL_RE.search(text)
        if match is None or _PAGINATION_HINT_RE.search(text):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecAuthzRouteFinding(
                rule="WEBSEC406",
                file=rel,
                line=line,
                message=(
                    f"WEBSEC406: {rel}:{line} a list endpoint fetches the "
                    f"whole table with no limit/paginate/page/slice "
                    f"anywhere in this file -- unbounded pagination "
                    f"(a large table turns one request into a resource-"
                    f"exhaustion vector). Paginate the response, or "
                    f'`frob:waive WEBSEC406 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _rate_limit_findings(root: Path) -> list[WebsecAuthzRouteFinding]:
    """WEBSEC407: an auth/expensive-endpoint route with no rate-limit
    hint anywhere in the same file.

    frob:ticket T-5357
    """
    findings: list[WebsecAuthzRouteFinding] = []
    for rel in _tracked_files(root, ".py"):
        text = _read_text(root / rel)
        match = _SENSITIVE_ROUTE_DECORATOR_RE.search(text)
        if match is None or _RATE_LIMIT_HINT_RE.search(text):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecAuthzRouteFinding(
                rule="WEBSEC407",
                file=rel,
                line=line,
                message=(
                    f"WEBSEC407: {rel}:{line} an auth/expensive endpoint "
                    f"has no rate-limit decorator/call anywhere in this "
                    f"file -- unbounded per-user request rate (credential "
                    f"stuffing/brute force, or a costly export hammered "
                    f"repeatedly). Add a rate limiter, or `frob:waive "
                    f'WEBSEC407 reason="..."` with a real justification'
                ),
            )
        )
    return findings


# frob:doc docs/modules/webapp-websec-authz-routes.md#public-api
# frob:ticket T-5357
def websec_authz_route_findings(root: Path) -> tuple[WebsecAuthzRouteFinding, ...]:
    """WEBSEC401-407: every route-level authorization finding under
    `root`.

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all -- the same contract every
    WEBSEC/COMPLY/A11Y/SEO/WEBPERF family in this repo uses (T-5302).
    """
    root = Path(root)
    if not detect_frameworks(root):
        _log.debug(
            "websec_authz_routes: no framework detected at %s, skipping scan", root
        )
        return ()

    findings: list[WebsecAuthzRouteFinding] = []
    findings.extend(_idor_bola_findings(root))
    findings.extend(_admin_route_findings(root))
    findings.extend(_frontend_guard_findings(root))
    findings.extend(_mass_assignment_findings(root))
    findings.extend(_field_overexposure_findings(root))
    findings.extend(_pagination_findings(root))
    findings.extend(_rate_limit_findings(root))

    _log.info("websec_authz_routes: %d finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/webapp-websec-authz-routes.md#public-api
# frob:ticket T-5357
def websec_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """`frob.gates._taint_gate.taint_gate`'s module-discovery hook
    (T-5308): every `frob.webapp._websec_*` module exposing a
    module-level `websec_findings(root, frameworks) -> tuple[Violation,
    ...]` is auto-discovered and folded into `taint_gate`'s scan, so
    this WEBSEC401-407 family never needs its own `gates/__init__.py`/
    `_taint_gate.py` edit. `frameworks` is the caller's own
    already-computed `detect_frameworks(root)` result (avoids a second
    detect call per discovered module) -- an empty set short-circuits
    to `()`, same contract as `websec_authz_route_findings`.
    """
    if not frameworks:
        _log.debug(
            "websec_authz_routes: no framework detected at %s, skipping scan (hook)",
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
        for finding in websec_authz_route_findings(root)
    )
