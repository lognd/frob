"""Accessibility-statement page content-lint (docs/modules/gates.md#statement).

# frob:ticket T-5324

The W3C WAI "Developing an Accessibility Statement" guidance names eight
things a conformant accessibility-statement page states: an explicit
COMMITMENT to accessibility, the STANDARD it targets (WCAG 2.2 level AA
for this repo's own posture), a CONTACT channel for feedback, any known
LIMITATIONS, the MEASURES taken, the TECHNICAL prerequisites a visitor
needs, and the TESTED ENVIRONMENTS it was verified against -- plus the
page's own PRESENCE, which is a precondition for linting any of the rest.
`a11y_findings` is the one entry point every A11Y gate leaf (T-5323) calls
to get all of that in one pass, same "single family-level findings
function, gate module owns wiring" convention `websec_findings`/
`comply_findings`-shaped siblings already use (docs/modules/gates.md's
"catalogued is not enforced" lesson: `@gate` registration alone never
runs a finder, so this module never imports `frob.gates` itself).

Same shallow-sniff posture as `frob.webapp._comply_substrate` (T-5360)
and `frob.webapp._detect` (T-5302): a false negative (a statement that is
actually complete but phrased in words this lint's needles miss) is
cheaper to live with than a fragile NLP-grade content classifier, and a
plain-substring check is one a repo owner can read and predict. This
module never re-detects frameworks (`frob.webapp._detect.
detect_frameworks`, T-5302, is the one entry point every caller already
ran) and never re-implements `frob.webapp._comply_substrate`'s own
required-page route tables; the accessibility-page location candidates
below are its own narrow slice (accessibility only) of that same shallow
file-presence idiom, kept local because `_comply_substrate.py` is outside
this ticket's declared scope.
"""

from __future__ import annotations

import re
from pathlib import Path

from frob.findings import Severity, Violation
from frob.logging import get_logger
from frob.webapp._detect import FrameworkKind

_log = get_logger(__name__)

# Rule id for "no accessibility-statement page was found at all" -- a
# precondition failure distinct from any single missing content section
# below (A11Y107-A11Y113 assume a page was found to lint in the first
# place).
_RULE_PAGE_MISSING = "A11Y114"

# Candidate accessibility-statement page paths (relative to repo root),
# keyed off the already-detected `FrameworkKind` -- same file-based-router
# vs config-based-router split `_comply_substrate._FILE_ROUTE_CANDIDATES`/
# `_CONTENT_ROUTE_FILES` uses, narrowed to just the accessibility page
# since that is the only page this ticket's lint reads.
_FILE_ROUTE_CANDIDATES: dict[FrameworkKind, tuple[str, ...]] = {
    FrameworkKind.NEXTJS: (
        "pages/accessibility.js",
        "pages/accessibility.tsx",
        "app/accessibility/page.tsx",
        "app/accessibility/page.js",
    ),
    FrameworkKind.SVELTEKIT: ("src/routes/accessibility/+page.svelte",),
    FrameworkKind.ASTRO: ("src/pages/accessibility.astro",),
    FrameworkKind.VITE: ("src/pages/Accessibility.jsx", "src/pages/Accessibility.tsx"),
}

