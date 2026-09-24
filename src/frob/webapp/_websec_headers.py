"""Response-header lint engine (WEBSEC config/headers substrate,
docs/modules/webapp-websec-headers.md, T-5325): checks a repo's in-repo
evidence -- app-framework security settings (Django `SECURE_*`, Express
`helmet()`) and reverse-proxy config files (nginx `add_header`, Caddy
`header`) -- for the standard security response headers, and reports the
documented CDN/edge-layer gap (Cloudflare/Fastly dashboards etc.) as a
WARN advisory rather than a false ERROR when NO in-repo security surface
exists at all (owner directive, T-5325).

Builds on `frob.webapp._detect.detect_frameworks` (T-5302) to gate the
Django settings scan; never re-detects frameworks itself. App-code and
config-file evidence are both plain-text line scans (not a
`frob.lang`/tree-sitter walk): `frob.lang`'s identifier walker has no
javascript/typescript entry yet (T-3232 follow-up), so a uniform
line-scan idiom is used across nginx/Caddy/Django/helmet rather than
mixing a real AST walk for Python with a text scan for JS.
"""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel
from typani import Err, Ok, Result

from frob.excludes import iter_files
from frob.logging import get_logger
from frob.webapp._detect import FrameworkKind, detect_frameworks

_log = get_logger(__name__)

__all__ = [
    "REQUIRED_HEADERS",
    "HeaderFinding",
    "HeaderSourceKind",
    "HeaderStatus",
    "WebsecHeadersError",
    "lint_response_headers",
]

# frob:doc docs/modules/webapp-websec-headers.md#required-headers
# frob:ticket T-5325
REQUIRED_HEADERS: tuple[str, ...] = (
    "Strict-Transport-Security",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Content-Security-Policy",
    "Referrer-Policy",
)

# Django settings.py identifier -> the header it controls (T-5325 fixture set).
_DJANGO_SETTING_TO_HEADER: dict[str, str] = {
    "SECURE_HSTS_SECONDS": "Strict-Transport-Security",
    "SECURE_CONTENT_TYPE_NOSNIFF": "X-Content-Type-Options",
    "X_FRAME_OPTIONS": "X-Frame-Options",
    "CSP_DEFAULT_SRC": "Content-Security-Policy",
    "SECURE_REFERRER_POLICY": "Referrer-Policy",
}

# helmet()'s own default middleware stack sets these four; CSP is opt-in
# (contentSecurityPolicy option) and deliberately excluded here rather than
# guessed at.
_HELMET_DEFAULT_HEADERS: tuple[str, ...] = (
    "Strict-Transport-Security",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
)

_APP_CODE_EXTENSIONS = (".js", ".jsx", ".ts", ".tsx")

_NGINX_ADD_HEADER = re.compile(r"^\s*add_header\s+([A-Za-z][A-Za-z-]*)\s")
_CADDY_HEADER_LINE = re.compile(r"^\s*header\s+([A-Za-z][A-Za-z-]*)\s")
_CADDY_BLOCK_DIRECTIVE = re.compile(r"^([A-Za-z][A-Za-z-]*)\s")
_HELMET_CALL = re.compile(r"\bhelmet\s*\(")
_DJANGO_ASSIGNMENT = re.compile(r"^([A-Z][A-Z0-9_]*)\s*[:=]")


# frob:doc docs/modules/webapp-websec-headers.md#headersourcekind
# frob:ticket T-5325
# frob:tests \
# tests/unit/test_webapp_websec_headers.py::test_full_evidence_all_present[nginx_full-nginx] kind="unit"  # noqa: E501
class HeaderSourceKind(StrEnum):
    """Where a `HeaderFinding`'s evidence came from: Django `SECURE_*`
    settings, an Express `helmet()` call, a manual `response.headers[...]=`
    assignment, or an nginx/Caddy reverse-proxy config file."""

    APP_DJANGO = "app_django"
    APP_HELMET = "app_helmet"
    APP_MANUAL = "app_manual"
    NGINX = "nginx"
    CADDY = "caddy"


# frob:doc docs/modules/webapp-websec-headers.md#headerstatus
# frob:ticket T-5325
# frob:tests \
# tests/unit/test_webapp_websec_headers.py::test_full_evidence_all_present[nginx_full-nginx] kind="unit"  # noqa: E501
class HeaderStatus(StrEnum):
    """PRESENT (evidence sets the header), MISSING (a recognized in-repo
    security surface exists but does not set it -- an actionable ERROR),
    or ADVISORY (no in-repo security surface found at all -- the header may
    still be set at the CDN/edge layer, so this is a WARN, never a false
    ERROR; T-5325 owner directive)."""

    PRESENT = "present"
    MISSING = "missing"
    ADVISORY = "advisory"


