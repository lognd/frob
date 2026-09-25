"""WEBPERF109-115: server/network performance config
(docs/modules/webapp-webperf-server.md, T-5366), the T-5140 web-app
epic's server/network-performance leaf: response compression, general
caching headers, HTTP/2, next-gen image format hints, CDN cache hints,
a server-side cache layer over expensive queries, and two React
render-performance lint shapes (undebounced input handlers, missing
`useEffect` dependency arrays).

Config-file evidence (compression/caching-headers/HTTP2/CDN-hints) is
TEXT-REGEX over nginx/Caddy/Express/Flask config, the same
add_header/`app.use(...)` scanning idiom
`frob.webapp._websec_headers.lint_response_headers` (T-5325) already
established for this repo's config-file evidence gathering -- this
leaf writes its own small private regex set (the established "own tiny
copy, not a cross-module private import" posture every `_websec_*`/
`_webperf_*`/`_seo_*` leaf in this family follows, `_websec_headers_log`'s
own module docstring names the same reasoning) rather than importing
`_websec_headers`'s private helpers, since `REQUIRED_HEADERS` there is
fixed to five SECURITY headers (HSTS/nosniff/X-Frame-Options/CSP/
Referrer-Policy) and carries no Cache-Control/compression-shaped
vocabulary this leaf needs.

Cache-Control-on-hashed-assets is T-5143-2's job, pagination-on-list-
endpoints is T-5144-2's (also the route-level authorization leaf's own
WEBSEC406, T-5357 -- lands separately), and DB-pool-config is
T-5148-4's -- this leaf blocks on all three and never re-implements
any of them (the ticket body's own cross-references).

SEVEN RULE IDS, filling the entire reserved `WEBPERF109`-`WEBPERF115`
block:

- WEBPERF109: no compression middleware/config found anywhere in a
  tracked nginx.conf/Caddyfile/Express `app.js`/Flask `app.py`
  (`gzip on;`/`compression()`/`flask_compress`).
- WEBPERF110: an nginx/Caddy config with no `Cache-Control` directive
  anywhere -- general response caching headers, distinct from
  T-5143-2's hashed-asset-specific check.
- WEBPERF111: an nginx config with TLS enabled (`listen ... ssl`) but
  no `http2` keyword anywhere in the file.
- WEBPERF112: an `<img>` tag referencing a `.jpg`/`.png` source in a
  file with no `.webp`/`.avif` reference anywhere -- no next-gen image
  format offered at all.
- WEBPERF113: a static-asset nginx `location` block with no
  `public`/`immutable` `Cache-Control` directive value -- CDN cache
  hint.
- WEBPERF114: an ORM query call (`.objects.all(`/`.query(`) in a
  Python handler file with no caching call/decorator
  (`cache`/`memoize`/`redis`) anywhere in that file -- no server cache
  layer over a potentially expensive, repeated query.
- WEBPERF115: a JSX/TSX `onChange={...}` handler with no `debounce`
  reference anywhere in the file, or a `useEffect(` call with no
  second (dependency-array) argument at all -- undebounced-input/
  unbounded-re-render React shapes.

Each fires WARN-tier at first turn-on, the same T-0688/T-0973 promotion
posture every other brand-new WEBSEC/SEO/WEBPERF family in this repo
follows.

DISCOVERY: same posture T-5374's `_seo_tags`/T-5365's `_seo_spam`/
T-5362's `_seo_crawl` module docstrings document in full --
`docs/modules/webapp-seo.md` defines no leaf-hook convention, and
`frob.gates._taint_gate`'s pkgutil discovery only scans
`frob.webapp._websec_*`-prefixed modules, so this module's
`websec_findings` hook is NOT currently auto-discovered by any live
gate either. T-draft-553232aa is the actual fix (widening
`_taint_gate`'s already-generalized discovered-prefix tuple,
`("_websec_", "_comply_")` since T-5372, to also include `_seo_`/
`_webperf_`); once it lands, this module's hook is discovered for free.
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
    "WebsecWebperfServerFinding",
    "webperf_server_findings",
    "websec_findings",
]

_COMPRESSION_HINT_RE = re.compile(
    r"""gzip\s+on\s*;|compression\s*\(\s*\)|flask[-_]compress""", re.IGNORECASE
)

_CACHE_CONTROL_RE = re.compile(r"""cache-control""", re.IGNORECASE)

_NGINX_SSL_LISTEN_RE = re.compile(r"""^\s*listen\s+[^\n;]*\bssl\b""", re.MULTILINE)
_HTTP2_RE = re.compile(r"""http2""", re.IGNORECASE)

_IMG_LEGACY_SRC_RE = re.compile(
    r"""<img\b[^>]*\bsrc\s*=\s*["'][^"']+\.(?:jpe?g|png)["']""", re.IGNORECASE
)
_NEXT_GEN_IMAGE_RE = re.compile(r"""\.(?:webp|avif)\b""", re.IGNORECASE)

_STATIC_LOCATION_BLOCK_RE = re.compile(
    r"""location\s+~\*?\s*\\\.\([^)]*(?:js|css|png|jpg)[^)]*\)[^{]*\{([^}]*)\}""",
    re.IGNORECASE | re.DOTALL,
)
_PUBLIC_IMMUTABLE_RE = re.compile(r"""public|immutable""", re.IGNORECASE)

_EXPENSIVE_QUERY_RE = re.compile(r"""\.objects\.all\s*\(|\.query\s*\(""")
_CACHE_LAYER_HINT_RE = re.compile(r"""\bcache\b|\bmemoize\b|\bredis\b""", re.IGNORECASE)

_ON_CHANGE_HANDLER_RE = re.compile(r"""onChange\s*=\s*\{""")
_DEBOUNCE_HINT_RE = re.compile(r"""debounce""", re.IGNORECASE)

_USE_EFFECT_NO_DEPS_RE = re.compile(
    r"""useEffect\s*\(\s*(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>\s*\{[^}]*\}\s*\)"""
)


# frob:doc docs/modules/webapp-webperf-server.md#public-api
# frob:ticket T-5366
@dataclass(frozen=True)
class WebsecWebperfServerFinding:
    """One WEBPERF109-115 finding: a missing server/network performance
    config, or a React render-performance lint shape.

    frob:ticket T-5366
    """

    rule: str
    file: str
    line: int
    message: str


def _tracked_files(root: Path, *suffixes: str) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `suffixes`, root-relative
    POSIX paths, `()` on any git failure -- mirrors
    `_websec_headers_log._tracked_files`'s own tracked-file-scan shape.

    frob:ticket T-5366
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("webperf_server: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("webperf_server: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(suffixes)
    )


def _tracked_named_files(root: Path, name: str) -> tuple[str, ...]:
    """Every tracked file literally named `name` anywhere under `root`.

    frob:ticket T-5366
    """
    return tuple(
        rel for rel in _tracked_files(root, name) if rel.rsplit("/", 1)[-1] == name
    )


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable.

    frob:ticket T-5366
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _line_of(text: str, offset: int) -> int:
    """1-based line number of char `offset` in `text`.

    frob:ticket T-5366
    """
    return text.count("\n", 0, offset) + 1


def _compression_findings(root: Path) -> list[WebsecWebperfServerFinding]:
    """WEBPERF109: no compression middleware/config found ANYWHERE
    across every relevant config/entrypoint file -- a repo-wide
    aggregate check (one finding for the whole repo, not one per file
    that individually lacks the hint; a Flask app's compression config
    typically lives in exactly one of these files, not all of them).

    frob:ticket T-5366
    """
    candidates = _tracked_files(root, "nginx.conf", "Caddyfile", "app.py", "app.js")
    if not candidates:
        return []
    combined = "\n".join(_read_text(root / rel) for rel in candidates)
    if _COMPRESSION_HINT_RE.search(combined):
        return []
    return [
        WebsecWebperfServerFinding(
            rule="WEBPERF109",
            file=candidates[0],
            line=1,
            message=(
                f"WEBPERF109: no compression middleware/config found "
                f"anywhere across {', '.join(candidates)} -- responses "
                f"ship uncompressed. Enable gzip/brotli, or `frob:waive "
                f'WEBPERF109 reason="..."` with a real justification'
            ),
        )
    ]


def _cache_control_findings(root: Path) -> list[WebsecWebperfServerFinding]:
    """WEBPERF110: no `Cache-Control` directive anywhere in a proxy
    config.

    frob:ticket T-5366
    """
    findings: list[WebsecWebperfServerFinding] = []
    for rel in _tracked_files(root, "nginx.conf", "Caddyfile"):
        text = _read_text(root / rel)
        if _CACHE_CONTROL_RE.search(text):
            continue
        findings.append(
            WebsecWebperfServerFinding(
                rule="WEBPERF110",
                file=rel,
                line=1,
                message=(
                    f"WEBPERF110: {rel} sets no Cache-Control directive "
                    f"anywhere. Add one, or `frob:waive WEBPERF110 reason="
                    f'"..."` with a real justification'
                ),
            )
        )
    return findings


def _http2_findings(root: Path) -> list[WebsecWebperfServerFinding]:
    """WEBPERF111: TLS enabled with no `http2` keyword.

    frob:ticket T-5366
    """
    findings: list[WebsecWebperfServerFinding] = []
    for rel in _tracked_named_files(root, "nginx.conf"):
        text = _read_text(root / rel)
        match = _NGINX_SSL_LISTEN_RE.search(text)
        if match is None or _HTTP2_RE.search(text):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecWebperfServerFinding(
                rule="WEBPERF111",
                file=rel,
                line=line,
                message=(
                    f"WEBPERF111: {rel}:{line} TLS is enabled with no "
                    f"http2 keyword anywhere -- HTTP/2 is off. Enable it, "
                    f'or `frob:waive WEBPERF111 reason="..."` with a '
                    f"real justification"
                ),
            )
        )
    return findings


def _image_format_findings(root: Path) -> list[WebsecWebperfServerFinding]:
    """WEBPERF112: a legacy-format `<img>` with no next-gen format
    offered anywhere in the file.

    frob:ticket T-5366
    """
    findings: list[WebsecWebperfServerFinding] = []
    for rel in _tracked_files(root, ".html", ".jsx", ".tsx"):
        text = _read_text(root / rel)
        match = _IMG_LEGACY_SRC_RE.search(text)
        if match is None or _NEXT_GEN_IMAGE_RE.search(text):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecWebperfServerFinding(
                rule="WEBPERF112",
                file=rel,
                line=line,
                message=(
                    f"WEBPERF112: {rel}:{line} an <img> references a "
                    f"legacy jpg/png source with no webp/avif offered "
                    f"anywhere in this file. Add a next-gen source, or "
                    f'`frob:waive WEBPERF112 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _cdn_cache_hint_findings(root: Path) -> list[WebsecWebperfServerFinding]:
    """WEBPERF113: a static-asset location block with no
    `public`/`immutable` Cache-Control value.

    frob:ticket T-5366
    """
    findings: list[WebsecWebperfServerFinding] = []
    for rel in _tracked_named_files(root, "nginx.conf"):
        text = _read_text(root / rel)
        for match in _STATIC_LOCATION_BLOCK_RE.finditer(text):
            block = match.group(1)
            if _PUBLIC_IMMUTABLE_RE.search(block):
                continue
            line = _line_of(text, match.start())
            findings.append(
                WebsecWebperfServerFinding(
                    rule="WEBPERF113",
                    file=rel,
                    line=line,
                    message=(
                        f"WEBPERF113: {rel}:{line} a static-asset "
                        f"location block sets no public/immutable "
                        f"Cache-Control value -- a CDN in front of this "
                        f"origin cannot cache aggressively. Add one, or "
                        f'`frob:waive WEBPERF113 reason="..."` with a '
                        f"real justification"
                    ),
                )
            )
    return findings


def _server_cache_layer_findings(root: Path) -> list[WebsecWebperfServerFinding]:
    """WEBPERF114: an expensive-looking ORM query with no caching
    call/decorator anywhere in the same file.

    frob:ticket T-5366
    """
    findings: list[WebsecWebperfServerFinding] = []
    for rel in _tracked_files(root, ".py"):
        text = _read_text(root / rel)
        match = _EXPENSIVE_QUERY_RE.search(text)
        if match is None or _CACHE_LAYER_HINT_RE.search(text):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecWebperfServerFinding(
                rule="WEBPERF114",
                file=rel,
                line=line,
                message=(
                    f"WEBPERF114: {rel}:{line} a query runs with no "
                    f"caching call/decorator anywhere in this file -- a "
                    f"repeated, potentially expensive query re-executes "
                    f"on every request. Add a cache layer, or `frob:waive "
                    f'WEBPERF114 reason="..."` with a real justification'
                ),
            )
        )
    return findings


def _react_render_perf_findings(root: Path) -> list[WebsecWebperfServerFinding]:
    """WEBPERF115: an undebounced `onChange` handler, or a `useEffect`
    call with no dependency-array argument.

    frob:ticket T-5366
    """
    findings: list[WebsecWebperfServerFinding] = []
    for rel in _tracked_files(root, ".jsx", ".tsx"):
        text = _read_text(root / rel)
        on_change_match = _ON_CHANGE_HANDLER_RE.search(text)
        if on_change_match is not None and not _DEBOUNCE_HINT_RE.search(text):
            line = _line_of(text, on_change_match.start())
            findings.append(
                WebsecWebperfServerFinding(
                    rule="WEBPERF115",
                    file=rel,
                    line=line,
                    message=(
                        f"WEBPERF115: {rel}:{line} an onChange handler "
                        f"has no debounce anywhere in this file -- every "
                        f"keystroke re-renders/re-fetches. Debounce it, "
                        f'or `frob:waive WEBPERF115 reason="..."` with a '
                        f"real justification"
                    ),
                )
            )
        effect_match = _USE_EFFECT_NO_DEPS_RE.search(text)
        if effect_match is not None:
            line = _line_of(text, effect_match.start())
            findings.append(
                WebsecWebperfServerFinding(
                    rule="WEBPERF115",
                    file=rel,
                    line=line,
                    message=(
                        f"WEBPERF115: {rel}:{line} useEffect has no "
                        f"dependency-array argument -- it runs on every "
                        f"render, unbounded. Add a dependency array, or "
                        f'`frob:waive WEBPERF115 reason="..."` with a '
                        f"real justification"
                    ),
                )
            )
    return findings


# frob:doc docs/modules/webapp-webperf-server.md#public-api
# frob:ticket T-5366
def webperf_server_findings(root: Path) -> tuple[WebsecWebperfServerFinding, ...]:
    """WEBPERF109-115: every server/network performance-config finding
    under `root`.

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all -- the same contract every
    WEBSEC/COMPLY/A11Y/SEO/WEBPERF family in this repo uses (T-5302).
    """
    root = Path(root)
    if not detect_frameworks(root):
        _log.debug("webperf_server: no framework detected at %s, skipping scan", root)
        return ()

    findings: list[WebsecWebperfServerFinding] = []
    findings.extend(_compression_findings(root))
    findings.extend(_cache_control_findings(root))
    findings.extend(_http2_findings(root))
    findings.extend(_image_format_findings(root))
    findings.extend(_cdn_cache_hint_findings(root))
    findings.extend(_server_cache_layer_findings(root))
    findings.extend(_react_render_perf_findings(root))

    _log.info("webperf_server: %d finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/webapp-webperf-server.md#public-api
# frob:ticket T-5366
def websec_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """Hook named to match `frob.gates._taint_gate`'s discovery SHAPE
    (`websec_findings(root, frameworks) -> tuple[Violation, ...]`), the
    same convention every sibling WEBSEC/SEO/WEBPERF leaf follows -- see
    the module docstring's DISCOVERY section for why no live gate
    currently calls it (`_webperf_server` does not match `_taint_gate`'s
    discovered-prefix tuple; T-draft-553232aa is the actual fix).
    `frameworks` is a caller's own already-computed
    `detect_frameworks(root)` result; an empty set short-circuits to
    `()`, same contract as `webperf_server_findings`.
    """
    if not frameworks:
        _log.debug(
            "webperf_server: no framework detected at %s, skipping scan (hook)",
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
        for finding in webperf_server_findings(root)
    )
