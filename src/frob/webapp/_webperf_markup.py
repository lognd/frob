"""WEBPERF101-108: Core Web Vitals causes in markup (docs/modules/
webapp-webperf-markup.md, T-5371, the T-5140 web-app epic's
WEBPERF-markup leaf, blocked_by=['T-5364']).

# frob:ticket T-5371

Seven markup-level causes of Core Web Vitals regressions (CLS/LCP), each
a static, shallow scan over `.html`/`.jsx` route files and CSS/config
text -- same posture every WEBSEC/COMPLY/A11Y/SEO/WEBPERF family in this
epic takes (owner directive, T-5302: a false negative here is cheaper
than a false positive a repo owner cannot reproduce):

- WEBPERF101: an `<img>` missing `width` or `height` (the browser cannot
  reserve layout space before the image loads -- the canonical CLS
  cause).
- WEBPERF102: an `<img>`/`<iframe>` with no `loading="lazy"` and no
  explicit `loading="eager"`/`fetchpriority="high"` escape hatch (an
  offscreen image forcing eager network/paint work).
- WEBPERF103: an `<img>` missing `srcset` (no responsive source set, so
  every viewport downloads the same, possibly oversized, asset).
- WEBPERF104: an `@font-face` CSS rule with no `font-display` (a custom
  font blocks text rendering with no documented fallback behavior --
  FOIT instead of a declared FOUT/swap strategy).
- WEBPERF105: a `<script src="...">` inside `<head>`/`<Head>` with
  neither `defer` nor `async` (a synchronous, render-blocking script).
- WEBPERF106: a webpack/vite config file with no bundle-size-budget
  assertion (`performance.max*`/`chunkSizeWarningLimit`) -- nothing
  catches an unbounded bundle-size regression at build time.
- WEBPERF108: a document with no `<meta name="viewport" ...>` (mobile
  layout falls back to a desktop-width viewport, a common CLS/zoom
  cause on narrow screens).

WEBPERF107 (source maps shipped in production) is DELIBERATELY not
implemented here: the ticket body's own scope note says "cross-refs
T-5143-3, not duplicated" -- T-5143-3 already owns detecting a
production build serving `.map` files, and this module does not
re-implement that check under a second rule id. WEBPERF107 stays
reserved in `_KNOWN_GATE_RULES` (`frob.gates._waive`) for that other
leaf; nothing here ever emits it.

SUBSTRATE REUSE (owner directive, brief 2026-09-24: "reuse the page
walker, never re-implement"): parsing goes through `frob.lang.raw_tree`
(T-5300's single parse dispatch) via `frob.webapp._seo_substrate`'s own
node-shape helpers (`_HTML_ELEMENT_TYPES`/`_JSX_ELEMENT_TYPES`,
`_html_tag_name`/`_html_attrs`, `_jsx_tag_name`/`_jsx_attrs`, `_find_head`
+ the HTML/JSX head-children iterators) -- this module never stands up
its own tree-sitter `Parser` and never re-derives an element's tag name
or attribute map from raw node text. `_seo_substrate`'s SCOPE note (only
`<head>` contents) applies to head-only rules here (WEBPERF105/108);
WEBPERF101-103 walk the WHOLE document body (every `<img>`/`<iframe>`
element, not just ones under `<head>`), via a new depth-first walker
(`_iter_elements`) built from the SAME element-type/tag-name/attrs
primitives -- a generalization of `_seo_substrate._find_head`'s search,
not a duplicate implementation of tree-sitter node walking.

GATE DISCOVERY (T-draft-553232aa, not yet landed): `frob.gates.
_taint_gate._discover_websec_hook_modules` only scans `frob.webapp.
_websec_*` submodules (`_WEBSEC_MODULE_PREFIX = "_websec_"`) as of this
ticket. This module follows the SAME `websec_findings(root, frameworks)
-> tuple[Violation, ...]` hook shape every WEBSEC/SEO/WEBPERF sibling
uses so it needs zero further wiring once T-draft-553232aa widens
discovery to the `_webperf_` prefix -- until then, `websec_findings` is
reachable directly (this module's own test suite calls it), just not
yet folded into `frob check`'s live gate scan. See docs/modules/
webapp-webperf-markup.md#gate-discovery for the end-to-end control this
gap blocks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from frob.findings import Severity, Violation
from frob.gitio import run_argv
from frob.lang import LangError, raw_tree
from frob.logging import get_logger
from frob.webapp._detect import FrameworkKind
from frob.webapp._seo_substrate import (
    _HTML_ELEMENT_TYPES,
    _JSX_ELEMENT_TYPES,
    _find_head,
    _html_attrs,
    _html_tag_name,
    _iter_html_head_children,
    _iter_jsx_head_children,
    _jsx_attrs,
    _jsx_tag_name,
)

_log = get_logger(__name__)

__all__ = [
    "WebperfMarkupFinding",
    "webperf_markup_findings",
    "websec_findings",
]

_PAGE_EXTENSIONS = (".html", ".jsx")
_CSS_EXTENSIONS = (".css", ".scss")
_BUNDLER_CONFIG_NAMES_RE = re.compile(
    r"^(webpack\.config\.(js|ts|mjs|cjs)|vite\.config\.(js|ts|mjs|cjs))$"
)

_FONT_FACE_RE = re.compile(r"@font-face\s*\{([^}]*)\}", re.DOTALL)
_FONT_DISPLAY_RE = re.compile(r"font-display\s*:", re.IGNORECASE)
_BUNDLE_BUDGET_RE = re.compile(r"maxAssetSize|maxEntrypointSize|chunkSizeWarningLimit")


# frob:doc docs/modules/webapp-webperf-markup.md#public-api
# frob:tests tests/unit/test_webapp_webperf_markup.py::test_webperf_markup_findings_fixture[webperf101_positive-WEBPERF101-True] kind="unit"  # noqa: E501
@dataclass(frozen=True)
class WebperfMarkupFinding:
    """One WEBPERF101-108 finding: a rule id, the file and line the
    evidence came from, and a human message.

    frob:ticket T-5371
    """

    rule: str
    file: str
    line: int
    message: str


def _tracked_files(root: Path, extensions: tuple[str, ...]) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `extensions`, root-relative
    POSIX paths, `()` on any git failure -- same tiny own tracked-file-scan
    shape `_websec_headers_rules._tracked_files` already established
    (an intentional own copy, not a cross-module private import).

    frob:ticket T-5371
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("webperf_markup: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("webperf_markup: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(extensions)
    )


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable.

    frob:ticket T-5371
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _line_of_offset(text: str, offset: int) -> int:
    """1-based line number of byte/char `offset` within `text` -- for
    findings from a plain regex scan (CSS/config text), which has no
    tree-sitter node to read a `.start_point` from.

    frob:ticket T-5371
    """
    return text.count("\n", 0, offset) + 1


def _iter_elements(node, element_types: frozenset[str]):  # noqa: ANN001, ANN201
    """Depth-first walk of every node in `element_types` under `node` --
    the whole-document generalization of `frob.webapp._seo_substrate.
    _find_head`'s single-target search (module docstring): same stack-
    based walk, but yields every match instead of returning the first.

    frob:ticket T-5371
    """
    stack = [node]
    while stack:
        current = stack.pop()
        if current.type in element_types:
            yield current
        stack.extend(reversed(current.children))


def _tag_and_attrs(node, is_html: bool) -> tuple[str, dict[str, str]]:  # noqa: ANN001
    """`(tag_name, attrs)` for `node`, dispatching to the HTML or JSX
    extractor `_seo_substrate` already owns -- the one place this module
    picks which vocabulary applies, so every rule below stays language-
    agnostic past this call.

    frob:ticket T-5371
    """
    if is_html:
        return _html_tag_name(node).lower(), _html_attrs(node)
    return _jsx_tag_name(node).lower(), _jsx_attrs(node)


def _parse_page(path: Path):  # noqa: ANN201
    """Parse `path` via `frob.lang.raw_tree` (T-5300's one dispatch),
    returning `(root_node, is_html)` or `None` for an unsupported/
    unparseable file -- the one parse call every rule below shares
    instead of re-parsing per rule.

    frob:ticket T-5371
    """
    parsed = raw_tree(path)
    if parsed.is_err:
        if parsed.danger_err is not LangError.UnsupportedLanguage:
            _log.debug(
                "webperf_markup: raw_tree failed for %s: %s", path, parsed.danger_err
            )
        return None
    tree, _source, language_label = parsed.danger_ok
    if language_label not in ("html", "javascript"):
        return None
    return tree.root_node, language_label == "html"


def _webperf101_findings(root: Path, rel: str, page_root, is_html: bool):  # noqa: ANN001, ANN201
    """WEBPERF101: an `<img>` missing `width` or `height` (CLS).

    frob:ticket T-5371
    """
    element_types = _HTML_ELEMENT_TYPES if is_html else _JSX_ELEMENT_TYPES
    for node in _iter_elements(page_root, element_types):
        tag, attrs = _tag_and_attrs(node, is_html)
        if tag != "img":
            continue
        if "width" not in attrs or "height" not in attrs:
            yield WebperfMarkupFinding(
                rule="WEBPERF101",
                file=rel,
                line=node.start_point[0] + 1,
                message="WEBPERF101: <img> is missing width/height -- the "
                "browser cannot reserve layout space before it loads, a "
                "canonical CLS cause",
            )


def _webperf102_findings(root: Path, rel: str, page_root, is_html: bool):  # noqa: ANN001, ANN201
    """WEBPERF102: an `<img>`/`<iframe>` with no `loading="lazy"` and no
    explicit eager/high-priority escape hatch.

    frob:ticket T-5371
    """
    element_types = _HTML_ELEMENT_TYPES if is_html else _JSX_ELEMENT_TYPES
    for node in _iter_elements(page_root, element_types):
        tag, attrs = _tag_and_attrs(node, is_html)
        if tag not in ("img", "iframe"):
            continue
        loading = attrs.get("loading", "").lower()
        fetchpriority = attrs.get("fetchpriority", "").lower()
        if loading == "lazy" or loading == "eager" or fetchpriority == "high":
            continue
        yield WebperfMarkupFinding(
            rule="WEBPERF102",
            file=rel,
            line=node.start_point[0] + 1,
            message=f'WEBPERF102: <{tag}> has no loading="lazy" (and no '
            'loading="eager"/fetchpriority="high" escape hatch) -- an '
            "offscreen element forcing eager network/paint work",
        )


def _webperf103_findings(root: Path, rel: str, page_root, is_html: bool):  # noqa: ANN001, ANN201
    """WEBPERF103: an `<img>` missing `srcset`.

    frob:ticket T-5371
    """
    element_types = _HTML_ELEMENT_TYPES if is_html else _JSX_ELEMENT_TYPES
    for node in _iter_elements(page_root, element_types):
        tag, attrs = _tag_and_attrs(node, is_html)
        if tag != "img":
            continue
        if "srcset" not in attrs:
            yield WebperfMarkupFinding(
                rule="WEBPERF103",
                file=rel,
                line=node.start_point[0] + 1,
                message="WEBPERF103: <img> is missing srcset -- no "
                "responsive source set, every viewport downloads the "
                "same asset",
            )


def _webperf105_findings(root: Path, rel: str, page_root, is_html: bool):  # noqa: ANN001, ANN201
    """WEBPERF105: a `<script src>` inside `<head>`/`<Head>` with neither
    `defer` nor `async`.

    frob:ticket T-5371
    """
    if is_html:
        head = _find_head(page_root, _HTML_ELEMENT_TYPES, frozenset({"head"}))
        children = _iter_html_head_children(head) if head is not None else ()
    else:
        head = _find_head(page_root, _JSX_ELEMENT_TYPES, frozenset({"head", "Head"}))
        children = _iter_jsx_head_children(head) if head is not None else ()
    for node in children:
        tag, attrs = _tag_and_attrs(node, is_html)
        if tag != "script" or "src" not in attrs:
            continue
        if "defer" in attrs or "async" in attrs:
            continue
        yield WebperfMarkupFinding(
            rule="WEBPERF105",
            file=rel,
            line=node.start_point[0] + 1,
            message="WEBPERF105: <script src> in <head> has neither defer "
            "nor async -- a synchronous, render-blocking script",
        )


def _webperf108_findings(root: Path, rel: str, page_root, is_html: bool):  # noqa: ANN001, ANN201
    """WEBPERF108: no `<meta name="viewport">` anywhere in `<head>`.

    frob:ticket T-5371
    """
    if is_html:
        head = _find_head(page_root, _HTML_ELEMENT_TYPES, frozenset({"head"}))
        children = _iter_html_head_children(head) if head is not None else ()
    else:
        head = _find_head(page_root, _JSX_ELEMENT_TYPES, frozenset({"head", "Head"}))
        children = _iter_jsx_head_children(head) if head is not None else ()
    if head is None:
        return
    for node in children:
        tag, attrs = _tag_and_attrs(node, is_html)
        if tag == "meta" and attrs.get("name", "").lower() == "viewport":
            return
    yield WebperfMarkupFinding(
        rule="WEBPERF108",
        file=rel,
        line=head.start_point[0] + 1,
        message='WEBPERF108: no <meta name="viewport"> in <head> -- '
        "mobile layout falls back to a desktop-width viewport, a "
        "common CLS/zoom cause",
    )


_PAGE_RULE_WALKERS = (
    _webperf101_findings,
    _webperf102_findings,
    _webperf103_findings,
    _webperf105_findings,
    _webperf108_findings,
)


def _page_findings(root: Path, rel: str) -> tuple[WebperfMarkupFinding, ...]:
    """Every WEBPERF101/102/103/105/108 finding for one `.html`/`.jsx`
    file -- one `_parse_page` call shared by every walker in
    `_PAGE_RULE_WALKERS`.

    frob:ticket T-5371
    """
    parsed = _parse_page(root / rel)
    if parsed is None:
        return ()
    page_root, is_html = parsed
    findings: list[WebperfMarkupFinding] = []
    for walker in _PAGE_RULE_WALKERS:
        findings.extend(walker(root, rel, page_root, is_html))
    return tuple(findings)


def _webperf104_findings(root: Path, rel: str) -> tuple[WebperfMarkupFinding, ...]:
    """WEBPERF104: an `@font-face` CSS rule with no `font-display`.

    A plain regex scan (CSS grammar is out of `_seo_substrate`'s scope,
    module docstring) -- same posture `_websec_headers_rules`'s own
    text-presence checks already take for a target this repo's tree-sitter
    substrate does not cover.

    frob:ticket T-5371
    """
    text = _read_text(root / rel)
    findings: list[WebperfMarkupFinding] = []
    for match in _FONT_FACE_RE.finditer(text):
        if _FONT_DISPLAY_RE.search(match.group(1)):
            continue
        findings.append(
            WebperfMarkupFinding(
                rule="WEBPERF104",
                file=rel,
                line=_line_of_offset(text, match.start()),
                message="WEBPERF104: @font-face has no font-display -- a "
                "custom font blocks text rendering with no documented "
                "fallback strategy (FOIT instead of swap/fallback)",
            )
        )
    return tuple(findings)


def _webperf106_findings(root: Path, rel: str) -> tuple[WebperfMarkupFinding, ...]:
    """WEBPERF106: a webpack/vite config file with no bundle-size-budget
    assertion.

    frob:ticket T-5371
    """
    if not _BUNDLER_CONFIG_NAMES_RE.match(Path(rel).name):
        return ()
    text = _read_text(root / rel)
    if _BUNDLE_BUDGET_RE.search(text):
        return ()
    return (
        WebperfMarkupFinding(
            rule="WEBPERF106",
            file=rel,
            line=1,
            message="WEBPERF106: no bundle-size-budget assertion "
            "(performance.max*/chunkSizeWarningLimit) -- nothing catches "
            "an unbounded bundle-size regression at build time",
        ),
    )


# frob:doc docs/modules/webapp-webperf-markup.md#public-api
# frob:tests tests/unit/test_webapp_webperf_markup.py::test_webperf_markup_findings_fixture[webperf101_positive-WEBPERF101-True] kind="unit"  # noqa: E501
def webperf_markup_findings(root: Path) -> tuple[WebperfMarkupFinding, ...]:
    """Every WEBPERF101/102/103/104/105/106/108 finding under `root`
    (WEBPERF107 deliberately excluded -- module docstring). Framework
    gating is `websec_findings`'s job (T-5302 convention: an empty
    `detect_frameworks(root)` short-circuits the whole family before any
    file scan runs); this function itself does its own tracked-file walk
    unconditionally, matching `_websec_headers_rules_findings`'s own
    direct-call contract for a caller that already knows it wants a scan.

    frob:ticket T-5371
    """
    findings: list[WebperfMarkupFinding] = []
    for rel in _tracked_files(root, _PAGE_EXTENSIONS):
        findings.extend(_page_findings(root, rel))
    for rel in _tracked_files(root, _CSS_EXTENSIONS):
        findings.extend(_webperf104_findings(root, rel))
    for rel in _tracked_files(root, (".js", ".ts", ".mjs", ".cjs")):
        findings.extend(_webperf106_findings(root, rel))
    _log.info("webperf_markup: %d finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/webapp-webperf-markup.md#public-api
# frob:ticket T-5371
def websec_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """T-5311's `taint_gate` module-discovery hook shape (module
    docstring: not yet DISCOVERED until T-draft-553232aa widens
    `_WEBSEC_MODULE_PREFIX` to also match `_webperf_`, but already
    callable directly). `frameworks` is the caller's own already-computed
    `detect_frameworks(root)` result; an empty set short-circuits to `()`
    exactly like every WEBSEC sibling's own hook.

    frob:ticket T-5371
    """
    if not frameworks:
        _log.debug(
            "webperf_markup: no framework detected at %s, skipping scan (hook)",
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
        for finding in webperf_markup_findings(root)
    )