# frob:doc docs/modules/webapp-websec-headers.md#websecheaderserror
# frob:ticket T-5325
# tests/unit/test_webapp_websec_headers.py::test_root_not_a_directory_is_err kind="unit"
class WebsecHeadersError(StrEnum):
    """Fallible-operation error for `lint_response_headers`."""

    ROOT_NOT_A_DIRECTORY = "root_not_a_directory"


# frob:doc docs/modules/webapp-websec-headers.md#headerfinding
# frob:ticket T-5325
# frob:tests \
# tests/unit/test_webapp_websec_headers.py::test_full_evidence_all_present[nginx_full-nginx] kind="unit"  # noqa: E501
class HeaderFinding(BaseModel):
    """One required header's lint result: its `HeaderStatus`, and -- for
    PRESENT/MISSING -- the evidence `HeaderSourceKind`/path/line the
    status was derived from (`None` for ADVISORY, which by definition has
    no in-repo evidence)."""

    header: str
    status: HeaderStatus
    source: HeaderSourceKind | None = None
    path: Path | None = None
    line: int | None = None
    message: str


def _iter_named_files(root: Path, name: str) -> tuple[Path, ...]:
    """Every file under `root` literally named `name`, routed through
    `frob.excludes.iter_files` (WALK001: prunes vendor/VCS/build
    directories -- and prefers a `git ls-files` fast path -- before ever
    descending, unlike a raw `Path.rglob`).

    frob:ticket T-5325
    """
    return tuple(path for path in iter_files(root) if path.name == name)


