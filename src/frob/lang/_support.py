"""LanguageSupport contract: one typed registration per language (T-0405).

The audit that motivated this ticket found the per-language gap class
scattered invisibly across `frob.lang`, `frob.vet`, `frob.testing`, and
`frob.dup`: Python is binding-resolved while TypeScript/Rust/C++ are
lexical-only, doc/coverage/drift gates run only in the Python pipeline,
and none of this showed up as a build failure -- a half-added language
(the PyO3-publicness incident class) shipped silently. This module does
NOT re-implement any of those registries -- it DERIVES a `LanguageSupport`
snapshot per language from each existing single-source-of-truth (`frob.
lang.supported_languages`, `frob.vet._capability_registry.LANGUAGES`,
`frob.dup._exhaustiveness.LANGUAGES`, `frob.arch`'s per-language dispatch,
`frob.gates._docblocks`'s fenced-block language buckets) so there is
exactly one place that knows "grammar exists" and exactly one place that
knows "grammar exists AND capability/dup/arch/docblock coverage is
accounted for too" -- this module is the latter.

Every `(language, facet)` cell is EITHER `IMPLEMENTED` (a real code path
exists), `NOT_APPLICABLE` with a reason (the facet genuinely does not
apply to this language -- e.g. `.strata` has no clone-detection use case),
or `KNOWN_GAP` with a reason naming the tracking ticket (a real,
acknowledged hole -- distinct from silence: it shows up in every
`conformance_violations` scan, it just does not fail the build until the
tracking ticket lands). A cell entirely ABSENT from a
`LanguageSupport.facets` dict is what `conformance_violations` treats as
the unaccounted-for hole this whole module exists to make loud -- see its
docstring.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

_log = get_logger(__name__)

# T-0405: `frob.dup`, `frob.gates._docblocks`, and `frob.vet` all sit ABOVE
# `frob.lang` in the dependency order (they import `frob.lang`, directly or
# transitively via `frob.graph`/`frob.check`) -- a module-level import here
# would make `import frob.lang` itself circular the moment this module is
# imported from `frob.lang.__init__`. Every per-facet `_*_status` helper
# below imports its one registry lazily, inside the function body, for
# exactly that reason; see docs/modules/lang.md#language-support-contract.

__all__ = [
    "FACETS",
    "FACET_ARCH",
    "FACET_CAPABILITY",
    "FACET_DOCBLOCK",
    "FACET_DUP",
    "FACET_GRAMMAR",
    "KNOWN_GAP_TRACKING_TICKETS",
    "FacetState",
    "FacetStatus",
    "LanguageSupport",
    "conformance_violations",
    "derive_language_registry",
]

# frob:doc docs/modules/lang.md#language-support-contract
#: Grammar/extraction exists for this language (`frob.lang.supported_languages`).
FACET_GRAMMAR = "grammar"

# frob:doc docs/modules/lang.md#language-support-contract
#: The dangerous-operation capability matrix (`frob.vet._capability_registry`)
#: has an entry for this language.
FACET_CAPABILITY = "capability"

# frob:doc docs/modules/lang.md#language-support-contract
#: The duplicate-detection rung ladder (`frob.dup._exhaustiveness`) claims
#: coverage for this language.
FACET_DUP = "dup"

# frob:doc docs/modules/lang.md#language-support-contract
#: `frob.arch`'s structural-analysis dispatch (long function/god class/...)
#: has a per-language branch for this language.
FACET_ARCH = "arch"

# frob:doc docs/modules/lang.md#language-support-contract
#: DOC004 (`frob.gates._docblocks`) recognizes this language's fenced-code
#: block tag and extracts symbols from it for doc-drift checking.
FACET_DOCBLOCK = "docblock"

# frob:doc docs/modules/lang.md#language-support-contract
#: Every facet a registered language must account for, one way or another
#: (`FacetState.IMPLEMENTED`/`NOT_APPLICABLE`/`KNOWN_GAP`) -- the
#: conformance gate's enumeration universe (T-0405).
FACETS: tuple[str, ...] = (
    FACET_GRAMMAR,
    FACET_CAPABILITY,
    FACET_DUP,
    FACET_ARCH,
    FACET_DOCBLOCK,
)


# frob:doc docs/modules/lang.md#language-support-contract
class FacetState(StrEnum):
    """How a `(language, facet)` cell is accounted for -- never silence."""

    IMPLEMENTED = "implemented"
    NOT_APPLICABLE = "not_applicable"
    KNOWN_GAP = "known_gap"


# frob:doc docs/modules/lang.md#language-support-contract
class FacetStatus(BaseModel):
    """One `(language, facet)` cell: its state plus an honest detail string.

    `detail` is required non-empty for `NOT_APPLICABLE`/`KNOWN_GAP` (a
    reasoned exemption or an acknowledged gap must say why/where it is
    tracked, mirroring the `frob:waive`/registry `disposition` discipline
    elsewhere in this repo) -- `derive_language_registry` never emits an
    empty one; `conformance_violations` flags a missing/blank detail on a
    hand-built registry the same way `WAIVE001` flags a reasonless waiver.
    """

    model_config = ConfigDict(frozen=True)

    state: FacetState
    detail: str


# frob:doc docs/modules/lang.md#language-support-contract
class LanguageSupport(BaseModel):
    """One language's full facet accounting -- the T-0405 typed registration.

    `facets` is keyed by facet name (`FACETS` members); a key ABSENT from
    this dict is the "fell through the cracks" case `conformance_violations`
    fails loudly on -- every facet for every registered language must be
    an explicit `FacetStatus`, never an implicit gap.
    """

    model_config = ConfigDict(frozen=True)

    language: str
    facets: dict[str, FacetStatus]

    # frob:doc docs/modules/lang.md#language-support-contract
    # frob:tests tests/test_lang_support.py::TestConformanceViolations.test_missing_facet_fails  # noqa: E501
    def missing_facets(self) -> tuple[str, ...]:
        """Facets in `FACETS` entirely absent from `self.facets`, sorted.

        Distinct from `KNOWN_GAP` (an acknowledged, ticketed hole) --
        this is the unaccounted-for case: nothing here ever says why.
        """
        return tuple(f for f in FACETS if f not in self.facets)

    # frob:doc docs/modules/lang.md#language-support-contract
    # frob:tests tests/test_lang_support.py::TestConformanceViolations.test_unreasoned_known_gap_fails  # noqa: E501
    def unreasoned_facets(self) -> tuple[str, ...]:
        """Present facets whose `NOT_APPLICABLE`/`KNOWN_GAP` `detail` is blank.

        A state without a reason is exactly as unaccountable as a missing
        cell -- see `FacetStatus.detail`'s docstring.
        """
        out = []
        for name in FACETS:
            status = self.facets.get(name)
            if status is None:
                continue
            if status.state is not FacetState.IMPLEMENTED and not status.detail.strip():
                out.append(name)
        return tuple(out)


def _implemented(detail: str) -> FacetStatus:
    """`FacetStatus(IMPLEMENTED, detail)` -- a one-line constructor so each
    per-language cell below reads as one call, not a three-field literal."""
    return FacetStatus(state=FacetState.IMPLEMENTED, detail=detail)


def _not_applicable(detail: str) -> FacetStatus:
    """`FacetStatus(NOT_APPLICABLE, detail)` -- see `_implemented`."""
    return FacetStatus(state=FacetState.NOT_APPLICABLE, detail=detail)


def _known_gap(detail: str) -> FacetStatus:
    """`FacetStatus(KNOWN_GAP, detail)` -- see `_implemented`."""
    return FacetStatus(state=FacetState.KNOWN_GAP, detail=detail)


# frob:doc docs/modules/lang.md#language-support-contract
# frob:ticket T-0823
#: Every ticket id ever cited by a `_known_gap` `detail` string in this
#: module, mapped to whether FROB'S OWN tracking still considers it open
#: (T-0823). These ids are frob-internal (e.g. `T-0329`, frob's own
#: multi-language-arch epic) -- they name work tracked in FROB's project,
#: not in whatever repo `frob check` happens to be running against. Prior
#: to T-0823, LANG003 verified a cited id against the CHECKED repo's own
#: `TicketQueue`, which only ever coincidentally works for frob's own
#: repo; a downstream adopter's queue never defines a frob-internal id at
#: all, so every known-gap facet escalated to ERROR there unconditionally
#: (T-0818's finding). This dict is frob's own shipped, hand-maintained
#: source of truth instead -- a maintainer flips an entry to `False` (or
#: removes the id from the corresponding `detail` string) the same
#: release a cited ticket actually closes; `_lang_conformance._lang003_
#: unsound_gaps` reads ONLY this, never any repo's `TicketQueue`, for
#: known-gap verification.
KNOWN_GAP_TRACKING_TICKETS: dict[str, bool] = {
    # T-0329: EPIC arch multi-language: normalized code model -- cited by
    # `_arch_status`'s known-gap detail for every language frob.arch has
    # no per-language dispatch branch for yet (c/rust/typescript today).
    "T-0329": True,
}


# T-0405: `frob.arch.__init__._run_language_checks` dispatches on
# `language == "python"` / `language == "cpp"` only (T-0329, the queued
# multi-language-arch epic, tracks widening this) -- there is no shared
# constant to import without touching that dispatch's own scope, so this
# mirrors it as the single derivation point for the arch facet below. If
# the dispatch chain changes, `tests/test_lang_support.py`'s fixture-driven
# assertions on `derive_language_registry()` catch the drift (a language
# newly dispatched there but still marked KNOWN_GAP here fails loudly, not
# silently).
_ARCH_DISPATCHED_LANGUAGES = frozenset({"python", "cpp"})

# The bare `LANGUAGES` capability-registry bucket "c-cpp" covers both
# `frob.lang`'s "c" and "cpp" labels (docs/modules/vet.md, T-0405 survey) --
# derived here as a set so `_capability_status` never hand-copies the
# `("c", "cpp")` pair a second time.
_CAPABILITY_C_CPP_MEMBERS = frozenset({"c", "cpp"})


def _docblock_languages() -> frozenset[str]:
    """DOC004's fenced-language buckets, normalized onto `frob.lang`
    canonical labels -- derived directly from `_PYTHON_LANGS`/`_RUST_LANGS`/
    `_TS_LANGS`/`_C_CPP_LANGS` (never a hand-copied second list) so a bucket
    added there is picked up here automatically. Imported lazily -- see the
    module-level dependency-order note above.

    T-0566: `_C_CPP_LANGS` covers both `frob.lang`'s "c" and "cpp" labels
    (one merged fenced-block bucket, same "c-cpp" merge `_capability_status`
    already uses for the capability-registry facet -- see
    `_CAPABILITY_C_CPP_MEMBERS`)."""
    from frob.gates._docblocks import (
        _C_CPP_LANGS,
        _PYTHON_LANGS,
        _RUST_LANGS,
        _TS_LANGS,
    )

    return frozenset(
        ({"python"} if _PYTHON_LANGS else set())
        | ({"rust"} if _RUST_LANGS else set())
        | ({"typescript"} if _TS_LANGS else set())
        | (_CAPABILITY_C_CPP_MEMBERS if _C_CPP_LANGS else set())
    )


def _grammar_status(language: str) -> FacetStatus:
    """Every language in `derive_language_registry`'s universe comes FROM
    `frob.lang.supported_languages`, so grammar is always implemented."""
    return _implemented(f"{language} has a registered frob.lang grammar/extractor")


def _capability_status(language: str) -> FacetStatus:
    """T-0405 survey: python/typescript/rust/kotlin are direct buckets in
    `frob.vet._capability_registry.LANGUAGES`; c/cpp share the "c-cpp"
    bucket; `.strata` is a design DSL with no general-purpose
    dangerous-operation surface (T-0405 survey), so it is a reasoned
    not-applicable rather than a gap."""
    if language == "strata":
        return _not_applicable(
            "strata is a system-design DSL with no general-purpose "
            "dangerous-operation surface; its own threat/effects "
            "catalogs (frob.strata._threat/_effects) cover the "
            "equivalent ground under a different vocabulary"
        )
    from frob.vet._capability_registry import LANGUAGES as capability_languages

    if language in _CAPABILITY_C_CPP_MEMBERS:
        if "c-cpp" in capability_languages:
            return _implemented(
                "covered by frob.vet._capability_registry's merged 'c-cpp' bucket"
            )
        return _known_gap("c-cpp bucket missing from capability LANGUAGES")
    if language in capability_languages:
        return _implemented("frob.vet._capability_registry.LANGUAGES entry")
    return _known_gap(f"{language} absent from frob.vet._capability_registry.LANGUAGES")


def _dup_status(language: str) -> FacetStatus:
    """`.strata` has no clone-detection use case (frob.dup._exhaustiveness's
    own module docstring); every other grammar language is expected to
    appear in `_DUP_LANGUAGES` directly."""
    if language == "strata":
        return _not_applicable(
            "no clone-detection use case for the .strata DSL "
            "(frob.dup._exhaustiveness module docstring)"
        )
    from frob.dup._exhaustiveness import LANGUAGES as dup_languages

    if language in dup_languages:
        return _implemented("frob.dup._exhaustiveness.LANGUAGES entry")
    return _known_gap(f"{language} absent from frob.dup._exhaustiveness.LANGUAGES")


def _arch_status(language: str) -> FacetStatus:
    """`.strata` is not general-purpose source code arch's categories
    (long function/god class/deep nesting) reason about; typescript/rust/c
    have no dispatch branch in `frob.arch` today -- a real, already-ticketed
    gap (T-0329's queued normalized-code-model epic), not silence."""
    if language == "strata":
        return _not_applicable(
            "strata design files are not general-purpose source code; "
            "frob.arch's long-function/god-class/nesting categories do "
            "not apply to the DSL's own structure"
        )
    if language in _ARCH_DISPATCHED_LANGUAGES:
        return _implemented("frob.arch dispatches a per-language rule submodule")
    return _known_gap(
        f"{language} has no frob.arch dispatch branch -- tracked by "
        f"T-0329 (EPIC arch multi-language: normalized code model)"
    )


def _docblock_status(language: str) -> FacetStatus:
    """`.strata` has no fenced-code-block doc convention today. c/cpp (T-0566)
    now share `_C_CPP_LANGS`'s merged bucket, same as every other language
    with a real `frob.gates._docblocks` entry -- no known_gap remains here."""
    if language == "strata":
        return _not_applicable(
            "no established ```strata fenced-code-block doc convention "
            "for DOC004 to extract symbols from yet"
        )
    if language in _docblock_languages():
        return _implemented("frob.gates._docblocks fenced-language bucket entry")
    return _known_gap(f"{language} has no DOC004 fenced-language bucket")


# frob:doc docs/modules/lang.md#language-support-contract
# frob:ticket T-0405
# frob:tests tests/test_lang_support.py::TestDeriveLanguageRegistry.test_covers_every_supported_language  # noqa: E501
def derive_language_registry() -> dict[str, LanguageSupport]:
    """One `LanguageSupport` per `frob.lang.supported_languages()` member.

    Every cell is derived from the real, live registry it names (never a
    hand-copied constant) -- see the module docstring and each `_*_status`
    helper above. This is the single place a new `frob.lang` grammar
    (Kotlin, Swift, Go, ...) becomes visible as a language that MUST
    account for every facet: adding it to `frob.lang._EXTENSION_TABLE`
    (or the `.strata`-style special case) is what makes it appear here at
    all, with every facet defaulting to `KNOWN_GAP` until the matching
    per-facet registry is updated too.
    """
    from frob.lang import supported_languages

    registry: dict[str, LanguageSupport] = {}
    for language in sorted(supported_languages()):
        facets = {
            FACET_GRAMMAR: _grammar_status(language),
            FACET_CAPABILITY: _capability_status(language),
            FACET_DUP: _dup_status(language),
            FACET_ARCH: _arch_status(language),
            FACET_DOCBLOCK: _docblock_status(language),
        }
        registry[language] = LanguageSupport(language=language, facets=facets)
    _log.info("derive_language_registry: %d language(s) registered", len(registry))
    return registry


# frob:doc docs/modules/lang.md#language-support-contract
# frob:ticket T-0405
# frob:tests tests/test_lang_support.py::TestConformanceViolations.test_missing_facet_fails  # noqa: E501
# frob:tests tests/test_lang_support.py::TestConformanceViolations.test_fully_registered_language_passes  # noqa: E501
def conformance_violations(
    registry: dict[str, LanguageSupport],
) -> tuple[str, ...]:
    """One message per unaccounted-for `(language, facet)` cell in `registry`.

    Fail-closed by construction: `LanguageSupport.missing_facets` (a facet
    key absent entirely) and `LanguageSupport.unreasoned_facets` (a
    `NOT_APPLICABLE`/`KNOWN_GAP` cell with a blank `detail`) both produce a
    message here -- a `KNOWN_GAP` WITH a detail does not (see the module
    docstring: an acknowledged, ticketed gap is accounted for, not silent).
    A fixture language registered with a missing facet fails here; a fully
    registered language (every facet `IMPLEMENTED`, or `NOT_APPLICABLE`/
    `KNOWN_GAP` with a reason) produces nothing.
    """
    violations: list[str] = []
    for language, support in sorted(registry.items()):
        for facet in support.missing_facets():
            violations.append(
                f"{language}: facet '{facet}' has no LanguageSupport entry "
                f"at all -- every registered language must declare every "
                f"facet as implemented, not-applicable (with a reason), or "
                f"a known gap (with a tracking ticket)"
            )
        for facet in support.unreasoned_facets():
            violations.append(
                f"{language}: facet '{facet}' is not-applicable/known-gap "
                f"but carries no reason -- an unreasoned exemption is as "
                f"unaccountable as a missing cell"
            )
    return tuple(violations)