# Config-based routers: one file whose text is sniffed for the
# accessibility slug -- same convention (and same limitation: presence
# only, not the page's own separate content) as `_comply_substrate.
# _CONTENT_ROUTE_FILES`. For these frameworks the "page" IS effectively
# the route-config file text itself, since there is no separate template
# file this lint could point at.
_CONTENT_ROUTE_FILES: dict[FrameworkKind, str] = {
    FrameworkKind.DJANGO: "urls.py",
    FrameworkKind.FLASK: "app.py",
    FrameworkKind.FASTAPI: "main.py",
    # frob:waive DOC006 reason="illustrative route path, not a repo file"
    FrameworkKind.RAILS: "config/routes.rb",
    # frob:waive DOC006 reason="illustrative route path, not a repo file"
    FrameworkKind.LARAVEL: "routes/web.php",
}


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable
    (missing, binary, permission) -- same broad-catch shape as
    `frob.webapp._detect._read_text`.

    frob:ticket T-5324
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _locate_statement_page(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> Path | None:
    """The first existing accessibility-statement page/route-config file
    under `root` for any of `frameworks`, or `None` if none is present.

    frob:ticket T-5324
    """
    for kind in frameworks:
        for candidate in _FILE_ROUTE_CANDIDATES.get(kind, ()):
            path = root / candidate
            if path.exists():
                _log.debug("_locate_statement_page: found %s via %s", path, kind)
                return path
        content_file = _CONTENT_ROUTE_FILES.get(kind)
        if content_file is not None:
            path = root / content_file
            if path.exists() and "accessibility" in _read_text(path):
                _log.debug("_locate_statement_page: found %s via %s", path, kind)
                return path
    _log.debug("_locate_statement_page: no accessibility statement page under %s", root)
    return None


# frob:doc docs/modules/gates.md#statement-section
class _StatementSection:
    """One W3C WAI required accessibility-statement content section: its
    gate rule id, a human label for the violation message, and the
    case-insensitive regex needle(s) `a11y_findings` sniffs the page text
    for -- ANY needle matching counts the section present (same shallow
    either/or-substring posture `_comply_substrate.detect_signals` uses).

    frob:ticket T-5324
    """

    __slots__ = ("rule", "label", "pattern")

    def __init__(self, rule: str, label: str, pattern: str) -> None:
        """Store `rule`/`label` verbatim and compile `pattern` once
        (case-insensitive) -- `a11y_findings` runs this section's check
        once per lint, so a pre-compiled pattern avoids re-compiling the
        same regex per call."""
        self.rule = rule
        self.label = label
        self.pattern = re.compile(pattern, re.IGNORECASE)


# The seven W3C WAI "Developing an Accessibility Statement" required
# content sections, each its own reserved A11Y10x id (docs/modules/
# gates.md, T-5301) -- one Violation per missing section, so a partially
# complete statement page reports exactly which sections it still needs
# rather than one opaque "statement incomplete" finding.
_STATEMENT_SECTIONS: tuple[_StatementSection, ...] = (
    _StatementSection(
        "A11Y107",
        "commitment to accessibility",
        r"committed to|commitment to accessib|our commitment",
    ),
    _StatementSection(
        "A11Y108",
        "conformance standard applied (WCAG 2.2 AA)",
        r"wcag\s*2\.2.{0,40}(level\s*)?aa|aa.{0,40}wcag\s*2\.2",
    ),
    _StatementSection(
        "A11Y109",
        "feedback/contact channel",
        r"contact us|feedback|reach out|email us",
    ),
    _StatementSection(
        "A11Y110",
        "known limitations",
        r"known limitation|not (?:yet |fully )?accessible|non-?compliant",
    ),
    _StatementSection(
        "A11Y111",
        "measures taken",
        r"measures (?:we|taken|to)|steps (?:we|taken)|we have taken",
    ),
    _StatementSection(
        "A11Y112",
        "technical prerequisites",
        r"technical(?:ly)? (?:prerequisite|requirement)|requires? (?:javascript"
        r"|a modern browser)",
    ),
    _StatementSection(
        "A11Y113",
        "tested environments",
        r"tested (?:with|on|using)|tested environment|assistive technolog",
    ),
)


# frob:doc docs/modules/gates.md#a11y_findings
def a11y_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """The accessibility-statement content-lint findings for `root`:
    `A11Y114` if no statement page/route is present at all, otherwise one
    `Violation` per `_STATEMENT_SECTIONS` entry whose needle pattern does
    not match the page text.

    An empty `frameworks` (no detected web framework) or a repo with no
    accessibility-statement page/route at all returns just the single
    `A11Y114` finding -- this function never re-detects frameworks itself
    (`frob.webapp._detect.detect_frameworks`, T-5302, is the caller's
    job), and a missing page is reported once, not once per section
    (there is nothing to sniff for sections yet).

    frob:ticket T-5324
    """
    page = _locate_statement_page(root, frameworks)
    if page is None:
        _log.debug("a11y_findings: no accessibility statement page found at %s", root)
        return (
            Violation(
                rule=_RULE_PAGE_MISSING,
                severity=Severity.ERROR,
                file=".",
                line=1,
                message=(
                    "no accessibility statement page found -- add one covering "
                    "commitment, WCAG 2.2 AA conformance, contact, known "
                    "limitations, measures taken, technical prerequisites, and "
                    "tested environments (W3C WAI accessibility statement guidance)"
                ),
            ),
        )

    text = _read_text(page)
    rel = str(page.relative_to(root))
    findings: list[Violation] = []
    for section in _STATEMENT_SECTIONS:
        if section.pattern.search(text):
            continue
        findings.append(
            Violation(
                rule=section.rule,
                severity=Severity.ERROR,
                file=rel,
                line=1,
                message=(
                    f"accessibility statement is missing its {section.label} "
                    "section (W3C WAI accessibility statement guidance)"
                ),
            )
        )
    _log.debug("a11y_findings: %d finding(s) for %s", len(findings), rel)
    return tuple(findings)
