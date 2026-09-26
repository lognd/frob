"""SEO101-112: per-page tags
(docs/modules/webapp-seo-tags.md, T-5374), the T-5140 web-app epic's
per-page-tags leaf: unique title/meta-description per route, the six
`og:*`/canonical/favicon tags, and JSON-LD LocalBusiness required
properties.

Reuses `frob.webapp._seo_substrate.extract_page_metadata`/
`build_duplicate_title_index` (T-5364) for every fact this module needs
-- it never re-parses a `<head>` block itself, and never stands up its
own tree-sitter walk (the substrate module's own module docstring: ONE
walk shared by every SEO/WEBPERF rule that needs title/meta/link/
JSON-LD facts).

DISCOVERY CONVENTION -- read before wiring a caller to this module:
`docs/modules/webapp-seo.md` (T-5364's substrate doc) defines NO hook
convention for a leaf like this one to opt into a gate -- unlike
A11Y/WEBSEC, no SEO-family discovery gate exists yet on `dev` at the
time this leaf landed. This module's public hook is named
`websec_findings(root, frameworks) -> tuple[Violation, ...]` to match
`frob.gates._taint_gate`'s established discovery SHAPE exactly (same
signature, same `Violation`/`Severity` wrapping) per this ticket's own
coordinator direction, but `_taint_gate._discover_websec_hook_modules`
only scans `frob.webapp` submodules whose NAME starts with `_websec_`
(`_WEBSEC_MODULE_PREFIX`) -- `_seo_tags` does not match that prefix, so
this hook is NOT currently auto-discovered by any live gate. Calling
`websec_findings`/`seo_tag_findings` directly (as this module's own
test suite does) is the only way to run this leaf's checks today. Real
gate wiring for this family -- a new discovery gate mirroring
`frob.gates._a11y_gate`'s own "first leaf of the family owns the one
discovery edit" pkgutil pattern, or widening the existing WEBSEC
discovery mechanism's matched-module-prefix set to also cover this
family -- is the correct fix, filed as follow-up scope rather than
widened into this ticket (a shared gate-registration file touches
every concurrent WEBSEC/COMPLY/A11Y/SEO/WEBPERF leaf; see the T-5374
Done report for the follow-up ticket id).

TWELVE RULE IDS, filling the entire reserved `SEO101`-`SEO112` block:

- SEO101: a `<title>` shared by two or more routes in the same
  directory (`build_duplicate_title_index`, reused unchanged) -- not a
  missing title, a DUPLICATE one.
- SEO102: a meta description (`<meta name="description">`) shared by
  two or more routes in the same directory (a local duplicate-index
  helper over `PageMetadata.meta`, the same shape
  `build_duplicate_title_index` already uses for `.title` -- not
  re-implementing head extraction, only the index-building step this
  leaf needs a second time for a different field).
- SEO103: no `<meta property="og:title">`.
- SEO104: no `<meta property="og:type">`.
- SEO105: no `<meta property="og:image">`.
- SEO106: no `<meta property="og:url">`.
- SEO107: no `<link rel="canonical">`.
- SEO108: no `<link rel="icon">`/`<link rel="shortcut icon">` (favicon).
- SEO109: a JSON-LD `<script type="application/ld+json">` block that
  is not valid JSON.
- SEO110: a JSON-LD `LocalBusiness` block (`@type == "LocalBusiness"`)
  with no `name` property.
- SEO111: a JSON-LD `LocalBusiness` block with no `address` property.
- SEO112: a JSON-LD `LocalBusiness` block with no `telephone` property.

SEO110-112 only fire for a JSON-LD block whose `@type` is exactly
`"LocalBusiness"` -- a block for a different `@type` (e.g.
`"Organization"`, `_seo_substrate`'s own `home.html` fixture) carries no
LocalBusiness-shaped signal and is silently skipped, not flagged.

`html-lang` cross-refs A11Y104's own rule id (the ticket body's own
cross-reference) and is not duplicated here.

Each fires WARN-tier at first turn-on, the same T-0688/T-0973 promotion
posture every other brand-new WEBSEC/SEO family in this repo follows.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from frob.findings import Severity, Violation
from frob.gitio import run_argv
from frob.logging import get_logger
from frob.webapp._detect import FrameworkKind, detect_frameworks
from frob.webapp._seo_substrate import (
    PageMetadata,
    build_duplicate_title_index,
    extract_page_metadata,
)

_log = get_logger(__name__)

__all__ = [
    "WebsecSeoTagFinding",
    "seo_tag_findings",
    "websec_findings",
]

_PAGE_EXTENSIONS = (".html", ".jsx")

#: `<link rel="...">` values this module recognizes as a favicon
#: declaration.
_FAVICON_RELS = frozenset({"icon", "shortcut icon"})


# frob:doc docs/modules/webapp-seo-tags.md#public-api
# frob:ticket T-5374
@dataclass(frozen=True)
class WebsecSeoTagFinding:
    """One SEO101-112 finding: a duplicate/missing per-page tag, or a
    JSON-LD LocalBusiness block missing a required property.

    frob:ticket T-5374
    """

    rule: str
    file: str
    line: int
    message: str


def _tracked_page_files(root: Path) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `_PAGE_EXTENSIONS`,
    root-relative POSIX paths, `()` on any git failure -- mirrors
    `_websec_headers_log._tracked_files`'s own tracked-file-scan shape.

    frob:ticket T-5374
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("seo_tags: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("seo_tags: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(_PAGE_EXTENSIONS)
    )


def _extract_pages(root: Path) -> tuple[PageMetadata, ...]:
    """Every tracked `.html`/`.jsx` route file under `root`, turned into
    a `PageMetadata` via `extract_page_metadata` (T-5364's substrate,
    reused unchanged) -- a file with no `<head>`/`<Head>` element at all
    is silently skipped (`_seo_substrate`'s own documented "normal,
    expected outcome" for `SeoError.NoHeadElement`).

    frob:ticket T-5374
    """
    pages: list[PageMetadata] = []
    for rel in _tracked_page_files(root):
        result = extract_page_metadata(root / rel, route=rel)
        if result.is_err:
            _log.debug("seo_tags: skipping %s: %s", rel, result.danger_err)
            continue
        pages.append(result.danger_ok)
    return tuple(pages)


def _build_duplicate_description_index(
    pages: tuple[PageMetadata, ...],
) -> dict[str, tuple[str, ...]]:
    """`{description: (route, route, ...)}` for every meta description
    shared by two or more routes in `pages` -- the same index shape
    `_seo_substrate.build_duplicate_title_index` already builds for
    `.title`, reused for `.meta`'s `name="description"` entry instead.

    frob:ticket T-5374
    """
    by_description: dict[str, list[str]] = {}
    for page in pages:
        for tag in page.meta:
            if tag.name != "description" or not tag.content:
                continue
            by_description.setdefault(tag.content, []).append(page.route)
    return {
        description: tuple(routes)
        for description, routes in by_description.items()
        if len(routes) > 1
    }


def _source_path_by_route(pages: tuple[PageMetadata, ...]) -> dict[str, str]:
    """`route -> source_path` for every page -- `build_duplicate_title_index`
    and `_build_duplicate_description_index` both key their result by
    route, but a `Violation` needs a real file path.

    frob:ticket T-5374
    """
    return {page.route: page.source_path for page in pages}


def _duplicate_title_findings(
    pages: tuple[PageMetadata, ...],
) -> list[WebsecSeoTagFinding]:
    """SEO101: a `<title>` shared by two or more routes.

    frob:ticket T-5374
    """
    findings: list[WebsecSeoTagFinding] = []
    source_by_route = _source_path_by_route(pages)
    for title, routes in build_duplicate_title_index(pages).items():
        for route in routes:
            findings.append(
                WebsecSeoTagFinding(
                    rule="SEO101",
                    file=source_by_route.get(route, route),
                    line=1,
                    message=(
                        f"SEO101: {source_by_route.get(route, route)} title "
                        f"{title!r} is shared by {len(routes)} routes "
                        f"({', '.join(routes)}) -- not unique per route. "
                        f"Give each route its own title, or `frob:waive "
                        f'SEO101 reason="..."` with a real justification'
                    ),
                )
            )
    return findings


def _duplicate_description_findings(
    pages: tuple[PageMetadata, ...],
) -> list[WebsecSeoTagFinding]:
    """SEO102: a meta description shared by two or more routes.

    frob:ticket T-5374
    """
    findings: list[WebsecSeoTagFinding] = []
    source_by_route = _source_path_by_route(pages)
    for description, routes in _build_duplicate_description_index(pages).items():
        for route in routes:
            findings.append(
                WebsecSeoTagFinding(
                    rule="SEO102",
                    file=source_by_route.get(route, route),
                    line=1,
                    message=(
                        f"SEO102: {source_by_route.get(route, route)} meta "
                        f"description {description!r} is shared by "
                        f"{len(routes)} routes ({', '.join(routes)}) -- "
                        f"not unique per route. Give each route its own "
                        f'description, or `frob:waive SEO102 reason="..."` '
                        f"with a real justification"
                    ),
                )
            )
    return findings


def _missing_meta_property_findings(
    pages: tuple[PageMetadata, ...], rule: str, prop: str, label: str
) -> list[WebsecSeoTagFinding]:
    """One SEO103-106 rule: no `<meta property="{prop}">` on a page.

    frob:ticket T-5374
    """
    findings: list[WebsecSeoTagFinding] = []
    for page in pages:
        if any(tag.property == prop and tag.content for tag in page.meta):
            continue
        findings.append(
            WebsecSeoTagFinding(
                rule=rule,
                file=page.source_path,
                line=1,
                message=(
                    f"{rule}: {page.source_path} has no "
                    f'<meta property="{prop}"> ({label}) -- the shared '
                    f"link preview card is missing this field. Add it, "
                    f'or `frob:waive {rule} reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _missing_link_findings(
    pages: tuple[PageMetadata, ...], rule: str, rels: frozenset[str], label: str
) -> list[WebsecSeoTagFinding]:
    """SEO107/SEO108: no `<link rel="...">` matching `rels` on a page.

    frob:ticket T-5374
    """
    findings: list[WebsecSeoTagFinding] = []
    for page in pages:
        if any(link.rel in rels and link.href for link in page.links):
            continue
        findings.append(
            WebsecSeoTagFinding(
                rule=rule,
                file=page.source_path,
                line=1,
                message=(
                    f"{rule}: {page.source_path} has no {label} link tag "
                    f"({'/'.join(sorted(rels))}). Add it, or `frob:waive "
                    f'{rule} reason="..."` with a real justification'
                ),
            )
        )
    return findings


def _local_business_findings(
    pages: tuple[PageMetadata, ...],
) -> list[WebsecSeoTagFinding]:
    """SEO109-112: a malformed JSON-LD block, or a JSON-LD
    `LocalBusiness` block missing `name`/`address`/`telephone`.

    frob:ticket T-5374
    """
    findings: list[WebsecSeoTagFinding] = []
    for page in pages:
        for raw_block in page.json_ld:
            try:
                data = json.loads(raw_block)
            except (ValueError, TypeError):
                findings.append(
                    WebsecSeoTagFinding(
                        rule="SEO109",
                        file=page.source_path,
                        line=1,
                        message=(
                            f"SEO109: {page.source_path} a JSON-LD "
                            f'<script type="application/ld+json"> block '
                            f"is not valid JSON -- structured data that "
                            f"cannot even parse is silently ignored by "
                            f"every consumer. Fix the JSON, or `frob:waive "
                            f'SEO109 reason="..."` with a real '
                            f"justification"
                        ),
                    )
                )
                continue
            if not isinstance(data, dict) or data.get("@type") != "LocalBusiness":
                continue
            for prop, rule in (
                ("name", "SEO110"),
                ("address", "SEO111"),
                ("telephone", "SEO112"),
            ):
                if data.get(prop):
                    continue
                findings.append(
                    WebsecSeoTagFinding(
                        rule=rule,
                        file=page.source_path,
                        line=1,
                        message=(
                            f"{rule}: {page.source_path} a JSON-LD "
                            f"LocalBusiness block has no {prop!r} "
                            f"property -- schema.org's LocalBusiness "
                            f"requires it. Add it, or `frob:waive {rule} "
                            f'reason="..."` with a real justification'
                        ),
                    )
                )
    return findings


# frob:doc docs/modules/webapp-seo-tags.md#public-api
# frob:ticket T-5374
def seo_tag_findings(root: Path) -> tuple[WebsecSeoTagFinding, ...]:
    """SEO101-112: every per-page-tag finding under `root`.

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all -- the same contract every
    WEBSEC/COMPLY/A11Y/SEO/WEBPERF family in this repo uses (T-5302).
    """
    root = Path(root)
    if not detect_frameworks(root):
        _log.debug("seo_tags: no framework detected at %s, skipping scan", root)
        return ()

    pages = _extract_pages(root)
    findings: list[WebsecSeoTagFinding] = []
    findings.extend(_duplicate_title_findings(pages))
    findings.extend(_duplicate_description_findings(pages))
    findings.extend(
        _missing_meta_property_findings(pages, "SEO103", "og:title", "Open Graph title")
    )
    findings.extend(
        _missing_meta_property_findings(pages, "SEO104", "og:type", "Open Graph type")
    )
    findings.extend(
        _missing_meta_property_findings(pages, "SEO105", "og:image", "Open Graph image")
    )
    findings.extend(
        _missing_meta_property_findings(pages, "SEO106", "og:url", "Open Graph url")
    )
    findings.extend(
        _missing_link_findings(pages, "SEO107", frozenset({"canonical"}), "canonical")
    )
    findings.extend(_missing_link_findings(pages, "SEO108", _FAVICON_RELS, "favicon"))
    findings.extend(_local_business_findings(pages))

    _log.info("seo_tags: %d finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/webapp-seo-tags.md#public-api
# frob:ticket T-5374
def websec_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """Hook named to match `frob.gates._taint_gate`'s discovery SHAPE
    (`websec_findings(root, frameworks) -> tuple[Violation, ...]`) per
    this ticket's own coordinator direction -- see the module docstring's
    DISCOVERY CONVENTION section for why no live gate currently calls
    this hook (`_seo_tags` does not match `_taint_gate`'s `_websec_*`
    module-name prefix). `frameworks` is a caller's own already-computed
    `detect_frameworks(root)` result; an empty set short-circuits to
    `()`, same contract as `seo_tag_findings`.
    """
    if not frameworks:
        _log.debug("seo_tags: no framework detected at %s, skipping scan (hook)", root)
        return ()
    return tuple(
        Violation(
            rule=finding.rule,
            severity=Severity.WARN,
            file=finding.file,
            line=finding.line,
            message=finding.message,
        )
        for finding in seo_tag_findings(root)
    )
