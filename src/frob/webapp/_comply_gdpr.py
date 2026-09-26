"""COMPLY109-116: GDPR and international disclosures (docs/modules/
webapp-comply-gdpr.md, T-5373, the `T-5140`/T-5145 web-app-lint epic's
GDPR/international leaf, blocked_by=['T-5360']).

Builds on `frob.webapp._comply_substrate` (T-5360, docs/modules/
webapp-comply.md) for the two questions that substrate already answers
-- "does this repo's manifest imply a GDPR-relevant behavior at all"
(`detect_signals`, any non-empty `ComplySignal` set) and, for the two
signal-gated rules, the specific `ai_on_user_data`/`sms` signals -- and
never re-implements either. Unlike T-5372's `_comply_privacy` leaf,
this module does not need a single "the privacy page" candidate file:
every rule here scans the WHOLE tracked-doc corpus (or, for COMPLY112,
every tracked `.sql` migration), the same "site-wide" posture several
non-page-specific WEBSEC leaves already use, since a GDPR disclosure can
legitimately live on any page (privacy policy, terms, a dedicated
/data-rights page) rather than one canonical file.

EIGHT RULE IDS (T-5301's reserved `COMPLY109`-`COMPLY116` block, the
ticket body's GDPR/international corpus):

- COMPLY109: no DSAR-response-SLA text anywhere in the tracked doc
  corpus (GDPR Art.12(3): a one-month/30-day response commitment near a
  "request" mention).
- COMPLY110: the tracked doc corpus is missing one or more of "data
  controller", "legal basis", "retention" (GDPR Art.13's
  identity/legal-basis/retention-period disclosure triad).
- COMPLY111: no right-to-erasure-shaped route/handler anywhere in the
  tracked source (GDPR Art.17) -- an erasure/delete-account endpoint.
- COMPLY112: a tracked `.sql` migration `CREATE TABLE` referencing a
  PII-shaped column (email/ssn/phone/address) with no expiry/TTL/
  retention keyword anywhere in that same migration file (GDPR
  Art.5(1)(e), storage limitation). The ticket body names a "5148-4"
  migration-scan helper to reuse for this check; as of this leaf no
  such helper exists anywhere in the tree (T-5148-4 is not a filed
  ticket and no migration-scan module exists under `frob.webapp`/
  `frob.sql`) -- this rule ships its own small self-contained migration
  text scan instead of blocking on a helper that was never built, and
  the gap is filed as follow-up scope (see the Done report).
- COMPLY113: a tracked datastore-provisioning file (`.tf`/`docker-
  compose.yml`/`settings.py` mentioning `postgres`/`DATABASES`) with no
  "encrypt" keyword anywhere in that same file (encryption-at-rest
  config, GDPR Art.32).
- COMPLY114: no tracked file whose NAME (not just content) suggests a
  breach-notification runbook ("SECURITY"/"incident"/"breach") exists
  anywhere in the repo (GDPR Art.33/34 breach-notification readiness).
- COMPLY115: `ComplySignal.AI_ON_USER_DATA` detected but no AI-
  disclosure-shaped text anywhere in the tracked doc corpus (EU AI Act
  Art.50 chatbot-transparency notice).
- COMPLY116: `ComplySignal.SMS` detected but no consent-capture-shaped
  text anywhere in the tracked doc corpus (CASL/TCPA consent-to-text
  requirement).

FRAMEWORK GATING (T-5302): same short-circuit posture every WEBSEC/
COMPLY/A11Y/SEO/WEBPERF family uses -- `frob.webapp._detect.
detect_frameworks(root)` empty means no scan at all.

WIRING: `frob.webapp._comply_substrate`'s own doc (docs/modules/
webapp-comply.md) defines no comply-specific gate-discovery hook or
convention of its own. T-5372's `_comply_privacy` leaf (landing
concurrently with this one) already established the precedent of
reusing `frob.gates._taint_gate`'s existing WEBSEC discovery CONVENTION
rather than inventing a new one: `websec_findings(root, frameworks) ->
tuple[Violation, ...]`, the exact signature T-5308's
`_discover_websec_hook_modules` already expects, over a discovery
prefix T-5372 widens from `_websec_` to also match `_comply_`. This
leaf follows the SAME convention and does NOT re-touch
`_taint_gate.py`'s prefix widening itself (T-5372 already owns that
edit, out of this leaf's own declared scope) -- this hook is written to
the discovered shape and becomes live the moment T-5372's widening is
on `dev` (T-5372 and T-5373 land independently; whichever lands second
picks up the other's change via the normal dev merge).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from frob.excludes import iter_files
from frob.findings import Severity, Violation
from frob.logging import get_logger
from frob.webapp._comply_substrate import ComplySignal, detect_signals
from frob.webapp._detect import FrameworkKind, detect_frameworks

_log = get_logger(__name__)

__all__ = [
    "ComplyGdprFinding",
    "comply_gdpr_findings",
    "websec_findings",
]


# frob:doc docs/modules/webapp-comply-gdpr.md#public-api
@dataclass(frozen=True)
class ComplyGdprFinding:
    """One COMPLY109-116 finding: a GDPR/international-disclosure gap.

    frob:ticket T-5373
    """

    rule: str
    file: str
    line: int
    message: str


_DOC_SUFFIXES = (".md", ".mdx", ".html", ".htm")

_DSAR_SLA_RE = re.compile(
    r"(?:30[\s-]days?|one[\s-]month)[^\n]{0,80}\brequest\b|"
    r"\brequest\b[^\n]{0,80}(?:30[\s-]days?|one[\s-]month)",
    re.IGNORECASE,
)

_ART13_KEYWORDS = ("data controller", "legal basis", "retention")

_ERASURE_ROUTE_RE = re.compile(
    r"delete[-_]account|erasure|gdpr[-_/]delete|right[-_]to[-_]be[-_]forgotten",
    re.IGNORECASE,
)

_CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\S+)\s*\(([^;]*)\)",
    re.IGNORECASE | re.DOTALL,
)
_PII_COLUMN_RE = re.compile(r"\b(email|ssn|phone|address)\b", re.IGNORECASE)
_RETENTION_KEYWORD_RE = re.compile(r"expir|ttl|retention", re.IGNORECASE)

_DATASTORE_CONFIG_RE = re.compile(r"postgres|DATABASES\s*=", re.IGNORECASE)
_ENCRYPT_KEYWORD_RE = re.compile(r"encrypt", re.IGNORECASE)

_RUNBOOK_NAME_RE = re.compile(r"security|incident|breach", re.IGNORECASE)

_AI_DISCLOSURE_RE = re.compile(
    r"you(?:'re| are) (?:chatting|talking) with an ai|ai[\s-]generated|"
    r"artificial intelligence assistant",
    re.IGNORECASE,
)

_SMS_CONSENT_RE = re.compile(
    r"consent[^\n]{0,60}(?:sms|text message)|(?:sms|text message)[^\n]{0,60}consent",
    re.IGNORECASE,
)


def _tracked_doc_text(root: Path) -> str:
    """Every tracked `.md`/`.mdx`/`.html`/`.htm` file's text under `root`,
    concatenated -- the "site-wide tracked doc corpus" every text-
    presence rule in this module scans.

    frob:ticket T-5373
    """
    parts: list[str] = []
    for path in iter_files(root):
        if path.suffix.lower() not in _DOC_SUFFIXES:
            continue
        try:
            parts.append(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    return "\n".join(parts)


def _dsar_sla_findings(doc_text: str, root: Path) -> list[ComplyGdprFinding]:
    """COMPLY109: no DSAR-response-SLA text anywhere in the tracked doc
    corpus.

    frob:ticket T-5373
    """
    if _DSAR_SLA_RE.search(doc_text):
        return []
    return [
        ComplyGdprFinding(
            rule="COMPLY109",
            file=".",
            line=1,
            message=(
                "COMPLY109: no data-subject-access-request response-SLA "
                "text (GDPR Art.12(3) requires a one-month response "
                "commitment) found anywhere in the tracked doc corpus. "
                "Publish the SLA, or "
                '`frob:waive COMPLY109 reason="..."` with a real '
                "justification"
            ),
        )
    ]


def _art13_findings(doc_text: str, root: Path) -> list[ComplyGdprFinding]:
    """COMPLY110: the tracked doc corpus is missing one or more of the
    Art.13 identity/legal-basis/retention triad.

    frob:ticket T-5373
    """
    lowered = doc_text.lower()
    missing = [kw for kw in _ART13_KEYWORDS if kw not in lowered]
    if not missing:
        return []
    return [
        ComplyGdprFinding(
            rule="COMPLY110",
            file=".",
            line=1,
            message=(
                f"COMPLY110: the tracked doc corpus is missing "
                f"{', '.join(missing)!r} (GDPR Art.13's identity/legal-"
                f"basis/retention-period disclosure triad). Add the "
                f"missing section(s), or `frob:waive COMPLY110 reason="
                f'"..."` with a real justification'
            ),
        )
    ]


def _erasure_endpoint_findings(root: Path) -> list[ComplyGdprFinding]:
    """COMPLY111: no right-to-erasure-shaped route/handler anywhere in
    the tracked source.

    frob:ticket T-5373
    """
    for path in iter_files(root):
        if path.suffix.lower() not in (".py", ".js", ".jsx", ".ts", ".tsx", ".rb"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if _ERASURE_ROUTE_RE.search(text):
            return []
    return [
        ComplyGdprFinding(
            rule="COMPLY111",
            file=".",
            line=1,
            message=(
                "COMPLY111: no right-to-erasure-shaped route/handler "
                "(GDPR Art.17) found anywhere in the tracked source. Add "
                "a delete-account/erasure endpoint, or "
                '`frob:waive COMPLY111 reason="..."` with a real '
                "justification"
            ),
        )
    ]


def _storage_limitation_findings(root: Path) -> list[ComplyGdprFinding]:
    """COMPLY112: a `CREATE TABLE` referencing a PII-shaped column with
    no expiry/TTL/retention keyword anywhere in that same migration
    file.

    frob:ticket T-5373
    """
    findings: list[ComplyGdprFinding] = []
    for path in iter_files(root):
        if path.suffix.lower() != ".sql":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if _RETENTION_KEYWORD_RE.search(text):
            continue
        rel_path = path.relative_to(root).as_posix()
        for match in _CREATE_TABLE_RE.finditer(text):
            table, body = match.group(1), match.group(2)
            if not _PII_COLUMN_RE.search(body):
                continue
            line = text.count("\n", 0, match.start()) + 1
            findings.append(
                ComplyGdprFinding(
                    rule="COMPLY112",
                    file=rel_path,
                    line=line,
                    message=(
                        f"COMPLY112: {rel_path}:{line} table {table!r} "
                        f"has a PII-shaped column but no expiry/TTL/"
                        f"retention keyword anywhere in this migration "
                        f"(GDPR Art.5(1)(e), storage limitation). Add a "
                        f"retention/TTL column or policy, or "
                        f'`frob:waive COMPLY112 reason="..."` with a '
                        f"real justification"
                    ),
                )
            )
    return findings


def _encryption_at_rest_findings(root: Path) -> list[ComplyGdprFinding]:
    """COMPLY113: a datastore-provisioning file with no "encrypt"
    keyword anywhere in that same file.

    frob:ticket T-5373
    """
    findings: list[ComplyGdprFinding] = []
    for path in iter_files(root):
        if path.suffix.lower() not in (".tf", ".yml", ".yaml", ".py"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if not _DATASTORE_CONFIG_RE.search(text):
            continue
        if _ENCRYPT_KEYWORD_RE.search(text):
            continue
        rel_path = path.relative_to(root).as_posix()
        findings.append(
            ComplyGdprFinding(
                rule="COMPLY113",
                file=rel_path,
                line=1,
                message=(
                    f"COMPLY113: {rel_path}:1 a datastore-provisioning "
                    f"file has no encryption-at-rest keyword anywhere "
                    f"(GDPR Art.32). Enable encryption at rest, or "
                    f'`frob:waive COMPLY113 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _breach_runbook_findings(root: Path) -> list[ComplyGdprFinding]:
    """COMPLY114: no tracked file whose NAME suggests a breach-
    notification runbook exists anywhere in the repo.

    frob:ticket T-5373
    """
    for path in iter_files(root):
        if _RUNBOOK_NAME_RE.search(path.name):
            return []
    return [
        ComplyGdprFinding(
            rule="COMPLY114",
            file=".",
            line=1,
            message=(
                "COMPLY114: no breach-notification-runbook-shaped file "
                "(GDPR Art.33/34) found anywhere in the repo. Add a "
                "SECURITY.md/incident-response runbook, or "
                '`frob:waive COMPLY114 reason="..."` with a real '
                "justification"
            ),
        )
    ]


def _ai_act_disclosure_findings(
    doc_text: str, signals: frozenset[ComplySignal]
) -> list[ComplyGdprFinding]:
    """COMPLY115: `ai_on_user_data` detected but no AI-disclosure-shaped
    text anywhere in the tracked doc corpus.

    frob:ticket T-5373
    """
    if ComplySignal.AI_ON_USER_DATA not in signals:
        return []
    if _AI_DISCLOSURE_RE.search(doc_text):
        return []
    return [
        ComplyGdprFinding(
            rule="COMPLY115",
            file=".",
            line=1,
            message=(
                "COMPLY115: AI-on-user-data is detected but no AI-"
                "disclosure-shaped text (EU AI Act Art.50 chatbot-"
                "transparency notice) was found anywhere in the tracked "
                "doc corpus. Add the disclosure, or "
                '`frob:waive COMPLY115 reason="..."` with a real '
                "justification"
            ),
        )
    ]


def _sms_consent_findings(
    doc_text: str, signals: frozenset[ComplySignal]
) -> list[ComplyGdprFinding]:
    """COMPLY116: `sms` detected but no consent-capture-shaped text
    anywhere in the tracked doc corpus.

    frob:ticket T-5373
    """
    if ComplySignal.SMS not in signals:
        return []
    if _SMS_CONSENT_RE.search(doc_text):
        return []
    return [
        ComplyGdprFinding(
            rule="COMPLY116",
            file=".",
            line=1,
            message=(
                "COMPLY116: SMS is detected but no consent-capture-"
                "shaped text (CASL/TCPA consent-to-text requirement) "
                "was found anywhere in the tracked doc corpus. Add "
                "consent-capture text, or "
                '`frob:waive COMPLY116 reason="..."` with a real '
                "justification"
            ),
        )
    ]


# frob:doc docs/modules/webapp-comply-gdpr.md#public-api
# frob:ticket T-5373
def comply_gdpr_findings(root: Path) -> tuple[ComplyGdprFinding, ...]:
    """COMPLY109-116: every GDPR/international-disclosure finding under
    `root`.

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all (T-5302's own contract, the same
    posture every WEBSEC/COMPLY family in this epic follows), and again
    when `frob.webapp._comply_substrate.detect_signals` reports no
    GDPR-relevant signal at all (a plain repo with no email collection,
    AI-on-user-data, subscriptions, data-sale-or-share, SMS, session-
    replay-or-pixel, or health-data behavior has nothing this module is
    relevant to).

    frob:ticket T-5373
    """
    root = Path(root)
    if not detect_frameworks(root):
        _log.debug("comply_gdpr: no framework detected at %s, skipping scan", root)
        return ()
    signals = detect_signals(root)
    if not signals:
        _log.debug("comply_gdpr: no GDPR-relevant signal at %s, skipping scan", root)
        return ()

    doc_text = _tracked_doc_text(root)
    findings: list[ComplyGdprFinding] = []
    findings.extend(_dsar_sla_findings(doc_text, root))
    findings.extend(_art13_findings(doc_text, root))
    findings.extend(_erasure_endpoint_findings(root))
    findings.extend(_storage_limitation_findings(root))
    findings.extend(_encryption_at_rest_findings(root))
    findings.extend(_breach_runbook_findings(root))
    findings.extend(_ai_act_disclosure_findings(doc_text, signals))
    findings.extend(_sms_consent_findings(doc_text, signals))

    _log.info("comply_gdpr: %d finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/webapp-comply-gdpr.md#public-api
# frob:ticket T-5373
def websec_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """`frob.gates._taint_gate.taint_gate`'s hook-discovery contract
    (T-5308's `websec_findings`-shaped signature, reused by this COMPLY
    leaf per T-5372's own precedent since `frob.webapp._comply_substrate`
    defines no comply-specific hook convention of its own yet).
    `frameworks` is the caller's own already-computed
    `detect_frameworks(root)` result -- an empty set short-circuits to
    `()` exactly like `comply_gdpr_findings`'s own direct-call contract.

    frob:ticket T-5373
    """
    if not frameworks:
        _log.debug(
            "comply_gdpr: no framework detected at %s, skipping scan (hook)", root
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
        for finding in comply_gdpr_findings(root)
    )
