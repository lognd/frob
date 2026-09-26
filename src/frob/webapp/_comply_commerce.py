"""COMPLY123-127: subscription/cancellation/commerce dark patterns
(docs/modules/webapp-comply-commerce.md, T-5363, the `T-5140`/T-5145
web-app-lint epic's commerce leaf, blocked_by=['T-5360']).

Builds on `frob.webapp._comply_substrate` (T-5360, docs/modules/
webapp-comply.md) for `detect_signals`'s `ComplySignal.SUBSCRIPTIONS`/
`ComplySignal.EMAIL_COLLECTION` manifest signals and never re-implements
manifest sniffing. The substrate has no route-table or email-template
content API at all (its own `RequiredPage` union is privacy/terms/
accessibility only), so this module's own tracked-file text scans for
route strings and email templates are new work, not a re-implementation
of anything the substrate already owns.

Stripe webhook SIGNATURE verification is explicitly OUT of this leaf's
corpus -- T-5144-3 (WEBSEC config/headers) owns that check; this module
never duplicates it, per the ticket body's own cross-reference.

FIVE RULE IDS (T-5301's reserved `COMPLY123`-`COMPLY127` block, the
ticket body's 16 CFR 425 / CAN-SPAM / PCI-SAQ-A-shaped corpus):

- COMPLY123: a subscribe/checkout route exists but no cancel-shaped
  route exists anywhere in the route table at all (16 CFR 425
  click-to-cancel: a "Negative Option Rule" cancellation mechanism must
  exist).
- COMPLY124: both exist, but the shallowest cancel route's path is
  DEEPER (more `/`-segments) than the shallowest subscribe/checkout
  route's path -- a proxy for 16 CFR 425's equal-prominence/
  simplicity-of-cancellation requirement (canceling must not take more
  steps than signing up).
- COMPLY125: `ComplySignal.EMAIL_COLLECTION` or `ComplySignal.
  SUBSCRIPTIONS` detected, and an email-template-shaped tracked file
  exists, but none has an unsubscribe-shaped link (CAN-SPAM 15 U.S.C.
  7704(a)(3)/(5)).
- COMPLY126: same gating, but no email template has a postal-address-
  shaped line (CAN-SPAM 15 U.S.C. 7704(a)(5)).
- COMPLY127: `ComplySignal.SUBSCRIPTIONS` detected and a raw
  card-number/CVV form field is found in app code with no Stripe/
  hosted-checkout-element marker in the same file -- a PCI SAQ-A scope
  proxy (SAQ-A's whole premise is that raw cardholder data never
  touches the merchant's own form fields; a bare `name="card_number"`
  input is the shape that widens PCI scope past SAQ-A).

FRAMEWORK GATING (T-5302): same short-circuit posture every WEBSEC/
COMPLY/A11Y/SEO/WEBPERF family uses -- `frob.webapp._detect.
detect_frameworks(root)` empty means no scan at all.

WIRING: `websec_findings(root, frameworks) -> tuple[Violation, ...]` --
T-5372's own `frob.webapp._comply_privacy` leaf already widened
`frob.gates._taint_gate`'s discovery prefix from `_websec_` alone to
also match `_comply_*` modules (docs/modules/webapp-comply-privacy.md),
so this sibling leaf needs no further `_taint_gate.py` edit -- it is
discovered automatically, same hook shape, same discovery mechanism.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from frob.findings import Severity, Violation
from frob.gitio import run_argv
from frob.logging import get_logger
from frob.webapp._comply_substrate import ComplySignal, detect_signals
from frob.webapp._detect import FrameworkKind, detect_frameworks

_log = get_logger(__name__)

__all__ = [
    "ComplyCommerceFinding",
    "comply_commerce_findings",
    "websec_findings",
]

#: Tracked-file extensions scanned for route-table strings and email-
#: template content -- app code (route decorators) plus templates.
_ROUTE_EXTENSIONS = (".py", ".js", ".jsx", ".ts", ".tsx", ".rb", ".php")
_TEMPLATE_EXTENSIONS = (".html", ".htm", ".mjml", ".txt", ".eml")

#: Quoted-path-literal extraction: any `"/..."`/`'/...'` string, the
#: same "plain-text scan, not a route-framework AST" posture every
#: sibling WEBSEC/COMPLY text-lint module uses.
_PATH_LITERAL_RE = re.compile(r"""["'](/[a-zA-Z0-9/_\-]*)["']""")

_SUBSCRIBE_PATH_RE = re.compile(r"subscribe|checkout", re.IGNORECASE)
_CANCEL_PATH_RE = re.compile(r"cancel", re.IGNORECASE)

#: An "email template"-shaped file: name/path mentions email/newsletter,
#: or lives under a templates/emails-shaped directory -- a v1 heuristic
#: (disclosed, same posture every sibling text-lint module uses), not a
#: claim of exhaustively finding every transactional email template.
_EMAIL_TEMPLATE_PATH_RE = re.compile(r"(email|newsletter|mailer)", re.IGNORECASE)

_UNSUBSCRIBE_RE = re.compile(r"unsubscribe", re.IGNORECASE)

#: A postal-address-shaped line: a leading street number, a street-type
#: word, and a 5-digit ZIP somewhere on the same line -- a shallow shape
#: match, not a full address parser.
_POSTAL_ADDRESS_RE = re.compile(
    r"\d{1,6}\s+[A-Za-z0-9.,'\s]*"
    r"(Street|St\.?|Avenue|Ave\.?|Boulevard|Blvd\.?|Road|Rd\.?|Drive|Dr\.?|"
    r"Lane|Ln\.?|Way|Suite|Ste\.?)\b[^\n]*\b\d{5}(-\d{4})?\b",
    re.IGNORECASE,
)

#: A raw cardholder-data form field -- the PCI SAQ-A scope-widening
#: shape (a merchant form field literally named for card data, rather
#: than a hosted/tokenized element).
_RAW_CARD_FIELD_RE = re.compile(
    r"""name\s*=\s*["'](?:card[_-]?number|cc[_-]?number|card[_-]?cvv|cvv)["']""",
    re.IGNORECASE,
)

#: Markers indicating the card field is inside a hosted/tokenized
#: Stripe/PCI-SAQ-A-safe checkout flow -- their presence in the SAME
#: file clears an otherwise-tainted raw-field match.
_HOSTED_CHECKOUT_MARKER_RE = re.compile(
    r"stripe\.js|elements\.create|checkout\.session|stripe-elements|"
    r"Stripe\(",
    re.IGNORECASE,
)


# frob:doc docs/modules/webapp-comply-commerce.md#public-api
# frob:tests \
# tests/unit/test_webapp_comply_commerce.py::test_comply_commerce_findings_fixture[no_cancel_route-COMPLY123-True] kind="unit"  # noqa: E501
@dataclass(frozen=True)
class ComplyCommerceFinding:
    """One COMPLY123-127 finding: a subscription/cancellation/commerce
    dark-pattern rule id, the file and line the evidence (or its
    absence) came from, and a human message.

    frob:ticket T-5363
    """

    rule: str
    file: str
    line: int
    message: str


def _tracked_files(root: Path, *suffixes: str) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `suffixes`, root-relative
    POSIX paths, `()` on any git failure -- mirrors `_websec_headers_log.
    _tracked_files`'s own tracked-file-scan shape (an intentional own
    tiny copy, not a cross-module private import; see this module's
    docstring).

    frob:ticket T-5363
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("comply_commerce: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("comply_commerce: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(suffixes)
    )


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable.

    frob:ticket T-5363
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _line_of(text: str, offset: int) -> int:
    """1-based line number of char `offset` in `text`.

    frob:ticket T-5363
    """
    return text.count("\n", 0, offset) + 1