def _iter_files_with_extensions(
    root: Path, extensions: tuple[str, ...]
) -> tuple[Path, ...]:
    """Every file under `root` whose suffix is in `extensions`, routed
    through `frob.excludes.iter_files` (see `_iter_named_files`).

    frob:ticket T-5325
    """
    return tuple(path for path in iter_files(root) if path.suffix in extensions)


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable (missing,
    binary, permission) -- mirrors `frob.webapp._detect._read_text`'s own
    per-module copy of this exact shape.

    frob:ticket T-5325
    """
    try:
        # frob:waive EXHAUST003 reason="read_text's only undeclared escape is OSError, \
        # already the except clause below (T-5325)"
        return path.read_text("utf-8", "ignore")
    except OSError:
        return ""


def _canonical_header(name: str) -> str | None:
    """Case-insensitive match of `name` against `REQUIRED_HEADERS`, or
    `None` if it names none of them.

    frob:ticket T-5325
    """
    lowered = name.lower()
    for header in REQUIRED_HEADERS:
        if header.lower() == lowered:
            return header
    return None


def _first_match_per_line(text: str, pattern: re.Pattern[str]) -> dict[str, int]:
    """`pattern.match(line).group(1)` -> first matching 1-based line
    number, over every line of `text` -- the shared single-pass scan
    `_nginx_headers` and `_django_setting_assignments` both reduce to
    (extracted for DUP002: the two were a 95%-identical loop over a
    different compiled pattern).

    frob:ticket T-5325
    """
    found: dict[str, int] = {}
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = pattern.match(line)
        if match:
            found.setdefault(match.group(1), lineno)
    return found


def _nginx_headers(text: str) -> dict[str, int]:
    """Header name (as written) -> first matching 1-based line number, for
    every `add_header <Name> ...;` directive in an nginx config's text.

    frob:ticket T-5325
    """
    return _first_match_per_line(text, _NGINX_ADD_HEADER)


def _caddy_headers(text: str) -> dict[str, int]:
    """Header name (as written) -> first matching 1-based line number, for
    every header directive in a Caddyfile's text -- both the single-line
    `header <Name> "<value>"` form and each line inside a `header { ... }`
    block.

    frob:ticket T-5325
    """
    found: dict[str, int] = {}
    in_block = False
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if in_block:
            if line == "}":
                in_block = False
                continue
            match = _CADDY_BLOCK_DIRECTIVE.match(line)
            if match:
                found.setdefault(match.group(1), lineno)
            continue
        if line == "header {" or line.startswith("header {"):
            in_block = True
            continue
        match = _CADDY_HEADER_LINE.match(line)
        if match:
            found.setdefault(match.group(1), lineno)
    return found


def _config_file_evidence(root: Path) -> dict[str, tuple[HeaderSourceKind, Path, int]]:
    """Scan every nginx.conf/Caddyfile found under `root` for
    `REQUIRED_HEADERS` header directives; header -> (source, path, line)
    for the first match found, config-file evidence per (b) of T-5325's
    HeaderSourceKind union parser.

    frob:ticket T-5325
    """
    evidence: dict[str, tuple[HeaderSourceKind, Path, int]] = {}
    for path in _iter_named_files(root, "nginx.conf"):
        for raw_name, line in _nginx_headers(_read_text(path)).items():
            header = _canonical_header(raw_name)
            if header is not None:
                evidence.setdefault(header, (HeaderSourceKind.NGINX, path, line))
    for path in _iter_named_files(root, "Caddyfile"):
        for raw_name, line in _caddy_headers(_read_text(path)).items():
            header = _canonical_header(raw_name)
            if header is not None:
                evidence.setdefault(header, (HeaderSourceKind.CADDY, path, line))
    return evidence


def _django_setting_assignments(text: str) -> dict[str, int]:
    """Left-hand-side identifier -> first matching 1-based line number, for
    every top-level `NAME = ...` assignment in a Django settings.py's text
    (a plain-text scan, the same idiom `_nginx_headers`/`_caddy_headers`
    use for their config-file line parsers).

    frob:ticket T-5325
    """
    return _first_match_per_line(text, _DJANGO_ASSIGNMENT)


def _django_app_code_evidence(
    root: Path,
) -> dict[str, tuple[HeaderSourceKind, Path, int]]:
    """A line-level assignment scan over every `settings.py` under `root`,
    matched against `_DJANGO_SETTING_TO_HEADER`; header -> (source, path,
    line) for the first match, part (a)'s app-code lint for Django.

    frob:ticket T-5325
    """
    evidence: dict[str, tuple[HeaderSourceKind, Path, int]] = {}
    for path in _iter_named_files(root, "settings.py"):
        for name, line in _django_setting_assignments(_read_text(path)).items():
            header = _DJANGO_SETTING_TO_HEADER.get(name)
            if header is not None:
                evidence.setdefault(header, (HeaderSourceKind.APP_DJANGO, path, line))
    return evidence


def _helmet_app_code_evidence(
    root: Path,
) -> dict[str, tuple[HeaderSourceKind, Path, int]]:
    """A line-level `helmet(` call-site scan over every JS/TS file under
    `root`, flagging the Express `helmet()` middleware call: sets
    `_HELMET_DEFAULT_HEADERS` at the line of the first occurrence, part
    (a)'s app-code lint for the Express/helmet idiom.

    Same plain-text line-scan idiom part (b)'s nginx/Caddy config-file
    parsers and `_django_app_code_evidence` use -- not routed through
    `frob.lang.iter_identifiers`, since `frob.lang._extract.
    _IDENTIFIER_TYPES` has no javascript/typescript entry yet (a known
    gap, tracked as a T-3232 follow-up: `iter_identifiers` silently
    returns `()` for every JS/TS file today, so a JS identifier walk
    would find nothing anyway).

    frob:ticket T-5325
    """
    evidence: dict[str, tuple[HeaderSourceKind, Path, int]] = {}
    for path in _iter_files_with_extensions(root, _APP_CODE_EXTENSIONS):
        helmet_line: int | None = None
        # frob:waive PERF015 reason="path's own lines, not a second fs-walk (T-5325)"
        for lineno, line in enumerate(_read_text(path).splitlines(), start=1):
            if _HELMET_CALL.search(line):
                helmet_line = lineno
                break
        if helmet_line is None:
            continue
        for header in _HELMET_DEFAULT_HEADERS:
            evidence.setdefault(
                header, (HeaderSourceKind.APP_HELMET, path, helmet_line)
            )
    return evidence


# frob:ticket T-5325
def _security_surface_present(
    root: Path,
    frameworks: frozenset[FrameworkKind],
    config_evidence: dict[str, tuple[HeaderSourceKind, Path, int]],
    django_evidence: dict[str, tuple[HeaderSourceKind, Path, int]],
    helmet_evidence: dict[str, tuple[HeaderSourceKind, Path, int]],
) -> bool:
    """True if `root` has AT LEAST ONE recognized security surface (an
    nginx.conf, a Caddyfile, a Django settings.py under a detected Django
    project, or a helmet() call) -- independent of whether that surface
    sets any particular header, since a surface existing but omitting a
    header is exactly what turns MISSING (an actionable ERROR) apart from
    ADVISORY (no evidence to judge at all).

    frob:ticket T-5325
    """
    return bool(
        config_evidence
        or django_evidence
        or helmet_evidence
        or _iter_named_files(root, "nginx.conf")
        or _iter_named_files(root, "Caddyfile")
        or (
            FrameworkKind.DJANGO in frameworks
            and _iter_named_files(root, "settings.py")
        )
    )


def _header_finding(
    header: str,
    evidence: tuple[HeaderSourceKind, Path, int] | None,
    security_surface_present: bool,
) -> HeaderFinding:
    """One `HeaderFinding` for `header`: PRESENT if `evidence` is given,
    else MISSING when `security_surface_present`, else ADVISORY (T-5325's
    documented CDN/edge-layer gap -- no in-repo evidence to judge at all,
    never a false ERROR).

    frob:ticket T-5325
    """
    if evidence is not None:
        source, path, line = evidence
        return HeaderFinding(
            header=header,
            status=HeaderStatus.PRESENT,
            source=source,
            path=path,
            line=line,
            message=f"{header} set via {source.value} at {path}:{line}",
        )
    if security_surface_present:
        return HeaderFinding(
            header=header,
            status=HeaderStatus.MISSING,
            message=(
                f"{header} not set in any recognized in-repo security surface "
                "(nginx/Caddy config, Django SECURE_* settings, helmet())"
            ),
        )
    return HeaderFinding(
        header=header,
        status=HeaderStatus.ADVISORY,
        message=(
            f"no in-repo evidence for {header}; confirm at your edge "
            "(CDN/reverse-proxy dashboard) -- documented gap, T-5325"
        ),
    )


# frob:doc docs/modules/webapp-websec-headers.md#lint_response_headers
# frob:ticket T-5325
# frob:tests \
# tests/unit/test_webapp_websec_headers.py::test_full_evidence_all_present[nginx_full-nginx] kind="unit"  # noqa: E501
# frob:waive WIRE001 reason="engine only; T-5326 wires the gate rule ids" \
# follow_up="T-5326"
def lint_response_headers(
    root: Path,
) -> Result[tuple[HeaderFinding, ...], WebsecHeadersError]:
    """Lint `root` for the `REQUIRED_HEADERS` security response headers.

    Combines app-code evidence (Django `SECURE_*` settings, gated on
    `detect_frameworks` reporting `FrameworkKind.DJANGO` so this never
    scans a non-Django `settings.py`-named file; a bare `helmet()` call)
    with config-file evidence (nginx `add_header`, Caddy `header`
    directives) -- see `_header_finding` for the PRESENT/MISSING/ADVISORY
    decision rule between them (the documented CDN/edge-layer gap, T-5325
    owner directive: a plain repo with no security surface should not
    report a false ERROR for a header that may be set entirely outside
    the repo, only a WARN advisory to confirm at the edge).

    `Err(WebsecHeadersError.ROOT_NOT_A_DIRECTORY)` if `root` does not
    resolve to an existing directory.
    """
    if not root.is_dir():
        _log.warning("websec_headers: root is not a directory: %s", root)
        return Err(WebsecHeadersError.ROOT_NOT_A_DIRECTORY)

    frameworks = detect_frameworks(root)
    config_evidence = _config_file_evidence(root)
    django_evidence = (
        _django_app_code_evidence(root) if FrameworkKind.DJANGO in frameworks else {}
    )
    helmet_evidence = _helmet_app_code_evidence(root)
    surface_present = _security_surface_present(
        root, frameworks, config_evidence, django_evidence, helmet_evidence
    )

    combined_evidence: dict[str, tuple[HeaderSourceKind, Path, int]] = {}
    combined_evidence.update(config_evidence)
    for header, evidence in {**django_evidence, **helmet_evidence}.items():
        combined_evidence.setdefault(header, evidence)

    findings = tuple(
        _header_finding(header, combined_evidence.get(header), surface_present)
        for header in REQUIRED_HEADERS
    )

    present = sum(1 for f in findings if f.status == HeaderStatus.PRESENT)
    missing = sum(1 for f in findings if f.status == HeaderStatus.MISSING)
    advisory = sum(1 for f in findings if f.status == HeaderStatus.ADVISORY)
    _log.info(
        "websec_headers: %s: %d present, %d missing, %d advisory",
        root,
        present,
        missing,
        advisory,
    )
    return Ok(findings)
