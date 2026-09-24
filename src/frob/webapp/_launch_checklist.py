"""LAUNCH101-107: pre-launch checklist advisory-only convention items
(docs/modules/webapp-launch-checklist.md, T-5361): team photo, case
studies, FAQ count, thank-you page, sticky mobile CTA, response-time
promise, and analytics presence -- file-existence/text-search checks
only, no AST walk, no gate-blocking output.

OWNER DIRECTIVE (ticket body): these NEVER error, NEVER warn -- every
LAUNCH finding is `Severity.ADVISORY` (T-5304, already landed in
`frob.findings`: a fourth, distinct outcome that is always reported but
NEVER contributes to exit status, the verify quarantine, or the
ratchet). This is not a never-fail flag bolted onto `WARN`; it is a
different KIND of claim, the same posture `Severity.UNRESOLVED` already
established for "could not determine an answer at all" -- see
`frob.findings.Severity`'s own docstring and
`tests/unit/test_check_gates_summary.py::TestSeverityAdvisory` (T-5304's
own must-fire fixture: an ADVISORY finding never turns a gate verdict
to FAIL) for the guarantee this leaf's own findings ride on unchanged.

Each check is a repo-wide presence/content sniff -- the same
"one aggregate finding for the whole repo, not one per file" shape
the SEO crawl/discovery leaf's own `llms.txt` presence check (T-5362)
already uses, and
the same `_file_route_present`/`_content_route_present`-style
file-existence-or-content-search idiom `frob.webapp._comply_substrate`
(T-5360) already established for its own PRIVACY/TERMS/ACCESSIBILITY
`RequiredPage` checks -- this leaf writes its own small local checks
rather than widening `RequiredPage` (a shared enum with three fixed,
GDPR/CCPA/ADA-adjacent members) for seven unrelated marketing/UX
convention items a single consumer needs.

SEVEN RULE IDS, filling the entire reserved `LAUNCH101`-`LAUNCH107`
block:

- LAUNCH101: no tracked page/path mentions a team photo ("our team"/
  "meet the team" text, or a `team` path segment).
- LAUNCH102: no tracked page/path mentions case studies ("case study"/
  "case studies" text, or a `case-studies`/`case_studies` path
  segment).
- LAUNCH103: an FAQ page exists (a `faq` path segment) but reads thin
  (fewer than 3 `?` question marks in its content).
- LAUNCH104: no tracked page/path is a thank-you page (`thank-you`/
  `thankyou`/`thanks` path segment).
- LAUNCH105: no tracked page mentions a sticky mobile call-to-action
  (`sticky`/`fixed` positioning AND `cta`/`call-to-action` wording in
  the SAME file).
- LAUNCH106: no tracked page makes an explicit response-time promise
  ("respond within"/"reply within"/"response time" wording).
- LAUNCH107: no tracked page/config carries an analytics snippet
  (`gtag(`/`google-analytics`/`plausible.io`/`posthog`).

DISCOVERY: same posture every WEBSEC/SEO/WEBPERF leaf in this family
documents -- no live gate discovers this module's `websec_findings`
hook yet (`_launch_checklist` does not match `frob.gates._taint_gate`'s
discovered-prefix tuple); T-draft-553232aa is the actual fix.
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
    "WebsecLaunchChecklistFinding",
    "launch_checklist_findings",
    "websec_findings",
]

_PAGE_EXTENSIONS = (".html", ".jsx", ".tsx")

_TEAM_PHOTO_RE = re.compile(r"""our team|meet the team""", re.IGNORECASE)
_TEAM_PATH_RE = re.compile(r"""(^|/)team(/|[.-]|$)""", re.IGNORECASE)

_CASE_STUDY_RE = re.compile(r"""case stud(?:y|ies)""", re.IGNORECASE)
_CASE_STUDY_PATH_RE = re.compile(r"""case[-_]stud""", re.IGNORECASE)

_FAQ_PATH_RE = re.compile(r"""(^|/)faq(/|[.-]|$)""", re.IGNORECASE)
_QUESTION_MARK_MIN = 3

_THANK_YOU_PATH_RE = re.compile(r"""thank[-_]?you|thanks""", re.IGNORECASE)

_STICKY_HINT_RE = re.compile(r"""\bsticky\b|position:\s*fixed""", re.IGNORECASE)
_CTA_HINT_RE = re.compile(r"""\bcta\b|call-to-action""", re.IGNORECASE)

_RESPONSE_TIME_RE = re.compile(
    r"""respond(?:s|ing)? within|reply within|response time""", re.IGNORECASE
)

_ANALYTICS_RE = re.compile(
    r"""gtag\s*\(|google-analytics|plausible\.io|posthog""", re.IGNORECASE
)


# frob:doc docs/modules/webapp-launch-checklist.md#public-api
# frob:ticket T-5361
@dataclass(frozen=True)
class WebsecLaunchChecklistFinding:
    """One LAUNCH101-107 finding: an advisory-only pre-launch checklist
    item missing repo-wide. Always `Severity.ADVISORY` once wrapped by
    `websec_findings` -- never WARN, never ERROR.

    frob:ticket T-5361
    """

    rule: str
    file: str
    line: int
    message: str


def _tracked_files(root: Path, *suffixes: str) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `suffixes`, root-relative
    POSIX paths, `()` on any git failure -- mirrors
    `_websec_headers_log._tracked_files`'s own tracked-file-scan shape.

    frob:ticket T-5361
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("launch_checklist: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("launch_checklist: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(suffixes)
    )


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable.

    frob:ticket T-5361
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _repo_wide_finding(rule: str, message: str) -> WebsecLaunchChecklistFinding:
    """One repo-wide advisory (`file="."`, `line=1`) -- every LAUNCH
    check here is a presence sniff across the whole repo, not a single
    call site.

    frob:ticket T-5361
    """
    return WebsecLaunchChecklistFinding(rule=rule, file=".", line=1, message=message)


def _team_photo_findings(
    pages: tuple[str, ...], texts: dict[str, str]
) -> list[WebsecLaunchChecklistFinding]:
    """LAUNCH101: no team photo page/mention anywhere.

    frob:ticket T-5361
    """
    if any(_TEAM_PATH_RE.search(rel) for rel in pages) or any(
        _TEAM_PHOTO_RE.search(text) for text in texts.values()
    ):
        return []
    return [
        _repo_wide_finding(
            "LAUNCH101",
            "LAUNCH101: no team photo page/mention found -- a team page "
            "builds trust before launch. Add one, or `frob:waive "
            'LAUNCH101 reason="..."` with a real justification',
        )
    ]


def _case_studies_findings(
    pages: tuple[str, ...], texts: dict[str, str]
) -> list[WebsecLaunchChecklistFinding]:
    """LAUNCH102: no case-studies page/mention anywhere.

    frob:ticket T-5361
    """
    if any(_CASE_STUDY_PATH_RE.search(rel) for rel in pages) or any(
        _CASE_STUDY_RE.search(text) for text in texts.values()
    ):
        return []
    return [
        _repo_wide_finding(
            "LAUNCH102",
            "LAUNCH102: no case studies page/mention found -- social "
            "proof helps conversion before launch. Add one, or `frob:waive "
            'LAUNCH102 reason="..."` with a real justification',
        )
    ]


def _faq_count_findings(
    pages: tuple[str, ...], texts: dict[str, str]
) -> list[WebsecLaunchChecklistFinding]:
    """LAUNCH103: an FAQ page exists but reads thin.

    frob:ticket T-5361
    """
    faq_pages = [rel for rel in pages if _FAQ_PATH_RE.search(rel)]
    if not faq_pages:
        return []
    findings: list[WebsecLaunchChecklistFinding] = []
    for rel in faq_pages:
        count = texts.get(rel, "").count("?")
        if count >= _QUESTION_MARK_MIN:
            continue
        findings.append(
            WebsecLaunchChecklistFinding(
                rule="LAUNCH103",
                file=rel,
                line=1,
                message=(
                    f"LAUNCH103: {rel} has only {count} question(s) -- "
                    f"a thin FAQ. Add more, or `frob:waive LAUNCH103 "
                    f'reason="..."` with a real justification'
                ),
            )
        )
    return findings


def _thank_you_page_findings(
    pages: tuple[str, ...],
) -> list[WebsecLaunchChecklistFinding]:
    """LAUNCH104: no thank-you page anywhere.

    frob:ticket T-5361
    """
    if any(_THANK_YOU_PATH_RE.search(rel) for rel in pages):
        return []
    return [
        _repo_wide_finding(
            "LAUNCH104",
            "LAUNCH104: no thank-you page found -- a post-conversion "
            "thank-you page confirms the action landed. Add one, or "
            '`frob:waive LAUNCH104 reason="..."` with a real '
            "justification",
        )
    ]


def _sticky_cta_findings(texts: dict[str, str]) -> list[WebsecLaunchChecklistFinding]:
    """LAUNCH105: no sticky mobile CTA anywhere.

    frob:ticket T-5361
    """
    if any(
        _STICKY_HINT_RE.search(text) and _CTA_HINT_RE.search(text)
        for text in texts.values()
    ):
        return []
    return [
        _repo_wide_finding(
            "LAUNCH105",
            "LAUNCH105: no sticky mobile call-to-action found -- a "
            "persistent mobile CTA lifts conversion. Add one, or "
            '`frob:waive LAUNCH105 reason="..."` with a real '
            "justification",
        )
    ]


def _response_time_findings(
    texts: dict[str, str],
) -> list[WebsecLaunchChecklistFinding]:
    """LAUNCH106: no explicit response-time promise anywhere.

    frob:ticket T-5361
    """
    if any(_RESPONSE_TIME_RE.search(text) for text in texts.values()):
        return []
    return [
        _repo_wide_finding(
            "LAUNCH106",
            "LAUNCH106: no response-time promise found (e.g. "
            '"we respond within 24 hours") -- sets expectations before '
            'launch. Add one, or `frob:waive LAUNCH106 reason="..."` '
            "with a real justification",
        )
    ]


def _analytics_findings(
    root: Path, pages: tuple[str, ...], texts: dict[str, str]
) -> list[WebsecLaunchChecklistFinding]:
    """LAUNCH107: no analytics snippet anywhere.

    frob:ticket T-5361
    """
    config_files = _tracked_files(root, ".html", ".jsx", ".tsx", ".js")
    combined = "\n".join(texts.get(rel, "") for rel in pages)
    combined += "\n".join(_read_text(root / rel) for rel in config_files)
    if _ANALYTICS_RE.search(combined):
        return []
    return [
        _repo_wide_finding(
            "LAUNCH107",
            "LAUNCH107: no analytics snippet found (gtag/Google "
            "Analytics/Plausible/PostHog) -- launching with no traffic "
            "visibility. Add one, or `frob:waive LAUNCH107 reason="
            '"..."` with a real justification',
        )
    ]


# frob:doc docs/modules/webapp-launch-checklist.md#public-api
# frob:ticket T-5361
def launch_checklist_findings(root: Path) -> tuple[WebsecLaunchChecklistFinding, ...]:
    """LAUNCH101-107: every pre-launch checklist advisory finding under
    `root`.

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all -- the same contract every
    WEBSEC/COMPLY/A11Y/SEO/WEBPERF family in this repo uses (T-5302).
    """
    root = Path(root)
    if not detect_frameworks(root):
        _log.debug("launch_checklist: no framework detected at %s, skipping scan", root)
        return ()

    pages = _tracked_files(root, *_PAGE_EXTENSIONS)
    texts = {rel: _read_text(root / rel) for rel in pages}

    findings: list[WebsecLaunchChecklistFinding] = []
    findings.extend(_team_photo_findings(pages, texts))
    findings.extend(_case_studies_findings(pages, texts))
    findings.extend(_faq_count_findings(pages, texts))
    findings.extend(_thank_you_page_findings(pages))
    findings.extend(_sticky_cta_findings(texts))
    findings.extend(_response_time_findings(texts))
    findings.extend(_analytics_findings(root, pages, texts))

    _log.info("launch_checklist: %d finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/webapp-launch-checklist.md#public-api
# frob:ticket T-5361
def websec_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """Hook named to match `frob.gates._taint_gate`'s discovery SHAPE
    (`websec_findings(root, frameworks) -> tuple[Violation, ...]`), the
    same convention every sibling WEBSEC/SEO/WEBPERF leaf follows -- see
    the module docstring's DISCOVERY section for why no live gate
    currently calls it. `frameworks` is a caller's own already-computed
    `detect_frameworks(root)` result; an empty set short-circuits to
    `()`, same contract as `launch_checklist_findings`.

    Every returned `Violation` carries `Severity.ADVISORY` -- the owner
    directive this whole family exists to satisfy (never WARN, never
    ERROR; see the module docstring for the T-5304 guarantee this rides
    on).
    """
    if not frameworks:
        _log.debug(
            "launch_checklist: no framework detected at %s, skipping scan (hook)",
            root,
        )
        return ()
    return tuple(
        Violation(
            rule=finding.rule,
            severity=Severity.ADVISORY,
            file=finding.file,
            line=finding.line,
            message=finding.message,
        )
        for finding in launch_checklist_findings(root)
    )