def _path_depth(path_literal: str) -> int:
    """Number of non-empty `/`-segments in `path_literal` -- the
    click-to-cancel equal-prominence proxy metric (COMPLY124).

    frob:ticket T-5363
    """
    return len([seg for seg in path_literal.split("/") if seg])


def _route_findings(root: Path) -> list[ComplyCommerceFinding]:
    """COMPLY123 (no cancel route at all) / COMPLY124 (cancel route
    deeper than the shallowest subscribe/checkout route).

    frob:ticket T-5363
    """
    subscribe_hits: list[tuple[str, int, str]] = []
    cancel_hits: list[tuple[str, int, str]] = []
    for rel in _tracked_files(root, *_ROUTE_EXTENSIONS):
        text = _read_text(root / rel)
        for match in _PATH_LITERAL_RE.finditer(text):
            path_literal = match.group(1)
            line = _line_of(text, match.start())
            if _SUBSCRIBE_PATH_RE.search(path_literal):
                subscribe_hits.append((rel, line, path_literal))
            elif _CANCEL_PATH_RE.search(path_literal):
                cancel_hits.append((rel, line, path_literal))

    if not subscribe_hits:
        return []

    shallowest_subscribe = min(subscribe_hits, key=lambda hit: _path_depth(hit[2]))
    if not cancel_hits:
        rel, line, path_literal = shallowest_subscribe
        return [
            ComplyCommerceFinding(
                rule="COMPLY123",
                file=rel,
                line=line,
                message=(
                    f"COMPLY123: {rel}:{line} a subscribe/checkout route "
                    f"({path_literal!r}) exists but no cancel-shaped route "
                    "exists anywhere -- 16 CFR 425 (click-to-cancel) "
                    "requires an online cancellation mechanism. Add a "
                    'cancel route, or `frob:waive COMPLY123 reason="..."` '
                    "with a real justification"
                ),
            )
        ]

    shallowest_cancel = min(cancel_hits, key=lambda hit: _path_depth(hit[2]))
    if _path_depth(shallowest_cancel[2]) <= _path_depth(shallowest_subscribe[2]):
        return []
    rel, line, path_literal = shallowest_cancel
    subscribe_literal = shallowest_subscribe[2]
    return [
        ComplyCommerceFinding(
            rule="COMPLY124",
            file=rel,
            line=line,
            message=(
                f"COMPLY124: {rel}:{line} the shallowest cancel route "
                f"({path_literal!r}) is deeper than the shallowest "
                f"subscribe/checkout route ({subscribe_literal!r}) -- 16 "
                "CFR 425 requires cancellation to be at least as simple "
                "as signing up. Flatten the cancel path, or `frob:waive "
                'COMPLY124 reason="..."` with a real justification'
            ),
        )
    ]


