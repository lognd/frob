"""LANG001-LANG003: language-extension conformance, shipped per-project (T-0405/T-0406).

LANG001 (`lang_conformance_gate`, T-0405) turns `frob.lang._support.
conformance_violations` into real `Violation`s -- a registered `frob.lang`
grammar language missing a facet (implemented, reasoned not-applicable, or
a ticketed known gap) fails `frob check` at ERROR severity, the same
fail-closed posture `frob.gates._registry_exhaustiveness` takes over
`docs/design/registry/*.yaml`. This is what makes the PyO3-publicness
incident class (a language quietly shipped with one facet unimplemented)
a build failure instead of an invisible product gap: `derive_language_
registry` runs against the LIVE state of every per-facet registry, so
this gate is always checking today's reality, not a stale snapshot.

LANG002/LANG003 (`project_lang_conformance_gate`, T-0406) is the per-
PROJECT half of the same guarantee: LANG001 only ever checks languages
frob has ALREADY registered a grammar for -- a downstream repo that
contains a language frob has NO registration for at all (Kotlin, Swift,
Go, ...) would otherwise get silent, invisible zero-coverage. LANG002
scans the actual repo tree for well-known candidate-language extensions
frob does not parse at all and fails loudly per file found. LANG003 scans
for languages frob DOES register but currently marks `KNOWN_GAP` for some
facet (T-0405) that are actually PRESENT in this repo's tree -- if the gap
names a real, currently-open tracking ticket, it stays a WARN (loud, but
honestly tracked); if the ticket reference does not verify (closed,
missing, or unparseable -- the same anti-lie posture REG002/REG003 take
over `handled_by`/`deferred`), it escalates to ERROR: a claimed gap that
does not actually check out is exactly the fake-coverage silence this
ticket exists to close.
"""

from __future__ import annotations

import re
from pathlib import Path

from frob.excludes import iter_files
from frob.gates._models import Severity, Violation
from frob.lang import language_for_extension, supported_extensions
from frob.lang._support import (
    FacetState,
    conformance_violations,
    derive_language_registry,
)
from frob.logging import get_logger
from frob.tickets._models import TicketQueue, TicketState

_log = get_logger(__name__)

__all__ = ["lang_conformance_gate", "project_lang_conformance_gate"]

# T-0406: well-known general-purpose-language extensions frob has NO
# `frob.lang` grammar registration for at all (as opposed to T-0405's
# `KNOWN_GAP`, which covers a registered language missing ONE facet) --
# a file matching one of these in a downstream repo gets literally zero
# frob coverage (no capability scan, no dup detection, no arch check, no
# doc-drift check) and nothing today ever says so. Deliberately a small,
# named, well-known set (not "any extension frob does not recognize",
# which would flag every config/asset file in a repo) -- the exact
# languages the T-0406 acceptance criteria name (Kotlin/Swift/Go) plus a
# few equally common general-purpose siblings.
_UNREGISTERED_CANDIDATE_LANGUAGES: dict[str, str] = {
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".swift": "swift",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".cs": "csharp",
}

# A `KNOWN_GAP`/`NOT_APPLICABLE` `detail` string's tracking-ticket
# reference, matched the same way `docs/design/registry` dispositions
# name a ticket -- see `_verify_known_gap_ticket` below.
_TICKET_REF_RE = re.compile(r"\bT-(?:draft-)?[0-9a-fA-F]+\b")


def _verify_known_gap_ticket(detail: str, queue: TicketQueue) -> str | None:
    """`None` if `detail` names a real, currently-open ticket; else an
    explanation of why the claim does not verify (missing ticket
    reference, unknown id, or a closed/dropped ticket) -- the anti-lie
    check `_classify_deferred` (`frob.gates._registry_exhaustiveness`)
    performs for `deferred:<ticket>`, reused here for `KNOWN_GAP` details.
    """
    match = _TICKET_REF_RE.search(detail)
    if match is None:
        return "detail names no tracking ticket at all"
    ticket_id = match.group(0)
    ticket = queue.tickets.get(ticket_id)
    if ticket is None:
        return f"detail names {ticket_id}, which does not exist in the loaded queue"
    if ticket.state in (TicketState.DONE, TicketState.DROPPED):
        return f"detail names {ticket_id}, which is already {ticket.state.value}"
    return None


# frob:doc docs/modules/lang.md#language-support-contract
# frob:ticket T-0405
# frob:tests tests/test_lang_conformance_gate.py::TestLangConformanceGate.test_real_registry_is_clean  # noqa: E501
# frob:tests tests/test_lang_conformance_gate.py::TestLangConformanceGate.test_missing_facet_becomes_error_violation  # noqa: E501
# frob:enforces CHK-GATE-LANG001
def lang_conformance_gate() -> tuple[Violation, ...]:
    """LANG001 for every unaccounted-for `(language, facet)` cell in the
    live `frob.lang` language-support registry.

    Takes no arguments (unlike most gates here) -- `derive_language_
    registry` reads the real, in-process registries directly, so there is
    no repo-scanned state to thread through; a caller wanting a different
    registry for testing calls `conformance_violations` directly instead
    (see `tests/test_lang_support.py`).
    """
    registry = derive_language_registry()
    messages = conformance_violations(registry)
    violations = tuple(
        Violation(
            rule="LANG001",
            severity=Severity.ERROR,
            file="src/frob/lang/_support.py",
            line=0,
            message=f"LANG001: {message}",
        )
        for message in messages
    )
    _log.info(
        "lang_conformance_gate: %d language(s) checked, %d violation(s)",
        len(registry),
        len(violations),
    )
    return violations


