"""WEBSEC310-316: debug/info-leak configuration
(docs/modules/webapp-websec-debug-config.md, T-5329), the T-5140 web-app
epic's debug/info-leak-config leaf: production-facing configuration that
discloses internal state to an attacker rather than a request-derived
taint flow (this module's checks are single-file evidence scans, unlike
`_websec_headers_log`'s source-to-sink pairing).

Same posture as the rest of the `_websec_*` family: TEXT-REGEX over
tracked source/config files, gated on `frob.webapp._detect.
detect_frameworks` reporting at least one web framework (T-5302's
contract), and discovered by `frob.gates._taint_gate`'s pkgutil hook
(T-5308) via this module's `websec_findings(root, frameworks)` -- no
`_taint_gate.py`/`gates/__init__.py` edit needed.

SEVEN RULE IDS used of the reserved `WEBSEC310`-`WEBSEC317` eight-id
block (T-5301-shaped reservation); `WEBSEC317` is left unimplemented --
see the T-5329 Done report for the follow-up ticket id:

- WEBSEC310: Django `DEBUG = True` left as a literal (not env-derived)
  in `settings.py`.
- WEBSEC311: source maps shipped to prod -- a webpack/vite config
  setting `devtool: 'source-map'`, or a tracked `.js.map`/`.css.map`
  file under a `build/`/`dist/` output directory.
- WEBSEC312: verbose stack traces in an error handler -- Flask
  `app.run(debug=True)`/`app.config['DEBUG'] = True`, or an Express
  error handler sending `err.stack` back in the response.
- WEBSEC313: directory listing left enabled -- nginx `autoindex on;` or
  Apache `Options +Indexes`.
- WEBSEC314: `.git`/`.svn` deployed -- a Dockerfile `COPY . .`-shaped
  broad copy with no sibling `.dockerignore` excluding `.git`.
- WEBSEC315: a public S3/GCS/Supabase bucket -- Terraform/CloudFormation
  IaC text containing `public-read`/`AllUsers`-shaped ACL grants (a
  regex scan, not a full HCL/CFN parser).
- WEBSEC316: a hardcoded-looking secret literal (`api_key`/`secret`/
  `token`/`password` assigned a long opaque string) in a tracked
  front-end bundle (`.js` under a `build/`/`dist/`/`static/` output
  directory) -- a small self-contained pattern table here, since
  T-5141's own reusable secret-pattern table has not landed yet (filed
  as a follow-up to fold this rule onto that table once it exists; see
  the T-5329 Done report).

Default-credential findings are SEC001-003's job, not duplicated here
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
    "WebsecDebugConfigFinding",
    "websec_debug_config_findings",
    "websec_findings",
]


# frob:doc docs/modules/webapp-websec-debug-config.md#public-api
# frob:ticket T-5329
@dataclass(frozen=True)
class WebsecDebugConfigFinding:
    """One WEBSEC310-316 finding: a production-facing configuration or
    build artifact that discloses internal state or source to an
    attacker.

    frob:ticket T-5329
    """

    rule: str
    file: str
    line: int
    message: str


_DJANGO_DEBUG_TRUE_RE = re.compile(r"^\s*DEBUG\s*=\s*True\s*$")

_SOURCE_MAP_CONFIG_RE = re.compile(r"""devtool\s*:\s*['"]source-map['"]""")
_MAP_FILE_SUFFIXES = (".js.map", ".css.map")
_BUILD_OUTPUT_DIR_RE = re.compile(r"(^|/)(build|dist|static)/")

_FLASK_DEBUG_RUN_RE = re.compile(r"app\.run\([^)]*debug\s*=\s*True")
_FLASK_DEBUG_CONFIG_RE = re.compile(r"""app\.config\[['"]DEBUG['"]\]\s*=\s*True""")
_EXPRESS_STACK_LEAK_RE = re.compile(
    r"""res\.(?:send|json)\(\s*\{?[^)]*\berr\.stack\b"""
)

_NGINX_AUTOINDEX_ON_RE = re.compile(r"^\s*autoindex\s+on\s*;")
_APACHE_INDEXES_RE = re.compile(r"^\s*Options\s+.*\+Indexes")