def _email_template_files(root: Path) -> tuple[str, ...]:
    """Every tracked `_TEMPLATE_EXTENSIONS` file whose path looks like an
    email template (`_EMAIL_TEMPLATE_PATH_RE`).

    frob:ticket T-5363
    """
    return tuple(
        rel
        for rel in _tracked_files(root, *_TEMPLATE_EXTENSIONS)
        if _EMAIL_TEMPLATE_PATH_RE.search(rel)
    )


def _email_template_findings(
    root: Path, signals: frozenset[ComplySignal]
) -> list[ComplyCommerceFinding]:
    """COMPLY125 (no unsubscribe link) / COMPLY126 (no postal address),
    gated on `EMAIL_COLLECTION`/`SUBSCRIPTIONS` and an email template
    actually existing.

    frob:ticket T-5363
    """
    if not (
        ComplySignal.EMAIL_COLLECTION in signals
        or ComplySignal.SUBSCRIPTIONS in signals
    ):
        return []
    templates = _email_template_files(root)
    if not templates:
        return []

    has_unsubscribe = False
    has_postal_address = False
    for rel in templates:
        text = _read_text(root / rel)
        if _UNSUBSCRIBE_RE.search(text):
            has_unsubscribe = True
        if _POSTAL_ADDRESS_RE.search(text):
            has_postal_address = True

    findings: list[ComplyCommerceFinding] = []
    first_template = templates[0]
    if not has_unsubscribe:
        findings.append(
            ComplyCommerceFinding(
                rule="COMPLY125",
                file=first_template,
                line=1,
                message=(
                    f"COMPLY125: no email template under {first_template} "
                    "or its siblings has an unsubscribe-shaped link -- "
                    "CAN-SPAM 15 U.S.C. 7704(a)(3)/(5) requires one. Add "
                    "an unsubscribe link, or `frob:waive COMPLY125 "
                    'reason="..."` with a real justification'
                ),
            )
        )
    if not has_postal_address:
        findings.append(
            ComplyCommerceFinding(
                rule="COMPLY126",
                file=first_template,
                line=1,
                message=(
                    f"COMPLY126: no email template under {first_template} "
                    "or its siblings has a postal-address-shaped line -- "
                    "CAN-SPAM 15 U.S.C. 7704(a)(5) requires a valid "
                    "physical postal address. Add one, or `frob:waive "
                    'COMPLY126 reason="..."` with a real justification'
                ),
            )
        )
    return findings