# frob:enforces CHK-GATE-LANG002
def _lang002_unregistered_files(repo_root: Path) -> tuple[Violation, ...]:
    """LANG002: one ERROR per tracked file whose extension matches a
    well-known candidate language (`_UNREGISTERED_CANDIDATE_LANGUAGES`)
    frob has no `frob.lang` grammar for at all -- split out of
    `project_lang_conformance_gate` for ARCH001."""
    violations: list[Violation] = []
    for ext, language in sorted(_UNREGISTERED_CANDIDATE_LANGUAGES.items()):
        for path in iter_files(repo_root, suffix=ext):
            rel = path.relative_to(repo_root).as_posix()
            violations.append(
                Violation(
                    rule="LANG002",
                    severity=Severity.ERROR,
                    file=rel,
                    line=0,
                    message=(
                        f"LANG002: {rel} is {language} source, a language "
                        f"frob has NO frob.lang grammar registration for at "
                        f"all -- zero capability/dup/arch/doc-drift "
                        f"coverage for this file, silently, unless a "
                        f"LanguageSupport entry (T-0405) is added for "
                        f"{language}"
                    ),
                )
            )
    return tuple(violations)


# frob:enforces CHK-GATE-LANG003
def _lang003_unsound_gaps(repo_root: Path, queue: TicketQueue) -> tuple[Violation, ...]:
    """LANG003: one violation per `KNOWN_GAP`/`NOT_APPLICABLE` facet cell
    whose language is actually present in `repo_root`'s tree -- WARN if
    the cell's `detail` names a real, open tracking ticket (an honestly
    tracked gap); ERROR if it does not verify (the anti-lie case: a
    claimed gap that does not actually check out is fake coverage, not
    tracked coverage). Split out of `project_lang_conformance_gate` for
    ARCH001."""
    registry = derive_language_registry()
    present_languages: set[str] = set()

    # Extension -> language via frob.lang's own canonical mapping (never a
    # second hand-copied table).
    for ext in supported_extensions():
        if not iter_files(repo_root, suffix=ext):
            continue
        language = language_for_extension(ext)
        if language is not None:
            present_languages.add(language)

    violations: list[Violation] = []
    for language in sorted(present_languages):
        support = registry.get(language)
        if support is None:
            continue
        for facet_name, status in sorted(support.facets.items()):
            # NOT_APPLICABLE never needs a ticket -- it means the facet
            # genuinely does not apply (e.g. strata's DSL-vs-source-code
            # exemptions), not a deferred gap. Only KNOWN_GAP is checked
            # against the live ticket queue.
            if status.state is not FacetState.KNOWN_GAP:
                continue
            problem = _verify_known_gap_ticket(status.detail, queue)
            if problem is None:
                violations.append(
                    Violation(
                        rule="LANG003",
                        severity=Severity.WARN,
                        file=f"src/frob/lang (facet={facet_name})",
                        line=0,
                        message=(
                            f"LANG003: {language} facet '{facet_name}' is "
                            f"{status.state.value} ({status.detail}) and "
                            f"{language} files are present in this repo -- "
                            f"tracked, not silent, but coverage for this "
                            f"facet is unsound for {language} today"
                        ),
                    )
                )
            else:
                violations.append(
                    Violation(
                        rule="LANG003",
                        severity=Severity.ERROR,
                        file=f"src/frob/lang (facet={facet_name})",
                        line=0,
                        message=(
                            f"LANG003: {language} facet '{facet_name}' is "
                            f"{status.state.value} ({status.detail}) and "
                            f"{language} files are present in this repo, "
                            f"but the claimed gap does not verify -- "
                            f"{problem}; this is unsound coverage "
                            f"masquerading as tracked coverage"
                        ),
                    )
                )
    return tuple(violations)


# frob:doc docs/modules/lang.md#per-project-conformance-lang002lang003-t-0406
# frob:ticket T-0406
# frob:tests tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate.test_unregistered_language_file_fails  # noqa: E501
# frob:tests tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate.test_all_conformant_project_passes  # noqa: E501
# frob:tests tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate.test_present_known_gap_with_open_ticket_warns  # noqa: E501
# frob:tests tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate.test_present_known_gap_with_bad_ticket_ref_errors  # noqa: E501
def project_lang_conformance_gate(
    repo_root: Path, queue: TicketQueue
) -> tuple[Violation, ...]:
    """LANG002 (unregistered-language file present) + LANG003 (a
    registered-but-`KNOWN_GAP` facet whose language is actually present)
    over `repo_root`'s tracked file tree (T-0406).

    This is the per-PROJECT half of the T-0405 conformance contract:
    `lang_conformance_gate` (LANG001) only ever checks languages frob has
    ALREADY registered a grammar for; this additionally scans the ACTUAL
    repo tree so a downstream project's real language mix decides what
    fires -- a repo using only fully-conformant languages passes cleanly
    even though frob's global registry still carries `KNOWN_GAP` cells for
    languages that repo never uses.
    """
    violations = _lang002_unregistered_files(repo_root)
    violations += _lang003_unsound_gaps(repo_root, queue)
    _log.info(
        "project_lang_conformance_gate: %d violation(s) (LANG002=%d, LANG003=%d)",
        len(violations),
        sum(1 for v in violations if v.rule == "LANG002"),
        sum(1 for v in violations if v.rule == "LANG003"),
    )
    return violations