_DOCKERFILE_BROAD_COPY_RE = re.compile(r"^\s*COPY\s+\.\s+\S+", re.MULTILINE)

_PUBLIC_BUCKET_RE = re.compile(r"""public-read|AllUsers|publicRead|allUsers""")

_SECRET_ASSIGNMENT_RE = re.compile(
    r"""\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*"""
    r"""['"]([A-Za-z0-9_\-]{16,})['"]""",
    re.IGNORECASE,
)


def _tracked_files(root: Path, *suffixes: str) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `suffixes`, root-relative
    POSIX paths, `()` on any git failure -- mirrors
    `_websec_headers_log._tracked_files`'s own tracked-file-scan shape.

    frob:ticket T-5329
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("websec_debug_config: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("websec_debug_config: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(suffixes)
    )


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable.

    frob:ticket T-5329
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _line_of(text: str, offset: int) -> int:
    """1-based line number of char `offset` in `text`.

    frob:ticket T-5329
    """
    return text.count("\n", 0, offset) + 1


def _django_debug_findings(root: Path) -> list[WebsecDebugConfigFinding]:
    """WEBSEC310: Django `DEBUG = True` left as a literal in
    `settings.py`.

    frob:ticket T-5329
    """
    findings: list[WebsecDebugConfigFinding] = []
    for rel in _tracked_files(root, "settings.py"):
        text = _read_text(root / rel)
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _DJANGO_DEBUG_TRUE_RE.match(line):
                findings.append(
                    WebsecDebugConfigFinding(
                        rule="WEBSEC310",
                        file=rel,
                        line=lineno,
                        message=(
                            f"WEBSEC310: {rel}:{lineno} DEBUG = True is a "
                            f"literal, not env-derived -- Django's debug "
                            f"error pages leak source, settings and "
                            f"tracebacks if this ships to prod. Derive it "
                            f"from an environment variable defaulting to "
                            f'False, or `frob:waive WEBSEC310 reason="..."` '
                            f"with a real justification"
                        ),
                    )
                )
    return findings


def _source_map_findings(root: Path) -> list[WebsecDebugConfigFinding]:
    """WEBSEC311: source maps shipped to prod.

    frob:ticket T-5329
    """
    findings: list[WebsecDebugConfigFinding] = []
    for rel in _tracked_files(root, "webpack.config.js", "vite.config.js"):
        text = _read_text(root / rel)
        match = _SOURCE_MAP_CONFIG_RE.search(text)
        if match is None:
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecDebugConfigFinding(
                rule="WEBSEC311",
                file=rel,
                line=line,
                message=(
                    f"WEBSEC311: {rel}:{line} devtool: 'source-map' ships "
                    f"a full source map to prod -- an attacker can "
                    f"reconstruct original source from the deployed "
                    f"bundle. Use 'hidden-source-map' (upload-only) or "
                    f"disable maps for the prod build, or `frob:waive "
                    f'WEBSEC311 reason="..."` with a real justification'
                ),
            )
        )
    for rel in _tracked_files(root, *_MAP_FILE_SUFFIXES):
        if _BUILD_OUTPUT_DIR_RE.search(rel) is None:
            continue
        findings.append(
            WebsecDebugConfigFinding(
                rule="WEBSEC311",
                file=rel,
                line=1,
                message=(
                    f"WEBSEC311: {rel} a source map file is tracked "
                    f"inside a build/dist output directory -- it will "
                    f"ship to prod alongside the bundle it maps. Remove "
                    f"it from the tracked build output, or `frob:waive "
                    f'WEBSEC311 reason="..."` with a real justification'
                ),
            )
        )
    return findings


