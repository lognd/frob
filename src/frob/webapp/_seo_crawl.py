"""SEO121-126: crawl/discovery config
(docs/modules/webapp-seo-crawl.md, T-5362), the T-5140 web-app epic's
crawl/discovery-config leaf: `robots.txt` malformed lines and its
Google-Extended AI-training-opt-out decision record, `sitemap.xml`
schema validation against the sitemaps.org structure, `llms.txt`
advisory-only presence, `hreflang` alternate-link config, and canonical
links carrying a query string.

`robots.txt` is line-oriented (the ticket body's own framing -- no
`frob.lang` grammar needed, a plain per-line regex scan). `sitemap.xml`
is validated via the stdlib `xml.etree.ElementTree` (the ticket body's
own framing again -- no third-party XML dependency). `hreflang`/
canonical-query-string checks reuse
`frob.webapp._seo_substrate.extract_page_metadata` (T-5364) for their
route walk, the same substrate `_seo_tags` (T-5374) and `_seo_spam`
(T-5365) already build on -- `hreflang` itself is read with a small
local text-regex over the raw file (`_seo_substrate.LinkTag` only
carries `rel`/`href`, no `hreflang` attribute, so this leaf reads that
one extra attribute itself rather than widening the shared substrate
model for a single consumer).

DISCOVERY: same posture T-5374's `_seo_tags`/T-5365's `_seo_spam`
module docstrings document in full -- `docs/modules/webapp-seo.md`
defines no leaf-hook convention, and `frob.gates._taint_gate`'s pkgutil
discovery only scans `frob.webapp._websec_*`-prefixed modules, so this
module's `websec_findings` hook is NOT currently auto-discovered by any
live gate either. T-draft-553232aa (filed by T-5374, and by the time
this leaf landed, narrowed by the coordinator's own plan to "widen
`_taint_gate`'s existing discovered-prefix tuple -- already
`("_websec_", "_comply_")` since T-5372 -- to also include `_seo_`/
`_webperf_`, plus one end-to-end control per family") is the actual
fix; once it lands, this module's hook is discovered for free.

SIX RULE IDS used of the reserved `SEO121`-`SEO127` seven-id block;
`SEO127` is left unimplemented -- see the T-5362 Done report for the
follow-up ticket id:

- SEO121: a `robots.txt` line that is neither blank, a `#` comment, nor
  a `Directive: value` shape -- malformed.
- SEO122: a `robots.txt` present with no explicit
  `User-agent: Google-Extended` stanza -- the AI-training-opt-out
  DECISION RECORD the ticket body names (an explicit Allow OR Disallow
  for Google-Extended, either choice is fine; having made NO choice at
  all is the finding).
- SEO123: a `sitemap.xml` that is not valid XML, whose root tag is not
  `urlset` (namespace-stripped), or whose `<url>` entries are missing a
  `<loc>` child -- sitemaps.org schema validation.
- SEO124: no tracked `llms.txt` at the repo root -- advisory-only
  presence (the ticket body's own framing: this is a SHOULD, not a
  MUST, hence WARN-tier like every other first-turn-on rule here, never
  promoted further by this leaf).
- SEO125: a page missing an `hreflang="x-default"` alternate link when
  it carries two or more `<link rel="alternate" hreflang="...">` tags.
- SEO126: a `<link rel="canonical">` href carrying a query string (`?`)
  -- the canonical target should be the clean, query-string-free URL.

Each fires WARN-tier at first turn-on, the same T-0688/T-0973 promotion
posture every other brand-new WEBSEC/SEO family in this repo follows.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from frob.findings import Severity, Violation
from frob.gitio import run_argv
from frob.logging import get_logger
from frob.webapp._detect import FrameworkKind, detect_frameworks
from frob.webapp._seo_substrate import PageMetadata, extract_page_metadata

_log = get_logger(__name__)

__all__ = [
    "WebsecSeoCrawlFinding",
    "seo_crawl_findings",
    "websec_findings",
]

_PAGE_EXTENSIONS = (".html", ".jsx")

_ROBOTS_LINE_RE = re.compile(r"^[A-Za-z][A-Za-z-]*\s*:\s*.*$")
_GOOGLE_EXTENDED_RE = re.compile(r"""user-agent\s*:\s*google-extended""", re.IGNORECASE)

_HREFLANG_LINK_RE = re.compile(
    r"""<link\b[^>]*\brel\s*=\s*["']alternate["'][^>]*\bhreflang\s*=\s*["']([^"']+)["']"""
    r"""|<link\b[^>]*\bhreflang\s*=\s*["']([^"']+)["'][^>]*\brel\s*=\s*["']alternate["']""",
    re.IGNORECASE,
)


# frob:doc docs/modules/webapp-seo-crawl.md#public-api
# frob:ticket T-5362
@dataclass(frozen=True)
class WebsecSeoCrawlFinding:
    """One SEO121-126 finding: a `robots.txt`/`sitemap.xml`/`llms.txt`
    config gap, or a per-page `hreflang`/canonical-query-string issue.

    frob:ticket T-5362
    """

    rule: str
    file: str
    line: int
    message: str


def _tracked_files(root: Path, *suffixes: str) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `suffixes`, root-relative
    POSIX paths, `()` on any git failure -- mirrors
    `_websec_headers_log._tracked_files`'s own tracked-file-scan shape.

    frob:ticket T-5362
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("seo_crawl: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("seo_crawl: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(suffixes)
    )


def _tracked_named_files(root: Path, name: str) -> tuple[str, ...]:
    """Every tracked file literally named `name` anywhere under `root`.

    frob:ticket T-5362
    """
    return tuple(
        rel for rel in _tracked_files(root, name) if rel.rsplit("/", 1)[-1] == name
    )


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable.

    frob:ticket T-5362
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _robots_txt_findings(root: Path) -> list[WebsecSeoCrawlFinding]:
    """SEO121/SEO122: a malformed `robots.txt` line, or no explicit
    `Google-Extended` decision record.

    frob:ticket T-5362
    """
    findings: list[WebsecSeoCrawlFinding] = []
    for rel in _tracked_named_files(root, "robots.txt"):
        text = _read_text(root / rel)
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not _ROBOTS_LINE_RE.match(stripped):
                findings.append(
                    WebsecSeoCrawlFinding(
                        rule="SEO121",
                        file=rel,
                        line=lineno,
                        message=(
                            f"SEO121: {rel}:{lineno} {stripped!r} is not "
                            f"a Directive: value line -- malformed "
                            f"robots.txt. Fix the syntax, or `frob:waive "
                            f'SEO121 reason="..."` with a real '
                            f"justification"
                        ),
                    )
                )
        if not _GOOGLE_EXTENDED_RE.search(text):
            findings.append(
                WebsecSeoCrawlFinding(
                    rule="SEO122",
                    file=rel,
                    line=1,
                    message=(
                        f"SEO122: {rel} has no explicit "
                        f"User-agent: Google-Extended stanza -- no "
                        f"AI-training-opt-out decision has been "
                        f"recorded (Allow or Disallow are both fine; "
                        f"making no choice is the finding). Add one, "
                        f'or `frob:waive SEO122 reason="..."` with a '
                        f"real justification"
                    ),
                )
            )
    return findings


def _sitemap_not_xml_finding(rel: str, exc: ET.ParseError) -> WebsecSeoCrawlFinding:
    """SEO123: `sitemap.xml` is not parseable XML at all.

    frob:ticket T-5362
    """
    return WebsecSeoCrawlFinding(
        rule="SEO123",
        file=rel,
        line=1,
        message=(
            f"SEO123: {rel} is not valid XML ({exc}) -- search engines "
            f"ignore an unparseable sitemap. Fix the XML, or `frob:waive "
            f'SEO123 reason="..."` with a real justification'
        ),
    )


def _sitemap_wrong_root_finding(rel: str, root_tag: str) -> WebsecSeoCrawlFinding:
    """SEO123: `sitemap.xml`'s root element is not `urlset`.

    frob:ticket T-5362
    """
    return WebsecSeoCrawlFinding(
        rule="SEO123",
        file=rel,
        line=1,
        message=(
            f'SEO123: {rel} root element is {root_tag!r}, not "urlset" '
            f"-- not a sitemaps.org-shaped sitemap. Fix the schema, or "
            f'`frob:waive SEO123 reason="..."` with a real justification'
        ),
    )


def _sitemap_missing_loc_findings(
    rel: str, tree: ET.Element
) -> list[WebsecSeoCrawlFinding]:
    """SEO123: every `<url>` entry in `tree` with no `<loc>` child.

    frob:ticket T-5362
    """
    findings: list[WebsecSeoCrawlFinding] = []
    for url_elem in tree:
        url_tag = url_elem.tag.rsplit("}", 1)[-1]
        if url_tag != "url":
            continue
        has_loc = any(
            child.tag.rsplit("}", 1)[-1] == "loc" and (child.text or "").strip()
            for child in url_elem
        )
        if has_loc:
            continue
        findings.append(
            WebsecSeoCrawlFinding(
                rule="SEO123",
                file=rel,
                line=1,
                message=(
                    f"SEO123: {rel} a <url> entry has no <loc> child -- "
                    f"sitemaps.org requires it. Add it, or `frob:waive "
                    f'SEO123 reason="..."` with a real justification'
                ),
            )
        )
    return findings


def _sitemap_xml_findings(root: Path) -> list[WebsecSeoCrawlFinding]:
    """SEO123: `sitemap.xml` schema validation against sitemaps.org.

    frob:ticket T-5362
    """
    findings: list[WebsecSeoCrawlFinding] = []
    for rel in _tracked_named_files(root, "sitemap.xml"):
        text = _read_text(root / rel)
        try:
            tree = ET.fromstring(text)
        except ET.ParseError as exc:
            findings.append(_sitemap_not_xml_finding(rel, exc))
            continue
        root_tag = tree.tag.rsplit("}", 1)[-1]
        if root_tag != "urlset":
            findings.append(_sitemap_wrong_root_finding(rel, root_tag))
            continue
        findings.extend(_sitemap_missing_loc_findings(rel, tree))
    return findings


def _llms_txt_findings(root: Path) -> list[WebsecSeoCrawlFinding]:
    """SEO124: no tracked `llms.txt` at all -- advisory-only presence.

    frob:ticket T-5362
    """
    if _tracked_named_files(root, "llms.txt"):
        return []
    return [
        WebsecSeoCrawlFinding(
            rule="SEO124",
            file=".",
            line=1,
            message=(
                "SEO124: no llms.txt found -- advisory-only: LLM crawlers "
                "have no declared usage policy for this site. Add one, "
                'or `frob:waive SEO124 reason="..."` with a real '
                "justification"
            ),
        )
    ]


def _tracked_page_files(root: Path) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `_PAGE_EXTENSIONS`.

    frob:ticket T-5362
    """
    return _tracked_files(root, *_PAGE_EXTENSIONS)


def _extract_pages(root: Path) -> tuple[PageMetadata, ...]:
    """Every tracked `.html`/`.jsx` route file under `root`, turned into
    a `PageMetadata` via `extract_page_metadata` (T-5364's substrate,
    reused unchanged) -- a file with no `<head>`/`<Head>` element is
    silently skipped.

    frob:ticket T-5362
    """
    pages: list[PageMetadata] = []
    for rel in _tracked_page_files(root):
        result = extract_page_metadata(root / rel, route=rel)
        if result.is_err:
            _log.debug("seo_crawl: skipping %s: %s", rel, result.danger_err)
            continue
        pages.append(result.danger_ok)
    return tuple(pages)


def _hreflang_findings(root: Path) -> list[WebsecSeoCrawlFinding]:
    """SEO125: two or more `hreflang` alternate links with no
    `x-default`.

    frob:ticket T-5362
    """
    findings: list[WebsecSeoCrawlFinding] = []
    for rel in _tracked_page_files(root):
        text = _read_text(root / rel)
        tags = [(m.group(1) or m.group(2)) for m in _HREFLANG_LINK_RE.finditer(text)]
        if len(tags) < 2:
            continue
        if any(tag.lower() == "x-default" for tag in tags):
            continue
        findings.append(
            WebsecSeoCrawlFinding(
                rule="SEO125",
                file=rel,
                line=1,
                message=(
                    f"SEO125: {rel} has {len(tags)} hreflang alternate "
                    f'links but no hreflang="x-default" -- visitors '
                    f"whose locale matches none of the declared "
                    f"alternates get no fallback. Add an x-default "
                    f'link, or `frob:waive SEO125 reason="..."` with a '
                    f"real justification"
                ),
            )
        )
    return findings


def _canonical_query_string_findings(
    pages: tuple[PageMetadata, ...],
) -> list[WebsecSeoCrawlFinding]:
    """SEO126: a canonical link carrying a query string.

    frob:ticket T-5362
    """
    findings: list[WebsecSeoCrawlFinding] = []
    for page in pages:
        for link in page.links:
            if link.rel != "canonical" or not link.href or "?" not in link.href:
                continue
            findings.append(
                WebsecSeoCrawlFinding(
                    rule="SEO126",
                    file=page.source_path,
                    line=1,
                    message=(
                        f"SEO126: {page.source_path} canonical link "
                        f"{link.href!r} carries a query string -- the "
                        f"canonical target should be the clean, "
                        f"query-string-free URL so every query-string "
                        f"variant consolidates onto one indexed page. "
                        f"Strip the query string, or `frob:waive SEO126 "
                        f'reason="..."` with a real justification'
                    ),
                )
            )
    return findings


# frob:doc docs/modules/webapp-seo-crawl.md#public-api
# frob:ticket T-5362
def seo_crawl_findings(root: Path) -> tuple[WebsecSeoCrawlFinding, ...]:
    """SEO121-126: every crawl/discovery-config finding under `root`.

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all -- the same contract every
    WEBSEC/COMPLY/A11Y/SEO/WEBPERF family in this repo uses (T-5302).
    """
    root = Path(root)
    if not detect_frameworks(root):
        _log.debug("seo_crawl: no framework detected at %s, skipping scan", root)
        return ()

    pages = _extract_pages(root)
    findings: list[WebsecSeoCrawlFinding] = []
    findings.extend(_robots_txt_findings(root))
    findings.extend(_sitemap_xml_findings(root))
    findings.extend(_llms_txt_findings(root))
    findings.extend(_hreflang_findings(root))
    findings.extend(_canonical_query_string_findings(pages))

    _log.info("seo_crawl: %d finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/webapp-seo-crawl.md#public-api
# frob:ticket T-5362
def websec_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """Hook named to match `frob.gates._taint_gate`'s discovery SHAPE
    (`websec_findings(root, frameworks) -> tuple[Violation, ...]`), the
    same convention T-5374's `_seo_tags`/T-5365's `_seo_spam` already
    follow -- see the module docstring's DISCOVERY section for why no
    live gate currently calls it (`_seo_crawl` does not match
    `_taint_gate`'s discovered-prefix tuple; T-draft-553232aa is the
    actual fix). `frameworks` is a caller's own already-computed
    `detect_frameworks(root)` result; an empty set short-circuits to
    `()`, same contract as `seo_crawl_findings`.
    """
    if not frameworks:
        _log.debug("seo_crawl: no framework detected at %s, skipping scan (hook)", root)
        return ()
    return tuple(
        Violation(
            rule=finding.rule,
            severity=Severity.WARN,
            file=finding.file,
            line=finding.line,
            message=finding.message,
        )
        for finding in seo_crawl_findings(root)
    )
