"""COMPLY101-108: privacy-policy page content, CCPA/CalOPPA
(docs/modules/webapp-comply-privacy.md, T-5372, the `T-5140`/T-5145
web-app-lint epic's privacy-policy leaf, blocked_by=['T-5360']).

Builds on `frob.webapp._comply_substrate` (T-5360, docs/modules/
webapp-comply.md) for the two questions that substrate already answers
-- "does this repo publish a /privacy page at all" (`detect_required_pages`,
`RequiredPage.PRIVACY`) and "does this repo's manifest imply a
session-replay-or-pixel / data-sale-or-share behavior" (`detect_signals`,
`ComplySignal.SESSION_REPLAY_OR_PIXEL`/`ComplySignal.DATA_SALE_OR_SHARE`)
-- and never re-implements either. The substrate's page-presence check is
a boolean only (it never exposes WHICH file the page lives at, since its
own per-framework candidate tables are private implementation detail),
so this module keeps its own small, disclosed-as-v1 candidate search
(`_locate_privacy_page`, a tracked-file name-stem scan) to find the
actual privacy-page file to content-lint -- the same "own tiny
candidate table, not a cross-module private import" posture
`frob.webapp._a11y_statement._locate_statement_page`'s module docstring
documents for the exact same problem in the accessibility-statement
leaf.

EIGHT RULE IDS (T-5301's reserved `COMPLY101`-`COMPLY108` block, the
ticket body's CCPA/CalOPPA-shaped corpus):

- COMPLY101: no `/privacy` page found at all (baseline requirement,
  `detect_required_pages`'s `RequiredPage.PRIVACY` reporting absent, or
  this module's own candidate search finding no file to content-lint
  even when the substrate reports the page present via a route-config
  slug mention with no matching file).
- COMPLY102: the privacy page's text has no "categories collected"-
  shaped section (CalOPPA Cal. Bus. & Prof. Code 22575(b): what
  categories of PI the site collects).
- COMPLY103: no "effective date"-shaped section (CalOPPA 22575(b)).
- COMPLY104: no "do not track"-shaped section (CalOPPA 22575(b)(5)).
- COMPLY105: no `last_updated` frontmatter date at all (CCPA Cal. Civ.
  Code 1798.130(a)(5) wants the policy's own update-recency visible).
- COMPLY106: `last_updated` frontmatter date present but more than 12
  months stale (CCPA 1798.130(a)(5)'s own 12-month review cadence).
- COMPLY107: `ComplySignal.SESSION_REPLAY_OR_PIXEL` detected (a tracking
  pixel/session-replay script implied by the manifest) but no
  "do not sell"/"do not sell or share"-shaped link/section in the
  privacy page (CCPA 1798.135(a)).
- COMPLY108: `ComplySignal.DATA_SALE_OR_SHARE` detected but no
  "categories ... sold"/"categories ... shared"-shaped section (CCPA
  1798.130(a)(5)'s second list -- categories collected, per COMPLY102,
  is distinct from categories SOLD/SHARED in the past 12 months, which
  this id owns).

FRAMEWORK GATING (T-5302): same short-circuit posture every WEBSEC/
COMPLY/A11Y/SEO/WEBPERF family uses -- `frob.webapp._detect.
detect_frameworks(root)` empty means no scan at all.

WIRING: `frob.webapp._comply_substrate`'s own doc
(docs/modules/webapp-comply.md) defines no comply-specific gate-
discovery hook or convention yet (no comply leaf has landed before this
one). Per this leaf's own dispatch brief, this module follows
`frob.gates._taint_gate`'s existing WEBSEC discovery CONVENTION instead
of inventing a new one: `websec_findings(root, frameworks) ->
tuple[Violation, ...]`, the exact signature T-5308's
`_discover_websec_hook_modules` already expects. `_taint_gate.py`'s
discovery prefix is widened from `_websec_` alone to also match
`_comply_` (see that module's own docstring) so this hook is actually
discovered and called, not merely convention-shaped -- the positive
control below calls the real `taint_gate()` end to end.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from frob.excludes import iter_files
from frob.findings import Severity, Violation
from frob.logging import get_logger
from frob.webapp._comply_substrate import (
    ComplySignal,
    RequiredPage,
    detect_required_pages,
    detect_signals,
)
from frob.webapp._detect import FrameworkKind, detect_frameworks

_log = get_logger(__name__)

__all__ = [
    "ComplyPrivacyFinding",
    "comply_privacy_findings",
    "websec_findings",
]

#: Tracked-file extensions this module content-lints as a "page" --
#: markdown/MDX/HTML/framework-component text, never binary.
_PAGE_EXTENSIONS = (".md", ".mdx", ".html", ".htm", ".astro", ".svelte", ".jsx", ".tsx")

#: 12-month staleness floor (CCPA 1798.130(a)(5)'s own review cadence),
#: measured in whole days rather than a calendar-month diff (no
#: dependency on a calendar-arithmetic library for one threshold).
_STALENESS_DAYS = 366

_FRONTMATTER_DATE_RE = re.compile(
    r"^last_updated\s*[:=]\s*[\"']?(\d{4}-\d{2}-\d{2})[\"']?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

_CATEGORIES_COLLECTED_RE = re.compile(
    r"categories\s+(?:of\s+(?:personal\s+information|pi)\s+)?(?:we\s+)?collect",
    re.IGNORECASE,
)
_EFFECTIVE_DATE_RE = re.compile(r"effective\s+date", re.IGNORECASE)
_DO_NOT_TRACK_RE = re.compile(r"do\s+not\s+track", re.IGNORECASE)
_DO_NOT_SELL_RE = re.compile(r"do\s+not\s+sell(?:\s+or\s+share)?", re.IGNORECASE)
_CATEGORIES_SOLD_RE = re.compile(
    r"categories\s+(?:of\s+(?:personal\s+information|pi)\s+)?(?:we\s+)?"
    r"(?:sold|sell|shared|share)",
    re.IGNORECASE,
)


# frob:doc docs/modules/webapp-comply-privacy.md#public-api
# frob:tests \
# tests/unit/test_webapp_comply_privacy.py::test_comply_privacy_findings_fixture[missing_page-COMPLY101-True] kind="unit"  # noqa: E501
@dataclass(frozen=True)
class ComplyPrivacyFinding:
    """One COMPLY101-108 finding: a privacy-policy content rule id, the
    file and line the gap was found (or not found) at, and a human
    message.

    frob:ticket T-5372
    """

    rule: str
    file: str
    line: int
    message: str


def _tracked_page_files(root: Path) -> tuple[Path, ...]:
    """Every tracked file under `root` whose suffix is `_PAGE_EXTENSIONS`,
    routed through `frob.excludes.iter_files` (WALK001: prunes vendor/
    VCS/build directories before ever descending).

    frob:ticket T-5372
    """
    return tuple(path for path in iter_files(root) if path.suffix in _PAGE_EXTENSIONS)


def _locate_privacy_page(root: Path) -> Path | None:
    """The first tracked page file whose path stem (case-insensitive)
    contains "privacy" -- this module's own small candidate search, kept
    separate from `frob.webapp._comply_substrate`'s private per-framework
    route tables (which only answer presence, never a path) per this
    module's own docstring. Disclosed v1 scope: a repo naming its policy
    page something with no "privacy" substring at all (e.g. a single
    "legal.md" covering privacy+terms) is not found here.

    frob:ticket T-5372
    """
    candidates = sorted(
        (path for path in _tracked_page_files(root) if "privacy" in path.stem.lower()),
        key=lambda path: path.as_posix(),
    )
    return candidates[0] if candidates else None


def _line_of(text: str, offset: int) -> int:
    """1-based line number of char `offset` in `text`.

    frob:ticket T-5372
    """
    return text.count("\n", 0, offset) + 1


def _section_finding(
    rule: str, pattern: re.Pattern[str], text: str, rel_path: str, label: str
) -> ComplyPrivacyFinding | None:
    """`None` if `pattern` matches somewhere in `text`; otherwise one
    `rule` finding reported at line 1 (a missing section has no line of
    its own to point at).

    frob:ticket T-5372
    """
    if pattern.search(text):
        return None
    return ComplyPrivacyFinding(
        rule=rule,
        file=rel_path,
        line=1,
        message=(
            f"{rule}: {rel_path} has no {label} section -- "
            f'add one, or `frob:waive {rule} reason="..."` with a real '
            "justification"
        ),
    )


def _staleness_findings(text: str, rel_path: str) -> list[ComplyPrivacyFinding]:
    """COMPLY105 (no `last_updated` frontmatter date at all) / COMPLY106
    (present but more than `_STALENESS_DAYS` old).

    frob:ticket T-5372
    """
    match = _FRONTMATTER_DATE_RE.search(text)
    if match is None:
        return [
            ComplyPrivacyFinding(
                rule="COMPLY105",
                file=rel_path,
                line=1,
                message=(
                    f"COMPLY105: {rel_path} has no last_updated frontmatter "
                    "date -- CCPA 1798.130(a)(5) wants the policy's own "
                    "update recency visible. Add a `last_updated: "
                    "YYYY-MM-DD` frontmatter key, or `frob:waive COMPLY105 "
                    'reason="..."` with a real justification'
                ),
            )
        ]
    line = _line_of(text, match.start())
    try:
        last_updated = date.fromisoformat(match.group(1))
    except ValueError:
        _log.warning(
            "comply_privacy: %s: unparseable last_updated date %r",
            rel_path,
            match.group(1),
        )
        return []
    age_days = (datetime.now(UTC).date() - last_updated).days
    if age_days <= _STALENESS_DAYS:
        return []
    return [
        ComplyPrivacyFinding(
            rule="COMPLY106",
            file=rel_path,
            line=line,
            message=(
                f"COMPLY106: {rel_path}:{line} last_updated ({last_updated}) "
                f"is {age_days} day(s) old, past the "
                f"{_STALENESS_DAYS}-day/12-month CCPA 1798.130(a)(5) review "
                f"cadence -- refresh the policy, or `frob:waive COMPLY106 "
                'reason="..."` with a real justification'
            ),
        )
    ]


def _signal_gated_findings(
    text: str, rel_path: str, signals: frozenset[ComplySignal]
) -> list[ComplyPrivacyFinding]:
    """COMPLY107 (Do-Not-Sell link missing when a tracking pixel is
    detected) / COMPLY108 (categories-sold-or-shared section missing when
    a data-sale-or-share signal is detected).

    frob:ticket T-5372
    """
    findings: list[ComplyPrivacyFinding] = []
    if ComplySignal.SESSION_REPLAY_OR_PIXEL in signals:
        finding = _section_finding(
            "COMPLY107", _DO_NOT_SELL_RE, text, rel_path, '"do not sell"'
        )
        if finding is not None:
            findings.append(finding)
    if ComplySignal.DATA_SALE_OR_SHARE in signals:
        finding = _section_finding(
            "COMPLY108",
            _CATEGORIES_SOLD_RE,
            text,
            rel_path,
            '"categories sold or shared"',
        )
        if finding is not None:
            findings.append(finding)
    return findings


# frob:doc docs/modules/webapp-comply-privacy.md#public-api
# frob:ticket T-5372
def comply_privacy_findings(root: Path) -> tuple[ComplyPrivacyFinding, ...]:
    """COMPLY101-108: every privacy-policy content finding under `root`.

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all (T-5302's contract, same posture
    every sibling WEBSEC/COMPLY family follows).

    frob:ticket T-5372
    """
    root = Path(root)
    frameworks = detect_frameworks(root)
    if not frameworks:
        _log.debug("comply_privacy: no framework detected at %s, skipping scan", root)
        return ()

    required_pages = detect_required_pages(root, frameworks)
    pages = frozenset() if required_pages.is_err else required_pages.danger_ok
    page_path = _locate_privacy_page(root)
    if RequiredPage.PRIVACY not in pages or page_path is None:
        return (
            ComplyPrivacyFinding(
                rule="COMPLY101",
                file="<repo>",
                line=1,
                message=(
                    "COMPLY101: no /privacy page found -- CalOPPA/CCPA "
                    "require a published privacy policy. Publish one, or "
                    '`frob:waive COMPLY101 reason="..."` with a real '
                    "justification"
                ),
            ),
        )

    rel_path = page_path.relative_to(root).as_posix()
    text = page_path.read_text(encoding="utf-8", errors="ignore")
    signals = detect_signals(root)

    findings: list[ComplyPrivacyFinding] = []
    for rule, pattern, label in (
        ("COMPLY102", _CATEGORIES_COLLECTED_RE, '"categories collected"'),
        ("COMPLY103", _EFFECTIVE_DATE_RE, '"effective date"'),
        ("COMPLY104", _DO_NOT_TRACK_RE, '"do not track"'),
    ):
        finding = _section_finding(rule, pattern, text, rel_path, label)
        if finding is not None:
            findings.append(finding)
    findings.extend(_staleness_findings(text, rel_path))
    findings.extend(_signal_gated_findings(text, rel_path, signals))

    _log.info("comply_privacy: %d finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/webapp-comply-privacy.md#public-api
# frob:ticket T-5372
def websec_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """`frob.gates._taint_gate.taint_gate`'s hook-discovery contract
    (T-5308's `_websec_findings`-shaped signature, reused by this COMPLY
    leaf per this module's own docstring since `frob.webapp.
    _comply_substrate` defines no comply-specific hook convention of its
    own yet). `frameworks` is the caller's own already-computed
    `detect_frameworks(root)` result -- an empty set short-circuits to
    `()` exactly like `comply_privacy_findings`'s own direct-call
    contract.

    frob:ticket T-5372
    """
    if not frameworks:
        _log.debug(
            "comply_privacy: no framework detected at %s, skipping scan (hook)", root
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
        for finding in comply_privacy_findings(root)
    )