def _verbose_stack_trace_findings(root: Path) -> list[WebsecDebugConfigFinding]:
    """WEBSEC312: verbose stack traces in an error handler.

    frob:ticket T-5329
    """
    findings: list[WebsecDebugConfigFinding] = []
    for rel in _tracked_files(root, ".py"):
        text = _read_text(root / rel)
        for pattern in (_FLASK_DEBUG_RUN_RE, _FLASK_DEBUG_CONFIG_RE):
            match = pattern.search(text)
            if match is None:
                continue
            line = _line_of(text, match.start())
            findings.append(
                WebsecDebugConfigFinding(
                    rule="WEBSEC312",
                    file=rel,
                    line=line,
                    message=(
                        f"WEBSEC312: {rel}:{line} Flask debug mode is "
                        f"enabled -- its debug error page discloses a "
                        f"full traceback and an interactive shell to "
                        f"anyone hitting a 500. Disable debug for prod, "
                        f'or `frob:waive WEBSEC312 reason="..."` with a '
                        f"real justification"
                    ),
                )
            )
    for rel in _tracked_files(root, ".js", ".jsx", ".ts", ".tsx"):
        text = _read_text(root / rel)
        match = _EXPRESS_STACK_LEAK_RE.search(text)
        if match is None:
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecDebugConfigFinding(
                rule="WEBSEC312",
                file=rel,
                line=line,
                message=(
                    f"WEBSEC312: {rel}:{line} an error handler sends "
                    f"err.stack back in the response -- a full stack "
                    f"trace discloses internal file paths and framework "
                    f"internals to the client. Log the stack server-side "
                    f"and send a generic message instead, or `frob:waive "
                    f'WEBSEC312 reason="..."` with a real justification'
                ),
            )
        )
    return findings


def _directory_listing_findings(root: Path) -> list[WebsecDebugConfigFinding]:
    """WEBSEC313: directory listing left enabled.

    frob:ticket T-5329
    """
    findings: list[WebsecDebugConfigFinding] = []
    for rel in _tracked_files(root, "nginx.conf"):
        text = _read_text(root / rel)
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _NGINX_AUTOINDEX_ON_RE.match(line):
                findings.append(
                    WebsecDebugConfigFinding(
                        rule="WEBSEC313",
                        file=rel,
                        line=lineno,
                        message=(
                            f"WEBSEC313: {rel}:{lineno} autoindex on; "
                            f"serves a directory listing for any path "
                            f"with no index file -- discloses the full "
                            f"file layout to an attacker. Remove the "
                            f"directive or set it off, or `frob:waive "
                            f'WEBSEC313 reason="..."` with a real '
                            f"justification"
                        ),
                    )
                )
    for rel in _tracked_files(root, ".conf") + tuple(
        p for p in _tracked_files(root) if p.rsplit("/", 1)[-1] == "httpd.conf"
    ):
        text = _read_text(root / rel)
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _APACHE_INDEXES_RE.match(line):
                findings.append(
                    WebsecDebugConfigFinding(
                        rule="WEBSEC313",
                        file=rel,
                        line=lineno,
                        message=(
                            f"WEBSEC313: {rel}:{lineno} Options +Indexes "
                            f"serves a directory listing for any path "
                            f"with no index file -- discloses the full "
                            f"file layout to an attacker. Remove "
                            f"+Indexes, or `frob:waive WEBSEC313 reason="
                            f'"..."` with a real justification'
                        ),
                    )
                )
    return findings


def _dot_vcs_deployed_findings(root: Path) -> list[WebsecDebugConfigFinding]:
    """WEBSEC314: `.git`/`.svn` deployed via a broad Dockerfile `COPY`.

    frob:ticket T-5329
    """
    findings: list[WebsecDebugConfigFinding] = []
    for rel in _tracked_files(root, "Dockerfile"):
        text = _read_text(root / rel)
        match = _DOCKERFILE_BROAD_COPY_RE.search(text)
        if match is None:
            continue
        dockerignore = root / Path(rel).parent / ".dockerignore"
        ignore_text = _read_text(dockerignore)
        if ".git" in ignore_text:
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecDebugConfigFinding(
                rule="WEBSEC314",
                file=rel,
                line=line,
                message=(
                    f"WEBSEC314: {rel}:{line} COPY . . copies the whole "
                    f"build context into the image with no "
                    f".dockerignore excluding .git -- .git/.svn history "
                    f"(and any credentials it carries) ships inside the "
                    f"deployed image. Add a .dockerignore excluding "
                    f'.git, or `frob:waive WEBSEC314 reason="..."` with '
                    f"a real justification"
                ),
            )
        )
    return findings


