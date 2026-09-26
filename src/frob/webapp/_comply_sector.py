"""COMPLY117-122: sector-specific applicability-flag-gated compliance
(docs/modules/webapp-comply-sector.md, T-5370, the `T-5140`/T-5145
web-app-lint epic's HIPAA/GLBA/COPPA/FERPA leaf, blocked_by=['T-5360']).

Builds on `frob.webapp._comply_substrate` (T-5360, docs/modules/
webapp-comply.md) for the one question it already answers this module
needs -- COMPLY120 (HIPAA administrative policies: a written,
version-controlled privacy-policies document) reuses
`detect_required_pages`'s `RequiredPage.PRIVACY` rather than
re-implementing page discovery, the same "ask the substrate, don't
re-detect" posture `frob.webapp._comply_privacy` (T-5372) already
follows for its own COMPLY101.

APPLICABILITY FLAGS (ticket body: "ship as config-driven rules reading a
[comply] table in frob.toml the repo opts into, never inferred"): unlike
`_comply_privacy`'s `ComplySignal`-driven gating (a manifest-implied
behavior), every rule in this module reads an explicit boolean out of
`frob.toml`'s `[comply]` table -- `financial_institution`,
`hipaa_covered_entity`, `directed_to_children`, `edtech_student_data` --
and NEVER infers applicability from a manifest/signal scan the way
`detect_signals` does for other COMPLY leaves. A repo with no `[comply]`
table, an unreadable/malformed `frob.toml`, or every flag absent/false
is a MUST-STAY-QUIET control: `_read_sector_flags` returns every flag
`False`, and `comply_sector_findings` returns `()` before it even calls
`detect_frameworks` or touches git -- a sector rule that has not been
opted into must never fire, not even a WARN, no matter what the repo's
tracked tree contains.

SIX RULE IDS (T-5301's reserved `COMPLY117`-`COMPLY122` block, mapped
onto the T-5145 corpus's sector-specific items A14/A15/A16/A17/A18/26):

- COMPLY117: GLBA Privacy Rule notices (16 CFR Part 313, item A14) --
  `financial_institution` flag; no tracked doc mentions BOTH an
  "initial privacy notice" and an "annual privacy notice".
- COMPLY118: GLBA Safeguards Rule encryption/MFA (16 CFR 314.4(c)(3),
  (c)(5), item A15) -- `financial_institution` flag; no tracked file
  mentions both an at-rest encryption reference and a multi-factor-
  auth reference.
- COMPLY119: HIPAA technical safeguards (45 CFR 164.312, item A16) --
  `hipaa_covered_entity` flag; no tracked file mentions both an
  audit-log reference and a role-based-access-control reference for
  ePHI.
- COMPLY120: HIPAA administrative policies (45 CFR 164.530(i), item
  A17) -- `hipaa_covered_entity` flag; `detect_required_pages` reports
  no version-controlled privacy-policies document (`RequiredPage.
  PRIVACY` absent).
- COMPLY121: COPPA verifiable parental consent (16 CFR 312.5, item
  A18) -- `directed_to_children` flag; a registration/signup route
  handler with no parental-consent reference anywhere in its file.
- COMPLY122: FERPA for edtech (20 U.S.C. 1232g, item 26) --
  `edtech_student_data` flag; no tracked file mentions a data-sharing
  agreement covering student education records.

FRAMEWORK GATING (T-5302): same short-circuit posture every WEBSEC/
COMPLY/A11Y/SEO/WEBPERF family uses -- `frob.webapp._detect.
detect_frameworks(root)` empty means no scan at all, checked AFTER the
flag short-circuit above (a repo with every flag false never even
reaches this check).

WIRING: `frob.webapp._comply_substrate`'s own doc (docs/modules/
webapp-comply.md) defines no comply-specific gate-discovery hook or
convention. Per this leaf's own dispatch brief this module follows
`frob.gates._taint_gate`'s existing WEBSEC discovery CONVENTION instead
of inventing a new one: `websec_findings(root, frameworks) ->
tuple[Violation, ...]`, the exact signature T-5308's
`_discover_websec_hook_modules` already expects -- the same convention
`frob.webapp._comply_privacy` (T-5372) already adopted for the same
reason. T-5372 widened `_taint_gate.py`'s discovery module-basename
prefix from `_websec_` alone to also match `_comply_`, so this hook is
actually discovered and called once that leaf lands, not merely
convention-shaped -- see this leaf's own Done report for the exact
landing-order dependency the positive control below carries.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from frob.excludes import iter_files
from frob.findings import Severity, Violation
from frob.logging import get_logger
from frob.webapp._comply_substrate import RequiredPage, detect_required_pages
from frob.webapp._detect import FrameworkKind, detect_frameworks

_log = get_logger(__name__)

__all__ = [
    "ComplySectorFinding",
    "ComplySectorFlags",
    "comply_sector_findings",
    "websec_findings",
]


# frob:doc docs/modules/webapp-comply-sector.md#public-api
@dataclass(frozen=True)
class ComplySectorFinding:
    """One COMPLY117-122 finding: a sector-specific applicability-flag-
    gated compliance gap.

    frob:ticket T-5370
    """

    rule: str
    file: str
    line: int
    message: str


# frob:doc docs/modules/webapp-comply-sector.md#public-api
@dataclass(frozen=True)
class ComplySectorFlags:
    """The four `[comply]` table booleans `frob.toml` can opt a repo
    into -- every flag defaults `False` (MUST-STAY-QUIET, module
    docstring).

    frob:ticket T-5370
    """

    financial_institution: bool = False
    hipaa_covered_entity: bool = False
    directed_to_children: bool = False
    edtech_student_data: bool = False

    def any_set(self) -> bool:
        """True if at least one sector flag is opted in -- the one
        short-circuit condition `comply_sector_findings` checks before
        doing any other work.

        frob:ticket T-5370
        """
        return (
            self.financial_institution
            or self.hipaa_covered_entity
            or self.directed_to_children
            or self.edtech_student_data
        )


def _read_sector_flags(root: Path) -> ComplySectorFlags:
    """Read `root/frob.toml`'s `[comply]` table into `ComplySectorFlags`
    -- a missing file, unreadable file, malformed TOML, or missing
    `[comply]` table all resolve to every flag `False` (module
    docstring's MUST-STAY-QUIET contract), never an exception.

    frob:ticket T-5370
    """
    toml_path = root / "frob.toml"
    try:
        with toml_path.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.debug("comply_sector: no readable frob.toml at %s: %s", toml_path, exc)
        return ComplySectorFlags()

    comply_table = data.get("comply", {})
    if not isinstance(comply_table, dict):
        _log.debug("comply_sector: frob.toml [comply] is not a table, ignoring")
        return ComplySectorFlags()

    return ComplySectorFlags(
        financial_institution=bool(comply_table.get("financial_institution", False)),
        hipaa_covered_entity=bool(comply_table.get("hipaa_covered_entity", False)),
        directed_to_children=bool(comply_table.get("directed_to_children", False)),
        edtech_student_data=bool(comply_table.get("edtech_student_data", False)),
    )


def _tracked_text(root: Path) -> str:
    """Concatenated text of every git-tracked `.md`/`.txt`/`.py`/`.js`/
    `.ts` file under `root`, one `git ls-files` call via
    `frob.excludes.iter_files` (the shared tracked-file-walk helper
    every sibling WEBSEC/COMPLY module's own `_tracked_files` copy
    mirrors) -- these rules ask "does ANY tracked file mention X", not
    "which line", so one concatenated haystack is enough; each rule
    that DOES need a location falls back to `"<repo>"`/line 1 (the same
    repo-level-finding shape `_comply_privacy.comply_privacy_findings`
    uses for its own COMPLY101).

    frob:ticket T-5370
    """
    chunks: list[str] = []
    for suffix in (".md", ".txt", ".py", ".js", ".ts"):
        for path in iter_files(root, suffix=suffix):
            try:
                chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
    return "\n".join(chunks)


_INITIAL_NOTICE_RE = re.compile(r"initial\s+privacy\s+notice", re.IGNORECASE)
_ANNUAL_NOTICE_RE = re.compile(r"annual\s+privacy\s+notice", re.IGNORECASE)
_ENCRYPT_AT_REST_RE = re.compile(
    r"encrypt(?:ion|ed)?[^\n]{0,40}\bat[- ]rest\b", re.IGNORECASE
)
_MFA_RE = re.compile(r"\b(mfa|multi[- ]factor|two[- ]factor)\b", re.IGNORECASE)
_AUDIT_LOG_RE = re.compile(r"audit[- ]log", re.IGNORECASE)
_RBAC_RE = re.compile(r"\b(rbac|role[- ]based access control)\b", re.IGNORECASE)
_DATA_SHARING_AGREEMENT_RE = re.compile(
    r"data[- ]sharing agreement|school official exception", re.IGNORECASE
)
_REGISTRATION_HANDLER_RE = re.compile(
    r"\bdef\s+(register|signup|sign_up)\s*\(|\bfunction\s+(register|signUp|sign_up)\s*\("
)
_PARENTAL_CONSENT_RE = re.compile(
    r"parental[_ ]consent|parent[_ ]consent", re.IGNORECASE
)


def _glba_notice_findings(
    text: str, flags: ComplySectorFlags
) -> list[ComplySectorFinding]:
    """COMPLY117: GLBA Privacy Rule initial/annual notice templates.

    frob:ticket T-5370
    """
    if not flags.financial_institution:
        return []
    if _INITIAL_NOTICE_RE.search(text) and _ANNUAL_NOTICE_RE.search(text):
        return []
    return [
        ComplySectorFinding(
            rule="COMPLY117",
            file="<repo>",
            line=1,
            message=(
                "COMPLY117: financial_institution=true (frob.toml [comply]) "
                "but no tracked doc mentions both an initial privacy notice "
                "and an annual privacy notice -- GLBA Privacy Rule (16 CFR "
                "Part 313) requires both. Publish the notice templates, or "
                '`frob:waive COMPLY117 reason="..."` with a real '
                "justification"
            ),
        )
    ]


def _glba_safeguards_findings(
    text: str, flags: ComplySectorFlags
) -> list[ComplySectorFinding]:
    """COMPLY118: GLBA Safeguards Rule at-rest encryption + MFA.

    frob:ticket T-5370
    """
    if not flags.financial_institution:
        return []
    if _ENCRYPT_AT_REST_RE.search(text) and _MFA_RE.search(text):
        return []
    return [
        ComplySectorFinding(
            rule="COMPLY118",
            file="<repo>",
            line=1,
            message=(
                "COMPLY118: financial_institution=true (frob.toml [comply]) "
                "but no tracked file references both at-rest encryption and "
                "multi-factor authentication -- GLBA Safeguards Rule (16 "
                "CFR 314.4(c)(3), (c)(5)) requires both for customer "
                "information. Configure them, or `frob:waive COMPLY118 "
                'reason="..."` with a real justification'
            ),
        )
    ]


def _hipaa_technical_findings(
    text: str, flags: ComplySectorFlags
) -> list[ComplySectorFinding]:
    """COMPLY119: HIPAA technical safeguards -- audit logging + RBAC.

    frob:ticket T-5370
    """
    if not flags.hipaa_covered_entity:
        return []
    if _AUDIT_LOG_RE.search(text) and _RBAC_RE.search(text):
        return []
    return [
        ComplySectorFinding(
            rule="COMPLY119",
            file="<repo>",
            line=1,
            message=(
                "COMPLY119: hipaa_covered_entity=true (frob.toml [comply]) "
                "but no tracked file references both audit logging and "
                "role-based access control -- HIPAA technical safeguards "
                "(45 CFR 164.312(a),(b)) require both for ePHI systems. "
                'Add them, or `frob:waive COMPLY119 reason="..."` with a '
                "real justification"
            ),
        )
    ]


def _hipaa_administrative_findings(
    root: Path, frameworks: frozenset[FrameworkKind], flags: ComplySectorFlags
) -> list[ComplySectorFinding]:
    """COMPLY120: HIPAA administrative policies -- a written, version-
    controlled privacy-policies document, reusing `detect_required_pages`
    rather than re-detecting page presence (module docstring).

    frob:ticket T-5370
    """
    if not flags.hipaa_covered_entity:
        return []
    required_pages = detect_required_pages(root, frameworks)
    pages = frozenset() if required_pages.is_err else required_pages.danger_ok
    if RequiredPage.PRIVACY in pages:
        return []
    return [
        ComplySectorFinding(
            rule="COMPLY120",
            file="<repo>",
            line=1,
            message=(
                "COMPLY120: hipaa_covered_entity=true (frob.toml [comply]) "
                "but no version-controlled privacy-policies document was "
                "found -- HIPAA administrative policies (45 CFR "
                "164.530(i)) require one. Publish and track one, or "
                '`frob:waive COMPLY120 reason="..."` with a real '
                "justification"
            ),
        )
    ]


def _coppa_consent_findings(
    root: Path, flags: ComplySectorFlags
) -> list[ComplySectorFinding]:
    """COMPLY121: COPPA verifiable parental consent -- a registration/
    signup handler with no parental-consent reference in its own file.

    frob:ticket T-5370
    """
    if not flags.directed_to_children:
        return []
    findings: list[ComplySectorFinding] = []
    for suffix in (".py", ".js", ".ts"):
        for path in iter_files(root, suffix=suffix):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if not _REGISTRATION_HANDLER_RE.search(text):
                continue
            if _PARENTAL_CONSENT_RE.search(text):
                continue
            rel_path = path.relative_to(root).as_posix()
            findings.append(
                ComplySectorFinding(
                    rule="COMPLY121",
                    file=rel_path,
                    line=1,
                    message=(
                        f"COMPLY121: directed_to_children=true (frob.toml "
                        f"[comply]) and {rel_path} defines a registration/"
                        f"signup handler with no parental-consent "
                        f"reference -- COPPA (16 CFR 312.5(a)) requires "
                        f"verifiable parental consent before collecting "
                        f"personal information from children. Add a "
                        f"parental-consent gate, or `frob:waive COMPLY121 "
                        f'reason="..."` with a real justification'
                    ),
                )
            )
    return findings


def _ferpa_edtech_findings(
    text: str, flags: ComplySectorFlags
) -> list[ComplySectorFinding]:
    """COMPLY122: FERPA for edtech -- a signed data-sharing agreement on
    file for any vendor processing student education records.

    frob:ticket T-5370
    """
    if not flags.edtech_student_data:
        return []
    if _DATA_SHARING_AGREEMENT_RE.search(text):
        return []
    return [
        ComplySectorFinding(
            rule="COMPLY122",
            file="<repo>",
            line=1,
            message=(
                "COMPLY122: edtech_student_data=true (frob.toml [comply]) "
                "but no tracked doc references a data-sharing agreement/"
                "school-official exception -- FERPA (20 U.S.C. 1232g) "
                "requires one on file before an edtech vendor processes "
                "student education records. Record the agreement, or "
                '`frob:waive COMPLY122 reason="..."` with a real '
                "justification"
            ),
        )
    ]


# frob:doc docs/modules/webapp-comply-sector.md#public-api
# frob:ticket T-5370
def comply_sector_findings(root: Path) -> tuple[ComplySectorFinding, ...]:
    """COMPLY117-122: every sector-specific applicability-flag-gated
    finding under `root`.

    MUST-STAY-QUIET (module docstring): returns `()` immediately, before
    even reading git state, when every `[comply]` flag is absent/false.
    Otherwise short-circuits to `()` when `frob.webapp._detect.
    detect_frameworks` reports no web framework at all (T-5302's
    contract, same posture every sibling WEBSEC/COMPLY family follows).

    frob:ticket T-5370
    """
    root = Path(root)
    flags = _read_sector_flags(root)
    if not flags.any_set():
        _log.debug("comply_sector: no [comply] flag set at %s, staying quiet", root)
        return ()

    frameworks = detect_frameworks(root)
    if not frameworks:
        _log.debug("comply_sector: no framework detected at %s, skipping scan", root)
        return ()

    text = _tracked_text(root)
    findings: list[ComplySectorFinding] = []
    findings.extend(_glba_notice_findings(text, flags))
    findings.extend(_glba_safeguards_findings(text, flags))
    findings.extend(_hipaa_technical_findings(text, flags))
    findings.extend(_hipaa_administrative_findings(root, frameworks, flags))
    findings.extend(_coppa_consent_findings(root, flags))
    findings.extend(_ferpa_edtech_findings(text, flags))

    _log.info("comply_sector: %d finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/webapp-comply-sector.md#public-api
# frob:ticket T-5370
def websec_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """`frob.gates._taint_gate.taint_gate`'s hook-discovery contract
    (T-5308's `websec_findings`-shaped signature, reused by this COMPLY
    leaf per this module's own docstring since `frob.webapp.
    _comply_substrate` defines no comply-specific convention of its
    own). `frameworks` is the caller's own already-computed
    `detect_frameworks(root)` result -- unused directly here since
    `comply_sector_findings` re-derives it itself after the flag
    short-circuit (the flag check must run BEFORE any framework/git
    work, module docstring's MUST-STAY-QUIET contract), but accepted for
    signature parity with every other discovered hook.

    frob:ticket T-5370
    """
    if not frameworks:
        _log.debug(
            "comply_sector: no framework detected at %s, skipping scan (hook)",
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
        for finding in comply_sector_findings(root)
    )