def _pci_saq_a_findings(
    root: Path, signals: frozenset[ComplySignal]
) -> list[ComplyCommerceFinding]:
    """COMPLY127: a raw cardholder-data form field with no hosted-
    checkout marker in the same file, gated on `ComplySignal.
    SUBSCRIPTIONS`.

    frob:ticket T-5363
    """
    if ComplySignal.SUBSCRIPTIONS not in signals:
        return []
    findings: list[ComplyCommerceFinding] = []
    for rel in _tracked_files(root, *_ROUTE_EXTENSIONS, ".html", ".htm"):
        text = _read_text(root / rel)
        match = _RAW_CARD_FIELD_RE.search(text)
        if match is None:
            continue
        if _HOSTED_CHECKOUT_MARKER_RE.search(text):
            continue
        line = _line_of(text, match.start())
        findings.append(
            ComplyCommerceFinding(
                rule="COMPLY127",
                file=rel,
                line=line,
                message=(
                    f"COMPLY127: {rel}:{line} a raw cardholder-data form "
                    "field is present with no Stripe/hosted-checkout "
                    "element marker in the same file -- widens PCI scope "
                    "past SAQ-A (cardholder data should never touch the "
                    "merchant's own form fields). Route the field "
                    "through a hosted/tokenized checkout element, or "
                    '`frob:waive COMPLY127 reason="..."` with a real '
                    "justification"
                ),
            )
        )
    return findings


# frob:doc docs/modules/webapp-comply-commerce.md#public-api
# frob:ticket T-5363
def comply_commerce_findings(root: Path) -> tuple[ComplyCommerceFinding, ...]:
    """COMPLY123-127: every subscription/cancellation/commerce
    dark-pattern finding under `root`.

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all (T-5302's contract, same posture
    every sibling WEBSEC/COMPLY family follows).

    frob:ticket T-5363
    """
    root = Path(root)
    if not detect_frameworks(root):
        _log.debug("comply_commerce: no framework detected at %s, skipping scan", root)
        return ()

    signals = detect_signals(root)
    findings: list[ComplyCommerceFinding] = []
    findings.extend(_route_findings(root))
    findings.extend(_email_template_findings(root, signals))
    findings.extend(_pci_saq_a_findings(root, signals))

    _log.info("comply_commerce: %d finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/webapp-comply-commerce.md#public-api
# frob:ticket T-5363
def websec_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """`frob.gates._taint_gate.taint_gate`'s hook-discovery contract
    (T-5308's `websec_findings`-shaped signature; T-5372 already widened
    the gate's discovery prefix to `_comply_*`, so this sibling leaf
    needs no further gate edit). `frameworks` is the caller's own
    already-computed `detect_frameworks(root)` result -- an empty set
    short-circuits to `()` exactly like `comply_commerce_findings`'s own
    direct-call contract.

    frob:ticket T-5363
    """
    if not frameworks:
        _log.debug(
            "comply_commerce: no framework detected at %s, skipping scan (hook)", root
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
        for finding in comply_commerce_findings(root)
    )