def _public_bucket_findings(root: Path) -> list[WebsecDebugConfigFinding]:
    """WEBSEC315: a public S3/GCS/Supabase bucket grant in IaC.

    frob:ticket T-5329
    """
    findings: list[WebsecDebugConfigFinding] = []
    for rel in _tracked_files(root, ".tf", ".yaml", ".yml"):
        text = _read_text(root / rel)
        match = _PUBLIC_BUCKET_RE.search(text)
        if match is None:
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecDebugConfigFinding(
                rule="WEBSEC315",
                file=rel,
                line=line,
                message=(
                    f"WEBSEC315: {rel}:{line} an IaC resource grants "
                    f"public-read/AllUsers access -- a public bucket "
                    f"discloses every object it holds to anyone with "
                    f"the URL. Restrict the grant to a named "
                    f'principal, or `frob:waive WEBSEC315 reason="..."` '
                    f"with a real justification"
                ),
            )
        )
    return findings


def _frontend_secret_findings(root: Path) -> list[WebsecDebugConfigFinding]:
    """WEBSEC316: a hardcoded-looking secret literal in a tracked
    front-end bundle.

    frob:ticket T-5329
    """
    findings: list[WebsecDebugConfigFinding] = []
    for rel in _tracked_files(root, ".js"):
        if _BUILD_OUTPUT_DIR_RE.search(rel) is None and "static/" not in rel:
            continue
        text = _read_text(root / rel)
        match = _SECRET_ASSIGNMENT_RE.search(text)
        if match is None:
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecDebugConfigFinding(
                rule="WEBSEC316",
                file=rel,
                line=line,
                message=(
                    f"WEBSEC316: {rel}:{line} a hardcoded-looking "
                    f"secret literal is compiled into a tracked "
                    f"front-end bundle -- anything shipped to the "
                    f"browser is public. Move it server-side or into a "
                    f"runtime-injected config, or `frob:waive WEBSEC316 "
                    f'reason="..."` with a real justification'
                ),
            )
        )
    return findings


# frob:doc docs/modules/webapp-websec-debug-config.md#public-api
# frob:ticket T-5329
def websec_debug_config_findings(root: Path) -> tuple[WebsecDebugConfigFinding, ...]:
    """WEBSEC310-316: every debug/info-leak configuration finding under
    `root`.

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all -- the same contract every
    WEBSEC/COMPLY/A11Y/SEO/WEBPERF family in this repo uses (T-5302).
    """
    root = Path(root)
    if not detect_frameworks(root):
        _log.debug(
            "websec_debug_config: no framework detected at %s, skipping scan", root
        )
        return ()

    findings: list[WebsecDebugConfigFinding] = []
    findings.extend(_django_debug_findings(root))
    findings.extend(_source_map_findings(root))
    findings.extend(_verbose_stack_trace_findings(root))
    findings.extend(_directory_listing_findings(root))
    findings.extend(_dot_vcs_deployed_findings(root))
    findings.extend(_public_bucket_findings(root))
    findings.extend(_frontend_secret_findings(root))

    _log.info("websec_debug_config: %d finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/webapp-websec-debug-config.md#public-api
# frob:ticket T-5329
def websec_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """`frob.gates._taint_gate.taint_gate`'s module-discovery hook
    (T-5308): every `frob.webapp._websec_*` module exposing a
    module-level `websec_findings(root, frameworks) -> tuple[Violation,
    ...]` is auto-discovered and folded into `taint_gate`'s scan, so
    this WEBSEC310-316 family never needs its own `gates/__init__.py`/
    `_taint_gate.py` edit. `frameworks` is the caller's own
    already-computed `detect_frameworks(root)` result (avoids a second
    detect call per discovered module) -- an empty set short-circuits
    to `()`, same contract as `websec_debug_config_findings`.
    """
    if not frameworks:
        _log.debug(
            "websec_debug_config: no framework detected at %s, skipping scan (hook)",
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
        for finding in websec_debug_config_findings(root)
    )
