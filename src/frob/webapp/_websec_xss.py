"""WEBSEC107-108: output-encoding/template-sink refinements on top of the
T-5307 XSS sink substrate (docs/modules/webapp-websec-xss.md).

T-5307's `frob.webapp._websec_sinks.websec_sink_findings` already owns
WEBSEC101-106 (the six sink kinds its own module docstring names: JS/TS
`.innerHTML`/`.outerHTML`/`document.write`/`insertAdjacentHTML` AST,
JSX `dangerouslySetInnerHTML`, Vue `v-html`, Jinja `|safe`/
`autoescape=False`, Django `mark_safe`/`{% autoescape off %}`, and Rails
`.html_safe`/`raw(...)`). This module claims the two reserved rule ids
directly above that block (T-5301's `WEBSEC107`/`WEBSEC108` reservation,
docs/design/registry/check-coverage.yaml) for two sink shapes the T-5307
corpus explicitly left out of its own six:

- WEBSEC107: Rails' EXPLICIT unescaped-output ERB tag `<%== expr %>`
  (as opposed to `.html_safe`/`raw(...)`, which WEBSEC106 already owns
  -- `<%==` is a distinct autoescape-bypass SHAPE in the same ecosystem,
  never emitted by the WEBSEC106 regex pair, so this is a genuinely new
  finder, not a second finder re-emitting an already-claimed id).
- WEBSEC108: PHP `echo`/`print`/short-echo (`<?= ... ?>`) of a raw
  superglobal (`$_GET`/`$_POST`/`$_REQUEST`/`$_COOKIE`/`$_SERVER`/
  `$_FILES`) with no `htmlspecialchars(...)` wrap -- the PHP output-
  encoding sink family, unclaimed by any prior WEBSEC10x finder (T-5307
  never reads `.php` at all).

Both are TEXT-REGEX, same posture `_websec_sinks`'s own WEBSEC104/105/106
finders already document: neither shape is a tree-sitter-parseable
grammar frob ships (no PHP grammar; ERB tags are not the Ruby grammar
proper). `websec_xss_findings` is the one entry point --
`frob.gates._taint_gate.taint_gate` folds its output into the same
`Violation` tuple as `websec_sink_findings`'s WEBSEC101-106, exactly the
way T-5307 folded that call in alongside SEC005 (one gate call site,
not a second parallel registration).

FRAMEWORK GATING (T-5302): short-circuits to no scan when
`frob.webapp._detect.detect_frameworks` reports no web framework, the
same posture every other WEBSEC/COMPLY/A11Y/SEO/WEBPERF family and
`_websec_sinks` itself already take.
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

__all__ = ["WebsecXssFinding", "websec_xss_findings", "websec_findings"]

#: Call/receiver names treated as "already escaped/sanitized" -- same
#: family `frob.webapp._websec_sinks._SANITIZER_NAME_RE` uses for the
#: WEBSEC101-106 substrate this module extends.
_SANITIZER_NAME_RE = re.compile(
    r"(DOMPurify|sanitize|escape|htmlspecialchars|clean)", re.IGNORECASE
)

#: A bare string/interpolation-only literal argument -- not a sink finding.
_TEXT_LITERAL_RE = re.compile(r'^\s*["\'].*["\']\s*$')

#: Rails ERB explicit-unescaped-output tag: `<%== expr %>` (as distinct
#: from the ordinary escaping `<%= expr %>` tag).
_ERB_UNESCAPED_TAG_RE = re.compile(r"<%==\s*(.*?)\s*%>")

#: PHP superglobal names a request/user can influence.
_PHP_SUPERGLOBALS = (
    "$_GET",
    "$_POST",
    "$_REQUEST",
    "$_COOKIE",
    "$_SERVER",
    "$_FILES",
)

#: `echo $_GET['x'];` / `print $_POST['x'];` / short-echo `<?= $_GET['x'] ?>`
#: -- any of the three PHP output constructs, directly naming a superglobal
#: with no `htmlspecialchars(...)` wrap between the construct and the name.
_PHP_ECHO_SUPERGLOBAL_RE = re.compile(
    r"(?:\b(?:echo|print)\s+|<\?=\s*)"
    r"(?!\s*htmlspecialchars\s*\()"
    r"(\$_(?:GET|POST|REQUEST|COOKIE|SERVER|FILES)\b[^;?]*)"
)


# frob:doc docs/modules/webapp-websec-xss.md#public-api
@dataclass(frozen=True)
class WebsecXssFinding:
    """One WEBSEC107/WEBSEC108 finding: an unsanitized value reaching a
    Rails ERB explicit-unescaped tag or a PHP echo/print of a superglobal
    (CWE-79).

    frob:ticket T-5306
    """

    rule: str
    file: str
    line: int
    message: str


def _tracked_files(root: Path, *suffixes: str) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `suffixes`, root-relative
    POSIX paths, `()` on any git failure -- same tracked-file-scan shape
    `frob.webapp._websec_sinks._tracked_files` already uses.

    frob:ticket T-5306
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("websec_xss: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("websec_xss: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(suffixes)
    )


def _is_sanitized(text: str) -> bool:
    """True if `text` already names a recognized sanitizer call -- same
    "textual proxy, not resolved flow" posture `_websec_sinks._is_sanitized`
    documents.

    frob:ticket T-5306
    """
    return bool(_SANITIZER_NAME_RE.search(text))


def _is_literal(text: str) -> bool:
    """True if `text` is a bare quoted string literal with no
    interpolation -- a hardcoded HTML fragment, not a sink finding.

    frob:ticket T-5306
    """
    return bool(_TEXT_LITERAL_RE.match(text))


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable.

    frob:ticket T-5306
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _rails_erb_unescaped_findings(path: Path, root: Path) -> list[WebsecXssFinding]:
    """WEBSEC107 findings: `<%== expr %>` (Rails' EXPLICIT unescaped-output
    ERB tag) where `expr` is not a literal or a sanitizer call -- distinct
    from WEBSEC106's `.html_safe`/`raw(...)` regex pair, which never
    matches this tag shape.

    frob:ticket T-5306
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text or "<%==" not in text:
        return []
    findings: list[WebsecXssFinding] = []
    for match in _ERB_UNESCAPED_TAG_RE.finditer(text):
        expr = match.group(1).strip()
        if not expr or _is_literal(expr) or _is_sanitized(expr):
            continue
        line = text.count("\n", 0, match.start()) + 1
        findings.append(
            WebsecXssFinding(
                rule="WEBSEC107",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC107: {rel_path}:{line} <%== {expr} %> is Rails' "
                    f"EXPLICIT unescaped-output ERB tag (ASVS 5.0 "
                    f"V1.1.2/V1.2.1, CWE-79) -- use `<%= %>` (auto-escaped) "
                    f"or pass the value through a sanitizer first, or "
                    f'`frob:waive WEBSEC107 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _php_echo_superglobal_findings(path: Path, root: Path) -> list[WebsecXssFinding]:
    """WEBSEC108 findings: `echo`/`print`/short-echo of a raw superglobal
    with no `htmlspecialchars(...)` wrap.

    frob:ticket T-5306
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text or not any(sg in text for sg in _PHP_SUPERGLOBALS):
        return []
    findings: list[WebsecXssFinding] = []
    for match in _PHP_ECHO_SUPERGLOBAL_RE.finditer(text):
        expr = match.group(1).strip()
        if not expr:
            continue
        line = text.count("\n", 0, match.start()) + 1
        findings.append(
            WebsecXssFinding(
                rule="WEBSEC108",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC108: {rel_path}:{line} echo/print of {expr!r} "
                    f"outputs a raw superglobal with no htmlspecialchars(...) "
                    f"wrap (ASVS 5.0 V1.1.2/V1.2.1, CWE-79) -- wrap the "
                    f"value in htmlspecialchars(...) before output, or "
                    f'`frob:waive WEBSEC108 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _scan(root: Path) -> tuple[WebsecXssFinding, ...]:
    """The actual file walk, with no framework-gating -- shared by
    `websec_xss_findings` (which detects for itself, the module's own
    standalone entry point) and `websec_findings` (the discovery-hook
    entry point, which trusts an already-detected `frameworks` set so it
    never re-runs `detect_frameworks` a second time per module).

    frob:ticket T-5306
    """
    findings: list[WebsecXssFinding] = []
    for rel in _tracked_files(root, ".erb"):
        findings.extend(_rails_erb_unescaped_findings(root / rel, root))
    for rel in _tracked_files(root, ".php"):
        findings.extend(_php_echo_superglobal_findings(root / rel, root))
    return tuple(findings)


# frob:doc docs/modules/webapp-websec-xss.md#public-api
# frob:ticket T-5306
def websec_xss_findings(root: Path) -> tuple[WebsecXssFinding, ...]:
    """WEBSEC107-108: every unsanitized Rails ERB explicit-unescaped-tag
    or PHP raw-superglobal-echo sink under `root`.

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all (T-5302's own contract), same
    posture `frob.webapp._websec_sinks.websec_sink_findings` follows.
    Standalone entry point: detects frameworks for itself, so a caller
    that has not already called `detect_frameworks` (e.g. a direct unit
    test) can use this without doing that first.

    frob:ticket T-5306
    """
    root = Path(root)
    if not detect_frameworks(root):
        _log.debug("websec_xss: no framework detected at %s, skipping scan", root)
        return ()
    findings = _scan(root)
    _log.info("websec_xss: %d finding(s) under %s", len(findings), root)
    return findings


# frob:doc docs/modules/webapp-websec-xss.md#public-api
# frob:ticket T-5306
def websec_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """Discovery-hook entry point `frob.gates._taint_gate.taint_gate`
    calls on every `frob.webapp._websec_*` module exposing this exact
    module-level name/signature (T-5311's discovery convention -- the
    taint gate detects frameworks ONCE and hands the result to every
    WEBSEC family module, instead of each module re-running
    `detect_frameworks` for itself).

    Returns `()` immediately for an empty `frameworks` (no web framework
    detected at all, T-5302's contract) without touching the filesystem
    beyond that check. WARN-tier, same T-0688/T-0973 promotion posture
    `websec_xss_findings` documents.

    frob:ticket T-5306
    """
    if not frameworks:
        _log.debug("websec_xss: no framework detected under %s, skipping scan", root)
        return ()
    root = Path(root)
    findings = _scan(root)
    _log.info("websec_xss: %d finding(s) under %s", len(findings), root)
    return tuple(
        Violation(
            rule=finding.rule,
            severity=Severity.WARN,
            file=finding.file,
            line=finding.line,
            message=finding.message,
        )
        for finding in findings
    )
