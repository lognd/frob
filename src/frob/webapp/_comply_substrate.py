"""COMPLY substrate: repo-behavior-signal detection plus required-page
presence, keyed off `frob.webapp._detect` (docs/modules/webapp-comply.md).

# frob:ticket T-5360

`detect_signals` sniffs manifests (package.json / requirements.txt /
pyproject.toml) for third-party packages that imply a COMPLY-relevant
repo behavior -- collecting email, running AI on user data, billing
subscriptions, selling-or-sharing data, sending SMS, embedding a
session-replay-or-pixel script, or processing health data -- mirroring
`frob.webapp._detect.detect_frameworks`'s own shallow marker-file/
manifest-substring sniff (T-5302): a false negative (a COMPLY rule
family that never fires) is cheaper to live with than a deep, fragile
AST-level intent analysis, and a shallow check is one a repo owner can
read and predict.

`detect_required_pages` is a presence/content sniff for the
privacy/terms/accessibility pages GDPR/CCPA/ADA-adjacent COMPLY rules
expect a repo to publish, keyed off the `FrameworkKind` the caller
already detected via `detect_frameworks` -- this module never
re-detects frameworks (T-5302 owns that).
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.logging import get_logger
from frob.webapp._detect import FrameworkKind

_log = get_logger(__name__)


# frob:doc docs/modules/webapp-comply.md#complysignal
class ComplySignal(StrEnum):
    """One repo-behavior signal `detect_signals` can report, each driving
    which COMPLY rules are relevant to this repo.

    frob:ticket T-5360
    """

    EMAIL_COLLECTION = "email_collection"
    AI_ON_USER_DATA = "ai_on_user_data"
    SUBSCRIPTIONS = "subscriptions"
    DATA_SALE_OR_SHARE = "data_sale_or_share"
    SMS = "sms"
    SESSION_REPLAY_OR_PIXEL = "session_replay_or_pixel"
    HEALTH_DATA = "health_data"


# frob:doc docs/modules/webapp-comply.md#requiredpage
class RequiredPage(StrEnum):
    """One site-signal page `detect_required_pages` checks presence of.

    frob:ticket T-5360
    """

    PRIVACY = "privacy"
    TERMS = "terms"
    ACCESSIBILITY = "accessibility"


# frob:doc docs/modules/webapp-comply.md#detect_required_pages
class ComplyScanError(ErrorSet):
    """Failure values `detect_required_pages` can return.

    frob:ticket T-5360
    """

    ROOT_NOT_READABLE = (
        "root directory could not be listed (permission denied or not a directory)"
    )


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable
    (missing, binary, permission) -- same broad-catch shape as
    `frob.webapp._detect._read_text` (T-5302).

    frob:ticket T-5360
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _manifest_mentions(root: Path, manifest_name: str, *needles: str) -> bool:
    """True if `root/manifest_name` exists and its text contains any of `needles`.

    frob:ticket T-5360
    """
    text = _read_text(root / manifest_name)
    if not text:
        return False
    return any(needle in text for needle in needles)


def _any_manifest_mentions(root: Path, *needles: str) -> bool:
    """True if any of the three manifest kinds this module reads
    (package.json, requirements.txt, pyproject.toml) mentions any of `needles`.

    frob:ticket T-5360
    """
    return (
        _manifest_mentions(root, "package.json", *needles)
        or _manifest_mentions(root, "requirements.txt", *needles)
        or _manifest_mentions(root, "pyproject.toml", *needles)
    )


# Packages whose presence in a manifest implies a COMPLY-relevant repo
# behavior. Needles are matched as plain substrings against manifest text
# (dependency names, however quoted), same shallow style as
# frob.webapp._detect's framework markers.
_SIGNAL_PACKAGES: dict[ComplySignal, tuple[str, ...]] = {
    ComplySignal.EMAIL_COLLECTION: (
        "sendgrid",
        "mailchimp",
        "mailgun",
        "nodemailer",
        "postmark",
    ),
    ComplySignal.AI_ON_USER_DATA: ("openai", "anthropic", "cohere", "langchain"),
    ComplySignal.SUBSCRIPTIONS: ("stripe", "paddle", "chargebee", "recurly"),
    ComplySignal.DATA_SALE_OR_SHARE: (
        "segment",
        "amplitude",
        "mixpanel",
        "google-ads",
        "doubleclick",
    ),
    ComplySignal.SMS: ("twilio", "vonage", "plivo", "messagebird"),
    ComplySignal.SESSION_REPLAY_OR_PIXEL: (
        "fullstory",
        "hotjar",
        "logrocket",
        "clarity",
        "mouseflow",
    ),
    ComplySignal.HEALTH_DATA: ("fhir", "hl7", "epic-fhir", "cerner"),
}


# frob:doc docs/modules/webapp-comply.md#detect_signals
def detect_signals(root: Path) -> frozenset[ComplySignal]:
    """Sniff `root`'s manifests for third-party packages implying a
    COMPLY-relevant repo behavior, returning the frozenset of matches.

    A repo with no matching package (the "plain" fixture) returns the
    empty frozenset -- the signal COMPLY rules use to skip a check that
    is not relevant to this repo at all.

    frob:ticket T-5360
    """
    found: set[ComplySignal] = set()
    for signal, needles in _SIGNAL_PACKAGES.items():
        if _any_manifest_mentions(root, *needles):
            found.add(signal)
            _log.debug("detect_signals: %s matched at %s", signal, root)
    if not found:
        _log.debug("detect_signals: no signal detected at %s", root)
    return frozenset(found)


# Candidate route file paths (relative to repo root) checked for each
# RequiredPage, keyed off the framework's own router/page convention.
# Each tuple entry is a glob-free relative path checked for existence;
# file-based routers (Next.js/SvelteKit/Astro) list one entry per
# recognized page-file convention, config-based routers (Django/Flask/
# FastAPI/Rails/Laravel) list the one file whose content is sniffed for
# the page's slug.
_FILE_ROUTE_CANDIDATES: dict[FrameworkKind, dict[RequiredPage, tuple[str, ...]]] = {
    FrameworkKind.NEXTJS: {
        RequiredPage.PRIVACY: (
            "pages/privacy.js",
            "pages/privacy.tsx",
            "app/privacy/page.tsx",
            "app/privacy/page.js",
        ),
        RequiredPage.TERMS: (
            "pages/terms.js",
            "pages/terms.tsx",
            "app/terms/page.tsx",
            "app/terms/page.js",
        ),
        RequiredPage.ACCESSIBILITY: (
            "pages/accessibility.js",
            "pages/accessibility.tsx",
            "app/accessibility/page.tsx",
            "app/accessibility/page.js",
        ),
    },
    FrameworkKind.SVELTEKIT: {
        RequiredPage.PRIVACY: ("src/routes/privacy/+page.svelte",),
        RequiredPage.TERMS: ("src/routes/terms/+page.svelte",),
        RequiredPage.ACCESSIBILITY: ("src/routes/accessibility/+page.svelte",),
    },
    FrameworkKind.ASTRO: {
        RequiredPage.PRIVACY: ("src/pages/privacy.astro",),
        RequiredPage.TERMS: ("src/pages/terms.astro",),
        RequiredPage.ACCESSIBILITY: ("src/pages/accessibility.astro",),
    },
    FrameworkKind.VITE: {
        RequiredPage.PRIVACY: ("src/pages/Privacy.jsx", "src/pages/Privacy.tsx"),
        RequiredPage.TERMS: ("src/pages/Terms.jsx", "src/pages/Terms.tsx"),
        RequiredPage.ACCESSIBILITY: (
            "src/pages/Accessibility.jsx",
            "src/pages/Accessibility.tsx",
        ),
    },
}

# Config-based routers: one file whose text is sniffed for the page slug.
_CONTENT_ROUTE_FILES: dict[FrameworkKind, str] = {
    FrameworkKind.DJANGO: "urls.py",
    FrameworkKind.FLASK: "app.py",
    FrameworkKind.FASTAPI: "main.py",
    FrameworkKind.RAILS: "config/routes.rb",
    FrameworkKind.LARAVEL: "routes/web.php",
}


def _file_route_present(root: Path, kind: FrameworkKind, page: RequiredPage) -> bool:
    """True if `root` has one of `kind`'s known page-file candidates for `page`.

    frob:ticket T-5360
    """
    candidates = _FILE_ROUTE_CANDIDATES.get(kind, {}).get(page, ())
    return any((root / candidate).exists() for candidate in candidates)


def _content_route_present(root: Path, kind: FrameworkKind, page: RequiredPage) -> bool:
    """True if `kind`'s single route-config file exists under `root` and
    mentions `page`'s slug.

    frob:ticket T-5360
    """
    route_file = _CONTENT_ROUTE_FILES.get(kind)
    if route_file is None:
        return False
    return page.value in _read_text(root / route_file)


# frob:doc docs/modules/webapp-comply.md#detect_required_pages
def detect_required_pages(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> Result[frozenset[RequiredPage], ComplyScanError]:
    """Check `root` for the privacy/terms/accessibility pages, keyed off
    the already-detected `frameworks` (from `detect_frameworks`, T-5302)
    -- this function never re-detects frameworks itself.

    Returns `Err(ComplyScanError.ROOT_NOT_READABLE)` if `root` is not a
    listable directory (permission denied, or not a directory at all);
    every other case -- including no frameworks detected -- returns
    `Ok` with whatever pages were found present (possibly empty).

    frob:ticket T-5360
    """
    if not root.is_dir():
        _log.debug("detect_required_pages: %s is not a readable directory", root)
        return Err(ComplyScanError.ROOT_NOT_READABLE)

    present: set[RequiredPage] = set()
    for kind in frameworks:
        for page in RequiredPage:
            if _file_route_present(root, kind, page) or _content_route_present(
                root, kind, page
            ):
                present.add(page)
                _log.debug(
                    "detect_required_pages: %s present at %s (via %s)", page, root, kind
                )
    return Ok(frozenset(present))
