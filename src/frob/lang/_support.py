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

# frob:waive LARGE001 reason="T-1651-grade: this module's own docstring states its \
# entire reason for existing is to be the SINGLE place that derives a LanguageSupport \
# snapshot per language across five upstream registries (frob.lang, frob.vet, \
# frob.dup, frob.arch, frob.gates._docblocks) -- the audit that motivated T-0405 found \
# scattering this exact concern across multiple places is what let a half-added \
# language ship silently. Splitting this module would recreate the scattering problem \
# it was built to eliminate."

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

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

# frob:waive ARCH102 reason="T-2365 added a SECOND, deliberately parallel typed \
# registration \
# (ADAPTER_CAPABILITIES/CapabilityStatus/AdapterCapabilitySupport/derive_capability_reg\
# istry/capability_conformance_violations) alongside the pre-existing one \
# (FACETS/FacetStatus/LanguageSupport/derive_language_registry/conformance_violations) \
# -- the clustering heuristic correctly finds two internally-cohesive naming/usage \
# clusters, one per axis, plus the shared \
# FacetState/_implemented/_not_applicable/_known_gap primitives both axes reuse on \
# purpose (this module's own docstring explains why: one axis is subsystem- \
# INTEGRATION coverage, the other is adapter-CAPABILITY coverage, genuinely different \
# questions this module answers together because they share the exact same accounting \
# discipline). Splitting into two files would duplicate that shared discipline instead \
# of reusing it -- the opposite of what T-2365 was asked to do."
__all__ = [
    "ADAPTER_CAPABILITIES",
    "CAPABILITY_CALL_GRAPH",
    "CAPABILITY_DIRECTIVE_PARSE",
    "CAPABILITY_DOC_EXTRACT",
    "CAPABILITY_IMPORT_GRAPH",
    "CAPABILITY_PUBLICNESS",
    "CAPABILITY_SYMBOL_WALK",
    "CAPABILITY_TEST_DISCOVERY",
    "FACETS",
    "FACET_ARCH",
    "FACET_CAPABILITY",
    "FACET_DOCBLOCK",
    "FACET_DUP",
    "FACET_GRAMMAR",
    "FACET_REFACTOR",
    "KNOWN_GAP_TRACKING_TICKETS",
    "LANGUAGE_SENSITIVE_PACKAGES",
    "AdapterCapabilitySupport",
    "CapabilityRequirement",
    "CapabilityStatus",
    "FacetState",
    "FacetStatus",
    "LanguageSupport",
    "PackageAudit",
    "PackageLanguageAxis",
    "capability_conformance_violations",
    "conformance_violations",
    "derive_capability_registry",
    "derive_language_registry",
    "unfaceted_packages",
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
#: T-2996: `frob.refactor` (move-module/move-symbol/rename) has a real,
#: registered per-language reference scanner for this language --
#: `frob.refactor._module_lang.supported_languages()` for whole-module
#: moves, or an equivalent symbol-reference engine for single-symbol
#: rename/move. Added because `frob.refactor` was found to be Python-only
#: with ZERO language-literal branching (T-2996's "sharpest finding"): a
#: silently single-language module is invisible to any scan that looks
#: for per-language dispatch, because it has no dispatch to find. This
#: facet exists so "does refactor support language X" is a declared cell,
#: not a fact only discoverable by reading `_module_lang.py` source.
# frob:ticket T-2996
FACET_REFACTOR = "refactor"

# frob:doc docs/modules/lang.md#language-support-contract
# frob:ticket T-2996
#: Every facet a registered language must account for, one way or another
#: (`FacetState.IMPLEMENTED`/`NOT_APPLICABLE`/`KNOWN_GAP`) -- the
#: conformance gate's enumeration universe (T-0405).
FACETS: tuple[str, ...] = (
    FACET_GRAMMAR,
    FACET_CAPABILITY,
    FACET_DUP,
    FACET_ARCH,
    FACET_DOCBLOCK,
    FACET_REFACTOR,
)

# T-2365: a SECOND facet-shaped axis, distinct from FACETS above. FACETS is
# subsystem-INTEGRATION coverage (does frob.vet/frob.dup/frob.arch/frob.
# gates._docblocks have an entry for this language). This axis is ADAPTER-
# CAPABILITY coverage: does the adapter ITSELF implement the primitive
# operation at all, independent of which downstream subsystem consumes it.
# The distinction matters because a language can score FACET_CAPABILITY
# IMPLEMENTED (frob.vet has an entry) while its adapter has no import-graph
# walker at all (frob.lang._extract._IMPORT_WALKERS) -- two genuinely
# different questions FACETS alone cannot separate.

# frob:doc docs/modules/lang.md#adapter-capability-contract-t-2365
#: `frob.lang._extract._WALKERS` (or the strata-core pairing for `.strata`)
#: can turn this language's source into a `RawSymbol` tuple at all.
CAPABILITY_SYMBOL_WALK = "symbol_walk"

# frob:doc docs/modules/lang.md#adapter-capability-contract-t-2365
#: Every `RawSymbol` this adapter emits carries a real, language-correct
#: `public: bool` (T-0841's per-grammar publicness rule), not a placeholder.
CAPABILITY_PUBLICNESS = "publicness"

# frob:doc docs/modules/lang.md#adapter-capability-contract-t-2365
#: This adapter extracts `RawComment`s at all -- `frob.lang._extract.
#: COMMENT_TYPES`, or (for `.strata`, which has no tree-sitter comment
#: node type) `_walk_strata`'s own whole-line `//` comment scan.
CAPABILITY_DOC_EXTRACT = "doc_extract"

# frob:doc docs/modules/lang.md#adapter-capability-contract-t-2365
#: `frob.graph.dsl.parse_directives` can recover a `frob:` directive from
#: this language's extracted comments, including a backslash-continued
#: multi-line directive (`_fold_continuations`) -- frob's own sharpest
#: test case for this capability, since a continuation that folds wrong
#: silently truncates the directive instead of failing loudly.
CAPABILITY_DIRECTIVE_PARSE = "directive_parse"

# frob:doc docs/modules/lang.md#adapter-capability-contract-t-2365
#: `frob.graph.callgraph.build_call_graph` can resolve a call edge for
#: this language's symbols (bare-short-name matching over `RawSymbol.
#: public`/`sig_tokens`, language-agnostic once `CAPABILITY_SYMBOL_WALK`
#: holds).
CAPABILITY_CALL_GRAPH = "call_graph"

# frob:doc docs/modules/lang.md#adapter-capability-contract-t-2365
#: `frob.lang.extract_imports` (`_IMPORT_WALKERS`) has a real per-language
#: walker for this language's import/include syntax.
CAPABILITY_IMPORT_GRAPH = "import_graph"

# frob:doc docs/modules/lang.md#adapter-capability-contract-t-2365
#: `frob.testing` has a `collect_*_tests` entrypoint that can discover
#: this language's own test suite.
CAPABILITY_TEST_DISCOVERY = "test_discovery"

# frob:doc docs/modules/lang.md#adapter-capability-contract-t-2365
#: Every capability a registered language's adapter must account for, one
#: way or another (`FacetState.IMPLEMENTED`/`NOT_APPLICABLE`/`KNOWN_GAP`)
#: -- the behavioral conformance suite's enumeration universe (T-2365).
ADAPTER_CAPABILITIES: tuple[str, ...] = (
    CAPABILITY_SYMBOL_WALK,
    CAPABILITY_PUBLICNESS,
    CAPABILITY_DOC_EXTRACT,
    CAPABILITY_DIRECTIVE_PARSE,
    CAPABILITY_CALL_GRAPH,
    CAPABILITY_IMPORT_GRAPH,
    CAPABILITY_TEST_DISCOVERY,
)


# frob:doc docs/modules/lang.md#adapter-capability-contract-t-2365
# frob:tests tests/test_lang_support.py::TestCapabilityConformanceViolations.test_fully_registered_language_passes  # noqa: E501
class CapabilityRequirement(StrEnum):
    """Whether a `(language, capability)` cell is REQUIRED (every language
    must eventually reach `IMPLEMENTED`, or be a reasoned `NOT_APPLICABLE`)
    or OPTIONAL (a `KNOWN_GAP` is an acceptable steady state, not just a
    tolerated one) -- distinct from `FacetState`, which says what the
    current status IS; this says how much that status is allowed to matter."""

    REQUIRED = "required"
    OPTIONAL = "optional"


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
        return _unreasoned_names(FACETS, self.facets)


# frob:doc docs/modules/lang.md#adapter-capability-contract-t-2365
# frob:tests tests/test_lang_support.py::TestCapabilityConformanceViolations.test_fully_registered_language_passes  # noqa: E501
class CapabilityStatus(BaseModel):
    """One `(language, capability)` cell: requirement, state, and an honest
    detail string -- the same `FacetState`/reasoned-detail discipline
    `FacetStatus` established, plus `requirement` (T-2365's own addition).
    `detail` is required non-empty for `NOT_APPLICABLE`/`KNOWN_GAP`, same
    rule as `FacetStatus.detail`."""

    model_config = ConfigDict(frozen=True)

    requirement: CapabilityRequirement
    state: FacetState
    detail: str


# frob:doc docs/modules/lang.md#adapter-capability-contract-t-2365
# frob:tests tests/test_lang_support.py::TestDeriveCapabilityRegistry.test_covers_every_supported_language  # noqa: E501
class AdapterCapabilitySupport(BaseModel):
    """One language's full adapter-capability accounting -- the T-2365
    typed registration, structurally identical in spirit to
    `LanguageSupport` but keyed on `ADAPTER_CAPABILITIES` instead of
    `FACETS`. A capability key ABSENT from `capabilities` is the same
    "fell through the cracks" case `capability_conformance_violations`
    fails loudly on."""

    model_config = ConfigDict(frozen=True)

    language: str
    capabilities: dict[str, CapabilityStatus]

    # frob:doc docs/modules/lang.md#adapter-capability-contract-t-2365
    # frob:tests tests/test_lang_support.py::TestCapabilityConformanceViolations.test_missing_capability_fails  # noqa: E501
    def missing_capabilities(self) -> tuple[str, ...]:
        """Capabilities in `ADAPTER_CAPABILITIES` entirely absent from
        `self.capabilities`, sorted -- mirrors `LanguageSupport.
        missing_facets`."""
        return tuple(c for c in ADAPTER_CAPABILITIES if c not in self.capabilities)

    # frob:doc docs/modules/lang.md#adapter-capability-contract-t-2365
    # frob:tests tests/test_lang_support.py::TestCapabilityConformanceViolations.test_unreasoned_known_gap_fails  # noqa: E501
    def unreasoned_capabilities(self) -> tuple[str, ...]:
        """Present capabilities whose `NOT_APPLICABLE`/`KNOWN_GAP` `detail`
        is blank -- shares `_unreasoned_names` with `LanguageSupport.
        unreasoned_facets` (the two axes' accounting rule is identical by
        design; DUP001 flagged the pre-extraction near-duplicate)."""
        return _unreasoned_names(ADAPTER_CAPABILITIES, self.capabilities)


# frob:doc docs/modules/lang.md#language-support-contract
# frob:tests tests/test_lang_support.py::TestConformanceViolations.test_unreasoned_known_gap_fails  # noqa: E501
# frob:tests tests/test_lang_support.py::TestCapabilityConformanceViolations.test_unreasoned_known_gap_fails  # noqa: E501
# frob:waive COV007 reason="docs/modules/lang.md's Adapter-capability contract \
# (T-2365) section documents several symbols under one section, not just a public \
# entry point -- the many-symbols- one-section convention this repo already accepted \
# for vet.md (T-2810 declined to touch it), not a T-2810-shaped duplicate"
def _unreasoned_names(
    universe: tuple[str, ...],
    cells: dict[str, FacetStatus] | dict[str, CapabilityStatus],
) -> tuple[str, ...]:
    """Names in `universe` present in `cells` with a `NOT_APPLICABLE`/
    `KNOWN_GAP` state and a blank `detail` -- the shared accounting rule
    both `LanguageSupport.unreasoned_facets` (T-0405) and `AdapterCapability
    Support.unreasoned_capabilities` (T-2365) apply, extracted once both
    axes turned out to need the IDENTICAL rule (`FacetStatus` and
    `CapabilityStatus` both carry `state`/`detail`, just as `CapabilityStatus`
    additionally carries `requirement`). A state without a reason is
    exactly as unaccountable as a missing cell -- see `FacetStatus.detail`'s
    docstring."""
    out = []
    for name in universe:
        status = cells.get(name)
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


def _cap_implemented(
    requirement: CapabilityRequirement, detail: str
) -> CapabilityStatus:
    """`CapabilityStatus(requirement, IMPLEMENTED, detail)` -- the
    capability-axis analogue of `_implemented`."""
    return CapabilityStatus(
        requirement=requirement, state=FacetState.IMPLEMENTED, detail=detail
    )


def _cap_not_applicable(
    requirement: CapabilityRequirement, detail: str
) -> CapabilityStatus:
    """`CapabilityStatus(requirement, NOT_APPLICABLE, detail)` -- see
    `_cap_implemented`."""
    return CapabilityStatus(
        requirement=requirement, state=FacetState.NOT_APPLICABLE, detail=detail
    )


def _cap_known_gap(requirement: CapabilityRequirement, detail: str) -> CapabilityStatus:
    """`CapabilityStatus(requirement, KNOWN_GAP, detail)` -- see
    `_cap_implemented`."""
    return CapabilityStatus(
        requirement=requirement, state=FacetState.KNOWN_GAP, detail=detail
    )


# frob:doc docs/modules/lang.md#language-support-contract
# frob:ticket T-0823
# frob:ticket T-2996
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
    # T-1604's own filed finding: bash's bare-word call syntax is
    # unrecognized by frob.graph.callgraph's shared token-adjacency call
    # detector -- cited by `_capability_call_graph_status`'s bash branch.
    "T-2901": True,
    # T-2906 (bash/csharp not yet wired into the capability/dup/docblock
    # FACETS, `_NEW_ADAPTER_LANGUAGES_PENDING_FACET_WIRING`'s prior
    # KNOWN_GAP) removed -- the gap is closed: bash/csharp are real
    # LANGUAGES entries in frob.vet._capability_registry and frob.dup.
    # _exhaustiveness, and real fenced-block buckets in frob.gates.
    # _docblocks (_CONSOLE_LANGS for bash, the new _CSHARP_LANGS for
    # csharp); no detail string cites T-2906 any more.
    # T-2409 (`_capability_test_discovery_status`'s prior kotlin
    # KNOWN_GAP) removed -- the gap is closed, T-2409 landed a real
    # `frob.testing.collect_kotlin_tests` collector and T-2499's
    # `_TEST_DISCOVERY_COLLECTORS` registry now derives kotlin as
    # IMPLEMENTED from that live entry; no detail string cites T-2409
    # any more.
    # T-2410 (`_capability_publicness_status`'s prior strata KNOWN_GAP)
    # removed -- the gap is closed, `_walk_strata.py` now derives a real
    # clearance-based `public` value; no live tracking ticket references
    # it here any more.
    # T-3231: EPIC refactor multi-language: per-language reference
    # scanners -- cited by `_refactor_status`'s known-gap detail for
    # every language `frob.refactor._module_lang._MODULE_LANGUAGE_
    # ADAPTERS` has no entry for yet (T-2996 found this is every
    # language except python).
    "T-3231": True,
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

# T-2996: `frob.refactor._module_lang._MODULE_LANGUAGE_ADAPTERS`'s key set,
# mirrored the same way `_ARCH_DISPATCHED_LANGUAGES` mirrors frob.arch's
# dispatch above -- NOT a lazy import of `frob.refactor`, deliberately.
# `frob.refactor._module_resolve` imports `frob.lang` at module level, so
# `frob.lang._support` importing `frob.refactor` back (even lazily, inside
# a function body -- CYCLE001's static analysis follows those edges too,
# unlike Python's own runtime resolution) would close a real import cycle
# across package boundaries: measured directly, this exact edge escalated
# frob-cycle from 2 pre-existing same-package warnings to a new
# cross-package ERROR the first time it was tried. If frob.refactor's
# adapter registry changes, `tests/test_lang_support.py`'s fixture-driven
# assertions on `derive_language_registry()` catch the drift the same way
# the arch mirror's comment above describes.
# frob:ticket T-2996
# frob:tests tests/test_lang_support.py::test_refactor_adapter_languages_matches_live_registry  # noqa: E501
_REFACTOR_ADAPTER_LANGUAGES = frozenset({"python"})

# The bare `LANGUAGES` capability-registry bucket "c-cpp" covers both
# `frob.lang`'s "c" and "cpp" labels (docs/modules/vet.md, T-0405 survey) --
# derived here as a set so `_capability_status` never hand-copies the
# `("c", "cpp")` pair a second time.
_CAPABILITY_C_CPP_MEMBERS = frozenset({"c", "cpp"})


def _docblock_languages() -> frozenset[str]:
    """DOC004's fenced-language buckets, normalized onto `frob.lang`
    canonical labels -- derived directly from `_PYTHON_LANGS`/`_RUST_LANGS`/
    `_TS_LANGS`/`_C_CPP_LANGS`/`_CONSOLE_LANGS`/`_CSHARP_LANGS` (never a
    hand-copied second list) so a bucket added there is picked up here
    automatically. Imported lazily -- see the module-level dependency-order
    note above.

    T-0566: `_C_CPP_LANGS` covers both `frob.lang`'s "c" and "cpp" labels
    (one merged fenced-block bucket, same "c-cpp" merge `_capability_status`
    already uses for the capability-registry facet -- see
    `_CAPABILITY_C_CPP_MEMBERS`).

    T-2906: bash's real DOC004 bucket was already `_CONSOLE_LANGS`
    (console-command drift checking, `bash`/`sh`/`shell` fence tags) --
    it was simply never unioned in here, so bash read as a fenced-block
    KNOWN_GAP despite already having a real checker. csharp gets a new
    `_CSHARP_LANGS` bucket (`_csharp_using_violations`, T-2906)."""
    from frob.gates._docblocks import (
        _C_CPP_LANGS,
        _CONSOLE_LANGS,
        _CSHARP_LANGS,
        _PYTHON_LANGS,
        _RUST_LANGS,
        _TS_LANGS,
    )

    return frozenset(
        ({"python"} if _PYTHON_LANGS else set())
        | ({"rust"} if _RUST_LANGS else set())
        | ({"typescript"} if _TS_LANGS else set())
        | (_CAPABILITY_C_CPP_MEMBERS if _C_CPP_LANGS else set())
        | ({"bash"} if _CONSOLE_LANGS else set())
        | ({"csharp"} if _CSHARP_LANGS else set())
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


# frob:ticket T-2996
def _refactor_status(language: str) -> FacetStatus:
    """T-2996: `frob.refactor` is Python-only today -- `_module_lang.
    _MODULE_LANGUAGE_ADAPTERS` has exactly one entry, and `_scan.py`'s
    single-symbol move/rename engine is Python `ast`-specific
    (`find_python_files`, `_handle_import`, ...). `.strata` is a design
    DSL with no established symbol-move/rename convention yet (unlike
    dup/arch/docblock, this is not a "the concept does not apply" case --
    a strata design element genuinely COULD be renamed/moved -- so this
    is judged a known gap, not not-applicable, distinct from how strata
    is treated by the other four facets)."""
    if language in _REFACTOR_ADAPTER_LANGUAGES:
        return _implemented(
            "frob.refactor._module_lang._MODULE_LANGUAGE_ADAPTERS entry "
            "(move-module reference scanner)"
        )
    return _known_gap(
        f"{language} has no frob.refactor reference scanner -- "
        f"move-module refuses it via RefactorError.UnsupportedLanguage "
        f"(PLATFORM001 declared boundary, not a silent no-op) and "
        f"move-symbol's engine is Python-ast-specific; tracked by T-3231 "
        f"(EPIC refactor multi-language: per-language reference scanners)"
    )


# frob:doc docs/modules/lang.md#language-support-contract
# frob:ticket T-0405
# frob:ticket T-2996
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
            FACET_REFACTOR: _refactor_status(language),
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


# --------------------------------------------------------------------------
# T-2365: the adapter-capability axis -- see ADAPTER_CAPABILITIES above.
# --------------------------------------------------------------------------

# `frob.lang._extract._WALKERS` covers every tree-sitter grammar language;
# `.strata` is handled separately by `_walk_strata.walk_strata`, which
# returns the identical `RawSymbol` shape (module docstring). Every member
# of `frob.lang.supported_languages()` therefore has a real symbol walker
# today -- there is no known gap here to derive, so this is a plain
# membership check rather than a lazy import of a registry, mirroring the
# other `_capability_*_status` helpers' "always true" branches (e.g.
# `_grammar_status` above).
_SYMBOL_WALK_LANGUAGES_NOTE = (
    "frob.lang._extract._WALKERS entry (or _walk_strata's equivalent "
    "RawSymbol-producing pairing with strata-core for .strata)"
)

# `RawSymbol.public: bool` (frob.lang._models) is a REQUIRED, non-optional
# pydantic field -- every walker (including `_walk_strata`) must set it or
# the walk itself cannot construct a `RawSymbol` at all. This is a
# structural guarantee, not a per-language registry to check membership
# against, hence the same "always true" shape as `_SYMBOL_WALK_LANGUAGES_
# NOTE` above.
_PUBLICNESS_NOTE = (
    "RawSymbol.public is a required pydantic field (frob.lang._models); "
    "every adapter walker must set a language-correct value (T-0841) to "
    "construct a RawSymbol at all"
)

# `frob.lang._extract.COMMENT_TYPES` covers every tree-sitter grammar
# language; `.strata` extracts its own whole-line `//` comments directly
# in `_walk_strata._extract_comments` (a different mechanism, same
# capability). Every registered language has one or the other.
_DOC_EXTRACT_NOTE = (
    "frob.lang._extract.COMMENT_TYPES entry, or (for .strata) "
    "_walk_strata._extract_comments's own whole-line comment scan"
)

# `frob.graph.dsl.parse_directives`/`_fold_continuations` operate on
# `RawComment.text` alone -- they have no per-language branch at all, so
# directive parsing (continuations included) works for any language whose
# comments get extracted, i.e. every language `_DOC_EXTRACT_NOTE` covers.
_DIRECTIVE_PARSE_NOTE = (
    "frob.graph.dsl.parse_directives is language-agnostic over extracted "
    "RawComment text (no per-language branch); available wherever "
    "CAPABILITY_DOC_EXTRACT holds"
)

# `frob.graph.callgraph.build_call_graph` resolves edges via bare-short-
# name matching over `RawSymbol.public`/`sig_tokens` -- also no per-
# language branch, available for every language `CAPABILITY_SYMBOL_WALK`
# covers EXCEPT `.strata`: a design file's declared constructs are not
# "calls" in the traditional sense frob.graph.callgraph's kind filter
# targets, and strata's own dependency/threat-discharge graphs
# (frob.strata._threat/_effects) already cover the equivalent ground
# under a different vocabulary (same reasoning `_capability_status`
# above already applies to strata for the FACETS axis).
_CALL_GRAPH_NOTE = (
    "frob.graph.callgraph.build_call_graph is language-agnostic over "
    "RawSymbol.public/sig_tokens (no per-language branch); available "
    "wherever CAPABILITY_SYMBOL_WALK holds"
)


def _capability_symbol_walk_status(language: str) -> CapabilityStatus:
    """Every `supported_languages()` member has a real walker -- see
    `_SYMBOL_WALK_LANGUAGES_NOTE`."""
    return _cap_implemented(CapabilityRequirement.REQUIRED, _SYMBOL_WALK_LANGUAGES_NOTE)


def _capability_publicness_status(language: str) -> CapabilityStatus:
    """`RawSymbol.public` is a required field for every walker -- see
    `_PUBLICNESS_NOTE`. T-2410 closed `.strata`'s prior placeholder:
    `_walk_strata.py` now derives `public` from each construct's own
    `clearance` clause (`node`/`store`/`queue`, the only construct kinds
    whose grammar carries one) instead of hardcoding `True` -- a real,
    language-correct rule per T-0841, not merely a required-field-shaped
    placeholder."""
    return _cap_implemented(CapabilityRequirement.REQUIRED, _PUBLICNESS_NOTE)


def _capability_doc_extract_status(language: str) -> CapabilityStatus:
    """Every `supported_languages()` member extracts comments one way or
    another -- see `_DOC_EXTRACT_NOTE`."""
    return _cap_implemented(CapabilityRequirement.REQUIRED, _DOC_EXTRACT_NOTE)


def _capability_directive_parse_status(language: str) -> CapabilityStatus:
    """Directive parsing (continuations included) rides on `CAPABILITY_
    DOC_EXTRACT`, which every language has -- see `_DIRECTIVE_PARSE_NOTE`.
    REQUIRED: this is frob's own obligation-graph DSL (`frob:doc`/
    `frob:tests`/`frob:ticket`/...), not optional tooling."""
    return _cap_implemented(CapabilityRequirement.REQUIRED, _DIRECTIVE_PARSE_NOTE)


def _capability_call_graph_status(language: str) -> CapabilityStatus:
    """Call-graph resolution is language-agnostic over symbol-walk output
    -- `.strata` is the one reasoned exemption, see `_CALL_GRAPH_NOTE`.
    T-1604: bash is a SECOND, distinct exemption -- not because calls are
    a meaningless concept for the language (they are exactly as
    meaningful as any other grammar's), but because `frob.graph.
    callgraph`'s shared token-adjacency call detector (`_called_names`,
    "identifier immediately followed by '('") structurally cannot
    recognize a bash call: bash invokes a function the same bare-word way
    it invokes any other command (`foo arg1`, never `foo(arg1)`), so no
    call in a bash `RawSymbol.body_tokens` stream ever produces the
    token shape the detector looks for. A real, disclosed shared-layer
    gap found while building T-1604 -- filed separately (this ticket's
    own scope is the bash adapter, not `frob.graph.callgraph`'s shared
    detector) rather than special-cased away quietly, per this ticket's
    own instruction that a special case is evidence the abstraction is
    wrong."""
    if language == "strata":
        return _cap_not_applicable(
            CapabilityRequirement.OPTIONAL,
            "strata design constructs are not 'calls' in the traditional "
            "sense frob.graph.callgraph's kind filter targets; strata's "
            "own dependency/threat-discharge graphs (frob.strata._threat/"
            "_effects) cover the equivalent ground under a different "
            "vocabulary",
        )
    if language == "bash":
        return _cap_known_gap(
            CapabilityRequirement.REQUIRED,
            "bash function invocation has no parenthesized call syntax "
            "('foo', not 'foo()'), so frob.graph.callgraph's shared "
            "token-adjacency call detector cannot recognize a call in "
            "bash body_tokens at all -- tracked by T-2901",
        )
    return _cap_implemented(CapabilityRequirement.REQUIRED, _CALL_GRAPH_NOTE)


# frob:ticket T-2494
def _capability_import_graph_status(language: str) -> CapabilityStatus:
    """IMPLEMENTED iff `language` has a real
    `frob.lang._extract._IMPORT_WALKERS` entry, derived directly from that
    dict's own keys (T-2494) rather than a hand-maintained membership set
    -- the T-2408 incident this replaces: a walker was added for
    typescript/rust/kotlin but this function's own hardcoded
    `{"python", "c", "cpp"}` set kept reporting them KNOWN_GAP anyway,
    because nothing forced the two to stay in sync. `.strata` has no
    `#include`/`import` analogue frob.lang.extract_imports models
    (strata's own module-dependency syntax is resolved by strata-core
    directly, not this walker) -- checked first since strata is not a
    tree-sitter grammar language and so is never a member of
    `_IMPORT_WALKERS` regardless."""
    if language == "strata":
        return _cap_not_applicable(
            CapabilityRequirement.OPTIONAL,
            "strata module dependencies are resolved by strata-core's "
            "own parser directly, not frob.lang.extract_imports's "
            "tree-sitter-only walker table",
        )
    from frob.lang._extract import _IMPORT_WALKERS

    if language in _IMPORT_WALKERS:
        return _cap_implemented(
            CapabilityRequirement.REQUIRED,
            "frob.lang._extract._IMPORT_WALKERS entry",
        )
    return _cap_known_gap(
        CapabilityRequirement.REQUIRED,
        f"{language} absent from frob.lang._extract._IMPORT_WALKERS -- "
        f"no walker registered for it yet",
    )


# T-2499: unlike `_capability_import_graph_status` above, there was no
#: existing single-source-of-truth table this status function could
#: import and derive from -- `frob.testing` exports `collect_python_
#: tests`/`collect_rust_tests`/`collect_ts_tests`/`collect_cpp_tests`/
#: `collect_kotlin_tests` as five independent module-level functions with
#: no language-keyed dispatch dict joining them (confirmed: no caller in
#: this repo dispatches a collector by language string). This is that
#: exact T-2408 incident class repeating -- `collect_kotlin_tests` landed
#: (T-2409) and this function's own hardcoded `{"python", "rust",
#: "typescript", "c", "cpp"}` set silently did not know about it, reading
#: kotlin as `KNOWN_GAP` the same day its real collector shipped. Building
#: the missing registry (rather than just adding "kotlin" to the hardcoded
#: set, which only fixes today's drift and repeats the identical failure
#: on the NEXT new collector) is the actual fix: this dict's own KEYS are
#: now the single source of truth `_capability_test_discovery_status`
#: derives from, so a future collector only needs one new entry here, in
#: the same table any other caller wanting a by-language collector
#: dispatch would also want -- not a second hardcoded set to forget.
_TEST_DISCOVERY_COLLECTORS: dict[str, str] = {
    "python": "frob.testing.collect_python_tests",
    "rust": "frob.testing.collect_rust_tests",
    "typescript": "frob.testing.collect_ts_tests",
    "c": "frob.testing.collect_cpp_tests",
    "cpp": "frob.testing.collect_cpp_tests",
    "kotlin": "frob.testing.collect_kotlin_tests",
}


# frob:ticket T-2499
# frob:tests \
# tests/test_lang_support.py::TestDeriveCapabilityRegistry.test_kotlin_test_discovery_i\
# s_implemented
# frob:tests \
# tests/test_lang_support.py::TestDeriveCapabilityRegistry.test_test_discovery_known_ga\
# p_tracks_a_language_absent_from_registry
# frob:tests \
# tests/test_lang_support.py::TestDeriveCapabilityRegistry.test_test_discovery_known_ga\
# p_when_registry_entry_is_stale
def _capability_test_discovery_status(language: str) -> CapabilityStatus:
    """IMPLEMENTED iff `language` has a real entry in
    `_TEST_DISCOVERY_COLLECTORS` (T-2499, mirroring
    `_capability_import_graph_status`'s T-2494 fix: derived from a real
    registry's keys, never a second hand-maintained membership set that
    can silently drift out of sync with the first) -- `frob.testing`
    itself exposes each collector as an independent function with no
    language-keyed dispatch dict of its own yet, so this module-level
    dict IS that missing registry (see its own comment for the T-2408/
    T-2409 incident this replaces). `.strata` design files have no
    runnable-test concept at all -- checked first, same as every other
    facet above, since strata's own module-dependency/test-discovery
    story is handled entirely outside this walker-shaped machinery."""
    if language == "strata":
        return _cap_not_applicable(
            CapabilityRequirement.OPTIONAL,
            "strata design files declare no runnable test suite of "
            "their own -- there is nothing for a test collector to find",
        )
    qualname = _TEST_DISCOVERY_COLLECTORS.get(language)
    if qualname is not None:
        # T-2499: resolve the named collector LIVE rather than trusting
        # the string alone -- a renamed/removed `frob.testing` function
        # this table's own entry still names would otherwise silently
        # read as IMPLEMENTED against a dead reference, exactly the kind
        # of drift this whole module exists to catch.
        import frob.testing as _testing_mod

        attr_name = qualname.rsplit(".", 1)[-1]
        # frob:waive OPAQUE001 reason="deliberate dynamic lookup, not a fail-closed \
        # blind spot -- attr_name only ever comes from this module's own \
        # _TEST_DISCOVERY_COLLECTORS dict literal (never external/attacker input), and \
        # the point of resolving it dynamically IS the drift check: a static literal \
        # getattr would defeat catching a renamed/removed frob.testing function, which \
        # is exactly the staleness bug this whole function exists to prevent"
        if getattr(_testing_mod, attr_name, None) is not None:
            return _cap_implemented(
                CapabilityRequirement.REQUIRED,
                f"{qualname} (frob.lang._support._TEST_DISCOVERY_COLLECTORS entry)",
            )
        return _cap_known_gap(
            CapabilityRequirement.REQUIRED,
            f"{language}'s _TEST_DISCOVERY_COLLECTORS entry names "
            f"{qualname}, which no longer resolves on frob.testing -- "
            f"the registry entry is stale, fix it or remove it",
        )
    return _cap_known_gap(
        CapabilityRequirement.REQUIRED,
        f"{language} absent from frob.lang._support._TEST_DISCOVERY_"
        f"COLLECTORS -- no frob.testing collect_*_tests entrypoint "
        f"registered for it yet",
    )


# frob:doc docs/modules/lang.md#adapter-capability-contract-t-2365
# frob:ticket T-2365
# frob:tests tests/test_lang_support.py::TestDeriveCapabilityRegistry.test_covers_every_supported_language  # noqa: E501
def derive_capability_registry() -> dict[str, AdapterCapabilitySupport]:
    """One `AdapterCapabilitySupport` per `frob.lang.supported_languages()`
    member -- the capability-axis analogue of `derive_language_registry`.
    Every cell is derived from the real, live adapter machinery it names
    (never a hand-copied constant); see each `_capability_*_status` helper
    above."""
    from frob.lang import supported_languages

    registry: dict[str, AdapterCapabilitySupport] = {}
    for language in sorted(supported_languages()):
        capabilities = {
            CAPABILITY_SYMBOL_WALK: _capability_symbol_walk_status(language),
            CAPABILITY_PUBLICNESS: _capability_publicness_status(language),
            CAPABILITY_DOC_EXTRACT: _capability_doc_extract_status(language),
            CAPABILITY_DIRECTIVE_PARSE: _capability_directive_parse_status(language),
            CAPABILITY_CALL_GRAPH: _capability_call_graph_status(language),
            CAPABILITY_IMPORT_GRAPH: _capability_import_graph_status(language),
            CAPABILITY_TEST_DISCOVERY: _capability_test_discovery_status(language),
        }
        registry[language] = AdapterCapabilitySupport(
            language=language, capabilities=capabilities
        )
    _log.info(
        "derive_capability_registry: %d language(s) registered",
        len(registry),
    )
    return registry


# frob:doc docs/modules/lang.md#adapter-capability-contract-t-2365
# frob:ticket T-2365
# frob:tests tests/test_lang_support.py::TestCapabilityConformanceViolations.test_missing_capability_fails  # noqa: E501
# frob:tests tests/test_lang_support.py::TestCapabilityConformanceViolations.test_fully_registered_language_passes  # noqa: E501
def capability_conformance_violations(
    registry: dict[str, AdapterCapabilitySupport],
) -> tuple[str, ...]:
    """One message per unaccounted-for `(language, capability)` cell in
    `registry` -- the capability-axis analogue of `conformance_violations`.
    Fail-closed the identical way: a missing cell or an unreasoned
    `NOT_APPLICABLE`/`KNOWN_GAP` both produce a message; a `KNOWN_GAP` WITH
    a detail does not."""
    violations: list[str] = []
    for language, support in sorted(registry.items()):
        for capability in support.missing_capabilities():
            violations.append(
                f"{language}: capability '{capability}' has no "
                f"AdapterCapabilitySupport entry at all -- every "
                f"registered language must declare every capability as "
                f"implemented, not-applicable (with a reason), or a "
                f"known gap (with a tracking ticket)"
            )
        for capability in support.unreasoned_capabilities():
            violations.append(
                f"{language}: capability '{capability}' is not-"
                f"applicable/known-gap but carries no reason -- an "
                f"unreasoned exemption is as unaccountable as a "
                f"missing cell"
            )
    return tuple(violations)


# --------------------------------------------------------------------------
# T-2996 part 2/3: the PACKAGE axis -- registers which `frob.*` packages
# carry per-language specialisation at all, and whether that specialisation
# is already accounted for by FACETS/ADAPTER_CAPABILITIES, or is a reasoned
# exemption. Part 1 (FACET_REFACTOR above) fixed one invisible gap;
# `refactor` had ZERO language literals to find, so no literal-scanning
# audit alone would ever have caught it. This registry is therefore the
# DECLARED half of the fix -- a maintainer judges and records each
# package once -- and `unfaceted_packages` below is the DETECTION half:
# a cross-check that fails when a package acquires language-literal
# branching the registry does not yet know about, so the registry cannot
# silently fall behind reality the way `refactor`'s Python-only assumption
# fell behind for years.
#
# T-2996 2026-08-26 measurement (language-literal density per package,
# `frob.lang` itself excluded as the source of truth every other entry
# here is measured against):
#
#     321  frob.vet          82  frob.lang (source of truth, not audited)
#      41  frob.gates        40  frob.arch          38  frob.app
#      25  frob.perf         21  frob.strata        17  frob.dup
#      10  frob._cli_parsers  9  frob.check          9  frob.graph
#       8  frob.testing       4  frob.policy         0  frob.refactor (!)
#
# `unfaceted_packages`'s AST-based detection cross-check (below) also
# turned up 5 more packages the density survey's manual grep pass missed:
# frob.bind, frob.deploy, frob.docs, frob.natives, frob.xref -- each has
# exactly one or a few language literals, which is precisely why they did
# not surface in a coarse density ranking; every one is registered below
# too, and this is the cross-check doing its job (T-2996 part 3): a
# registry built by hand alone would have missed these five permanently.
#
# Each entry's `detail` records the actual reasoning, not just the verdict.
# --------------------------------------------------------------------------


# frob:doc docs/modules/lang.md#package-language-axis-t-2996
# frob:ticket T-2996
# frob:tests tests/test_lang_support.py::TestPackageAudit.test_every_measured_package_is_registered  # noqa: E501
class PackageLanguageAxis(StrEnum):
    """How a package's per-language specialisation is accounted for
    (T-2996 part 2): `FACET`/`CAPABILITY` mean an existing FACETS/
    ADAPTER_CAPABILITIES cell already tracks it end to end; `AGNOSTIC`
    means the package contains language LITERALS (constants, choices
    lists, extension tables) but no per-language behavioral gap for
    `conformance_violations`/`capability_conformance_violations` to miss
    -- a judged exemption, recorded with a reason, never silence."""

    FACET = "facet"
    CAPABILITY = "capability"
    AGNOSTIC = "agnostic"


# frob:doc docs/modules/lang.md#package-language-axis-t-2996
# frob:ticket T-2996
# frob:tests tests/test_lang_support.py::TestPackageAudit.test_every_measured_package_is_registered  # noqa: E501
class PackageAudit(BaseModel):
    """One package's T-2996 part-2 classification: which axis accounts
    for its per-language specialisation, plus the reasoning."""

    model_config = ConfigDict(frozen=True)

    axis: PackageLanguageAxis
    detail: str


# frob:doc docs/modules/lang.md#package-language-axis-t-2996
# frob:ticket T-2996
# frob:tests tests/test_lang_support.py::TestPackageAudit.test_every_measured_package_is_registered  # noqa: E501
#: T-2996 part 2's declared registry: every `frob.*` package this ticket's
#: survey found branching on language identity (plus `frob.refactor`,
#: which branches on nothing but is Python-only anyway -- the invisible
#: case FACET_REFACTOR above exists to cover), mapped to how its
#: specialisation is accounted for. `frob.lang` itself is the source of
#: truth every FACETS/ADAPTER_CAPABILITIES cell derives from and is not
#: a member here for the same reason `conformance_violations` does not
#: audit itself.
LANGUAGE_SENSITIVE_PACKAGES: dict[str, PackageAudit] = {
    "frob.vet": PackageAudit(
        axis=PackageLanguageAxis.FACET,
        detail=(
            "frob.vet._capability_registry.LANGUAGES IS FACET_CAPABILITY's "
            "own source registry -- this is the facet, not a package that "
            "needs one."
        ),
    ),
    "frob.dup": PackageAudit(
        axis=PackageLanguageAxis.FACET,
        detail=(
            "frob.dup._exhaustiveness.LANGUAGES IS FACET_DUP's own source registry."
        ),
    ),
    "frob.arch": PackageAudit(
        axis=PackageLanguageAxis.FACET,
        detail=(
            "frob.arch's per-language rule-submodule dispatch IS "
            "FACET_ARCH's own source (`_ARCH_DISPATCHED_LANGUAGES`)."
        ),
    ),
    "frob.gates": PackageAudit(
        axis=PackageLanguageAxis.FACET,
        detail=(
            "frob.gates._docblocks's fenced-language buckets ARE "
            "FACET_DOCBLOCK's own source (`_docblock_languages`); the "
            "rest of frob.gates's language literals are LANG001/LANG002/"
            "LANG003 themselves (this module's own gate, not a second "
            "specialisation needing a facet)."
        ),
    ),
    "frob.refactor": PackageAudit(
        axis=PackageLanguageAxis.FACET,
        detail=(
            "FACET_REFACTOR (T-2996 part 1, added above) covers this "
            "directly -- the package with ZERO language literals that "
            "was nonetheless Python-only, the finding that motivated "
            "this whole ticket."
        ),
    ),
    "frob.graph": PackageAudit(
        axis=PackageLanguageAxis.CAPABILITY,
        detail=(
            "frob.graph.callgraph's per-language dispatch and extension "
            "table back CAPABILITY_CALL_GRAPH directly; frob.graph.dsl's "
            "directive parsing backs CAPABILITY_DIRECTIVE_PARSE. Both "
            "are ADAPTER_CAPABILITIES (T-2365) entries already."
        ),
    ),
    "frob.testing": PackageAudit(
        axis=PackageLanguageAxis.CAPABILITY,
        detail=(
            "frob.testing's collect_*_tests entrypoints "
            "(`_TEST_DISCOVERY_COLLECTORS`) back CAPABILITY_TEST_"
            "DISCOVERY directly -- kotlin's collector (T-2409) is the "
            "concrete example a prior known-gap here closed against."
        ),
    ),
    "frob.app": PackageAudit(
        axis=PackageLanguageAxis.AGNOSTIC,
        detail=(
            "frob.app.check_runner's per-language project-toolchain "
            "sentinels (Cargo.toml/CMakeLists.txt/pyproject.toml/"
            "package.json) decide WHICH gate stages a detected repo "
            "runs -- a symmetric membership test over frob.lang."
            "supported_languages()'s own set, not a place a language "
            "can be partially or incorrectly supported independent of "
            "grammar. A language missing here is a language missing "
            "from frob.lang itself (LANG002 territory), not a new gap "
            "this axis would add."
        ),
    ),
    "frob.check": PackageAudit(
        axis=PackageLanguageAxis.AGNOSTIC,
        detail=(
            "frob.check.__init__'s detect_project_type is the same "
            "project-toolchain-sentinel shape as frob.app.check_runner "
            "(their own T-0404 finding-11 docstring says the two used to "
            "disagree and were unified) -- same reasoning as frob.app "
            "above, not a second axis."
        ),
    ),
    "frob._cli_parsers": PackageAudit(
        axis=PackageLanguageAxis.AGNOSTIC,
        detail=(
            "argparse `choices=[...]` lists on --lang flags (xref, "
            "cycle, check) restrict which languages a CLI FLAG accepts; "
            "they gate presentation of an underlying capability "
            "(FACET_GRAMMAR/CAPABILITY_CALL_GRAPH) that already has its "
            "own cell, not a second implementation. MEASURED GAP, "
            "recorded not fixed here (out of T-2996's scope, which owns "
            "frob.lang's facet registry, not frob._cli_parsers): several "
            "choices lists (e.g. xref --lang) hard-code "
            "['python','cpp','c'] and have drifted narrower than "
            "frob.lang.supported_languages() -- filed as T-3233."
        ),
    ),
    "frob.strata": PackageAudit(
        axis=PackageLanguageAxis.AGNOSTIC,
        detail=(
            "frob.strata's language literals (`_code_binding.py`'s "
            "hard-coded 'python' import resolution, `_cve_fingerprint."
            "py`'s per-language CVE catalog) are strata's OWN domain "
            "reasoning about which host languages a design binds "
            "code to -- not frob analyzing that language's own source "
            "the way FACETS/ADAPTER_CAPABILITIES do. Distinct question "
            "from 'does frob support language X', same distinction "
            "already drawn for strata's own NOT_APPLICABLE cells "
            "elsewhere in this module."
        ),
    ),
    "frob.perf": PackageAudit(
        axis=PackageLanguageAxis.AGNOSTIC,
        detail=(
            "frob.perf._collectors._LANGUAGE_ADAPTER_EXTENSIONS picks a "
            "hot-graph ADAPTER class for `frob perf collect`, an opt-in "
            "profiling tool gated by which profiler actually ran, not a "
            "conformance requirement every supported language must meet "
            "the way FACETS/ADAPTER_CAPABILITIES are. MEASURED GAP, "
            "recorded not fixed here: it only covers python/typescript/"
            "rust/kotlin (4 of 9) -- filed as T-3234 rather than judged "
            "in scope for this ticket's facet registry."
        ),
    ),
    "frob.policy": PackageAudit(
        axis=PackageLanguageAxis.AGNOSTIC,
        detail=(
            "frob.policy's per-language import-statement regexes are a "
            "SECOND, parallel import extractor alongside frob.lang."
            "extract_imports (which backs CAPABILITY_IMPORT_GRAPH) -- "
            "functionally the same axis, duplicated rather than reused. "
            "That duplication is itself a finding (NO DUPLICATION), not "
            "a facet gap; recorded and filed as T-3235 rather than fixed "
            "in this ticket's scope (frob.lang's facet registry, not "
            "frob.policy's implementation)."
        ),
    ),
    "frob.docs": PackageAudit(
        axis=PackageLanguageAxis.AGNOSTIC,
        detail=(
            "frob.docs.__init__.extract_docstrings filters to "
            "`parsed.language != 'python': return []` -- every other "
            "language's docstrings are silently unextracted. MEASURED "
            "GAP, recorded not fixed here -- filed as T-3232."
        ),
    ),
    "frob.xref": PackageAudit(
        axis=PackageLanguageAxis.AGNOSTIC,
        detail=(
            "frob.xref.__init__._LANG_EXTS (the --lang filter map) only "
            "covers python/c/cpp/strata; _ALL_EXTS (the actual "
            "collection/search set) is the full frob.lang registry, so "
            "this is a --lang FILTER gap, not a coverage gap -- xref "
            "collects and searches every language, it just cannot filter "
            "to typescript/rust/kotlin/csharp/bash individually. MEASURED "
            "GAP, recorded not fixed here -- filed as T-3232."
        ),
    ),
    "frob.bind": PackageAudit(
        axis=PackageLanguageAxis.AGNOSTIC,
        detail=(
            "frob.bind's 'cpp'/'rust' literals are PyO3-binding-drift-"
            "specific (Python<->Rust FFI signature comparison) -- the "
            "tool's whole domain is that one language pair, not a "
            "general per-language capability with other-language cells "
            "to fill."
        ),
    ),
    "frob.deploy": PackageAudit(
        axis=PackageLanguageAxis.AGNOSTIC,
        detail=(
            "frob.deploy._drift.py's 'strata' literal is a `frob.toml` "
            "TOML section-key NAME (`data.get('strata', {})`), not a "
            "language dispatch -- deploy drift only ever concerns "
            "`.strata` design models by definition (T-2996's own "
            "detection heuristic false-positives on this one: a string "
            "constant that happens to equal a language name but names a "
            "config key, not a branch on language identity)."
        ),
    ),
    "frob.natives": PackageAudit(
        axis=PackageLanguageAxis.AGNOSTIC,
        detail=(
            "frob.natives._build.py's 'rust' literal gates a skip-check "
            "for non-rust native specs -- native-extension building is "
            "inherently rust-specific today (Cargo/PyO3 vendoring), not "
            "a general per-language capability with other-language cells "
            "expected."
        ),
    ),
}


# frob:doc docs/modules/lang.md#package-language-axis-t-2996
# frob:ticket T-2996
# frob:tests tests/test_lang_support.py::TestPackageAudit.test_must_fire_unregistered_language_branching  # noqa: E501
# frob:tests tests/test_lang_support.py::TestPackageAudit.test_must_stay_quiet_agnostic_package  # noqa: E501
# frob:waive ARCH001 reason="one cohesive AST-based scan (default-resolve known_languages/registry, then walk each package dir's .py files looking for a language-literal ast.Constant) -- splitting the default-resolution preamble or the inner per-file AST walk into a second function would fragment one linear pass into two callers that must always run together, the opposite of T-2996's own no-duplication rule"  # noqa: E501
def unfaceted_packages(
    src_root: Path,
    known_languages: frozenset[str] | None = None,
    registry: dict[str, PackageAudit] | None = None,
) -> tuple[str, ...]:
    """T-2996 part 3's detection cross-check: `frob.*` packages under
    `src_root` (a `pathlib.Path` to a `src/frob` directory) whose source
    contains a language-name string literal (compared against
    `known_languages`, default `frob.lang.supported_languages()`) but
    which have NO entry in `LANGUAGE_SENSITIVE_PACKAGES` (`registry`,
    default the module-level registry).

    Detection is AST-based (`ast.walk` over each file's parsed module,
    matching `ast.Constant` string values), never a text/regex scan --
    this repo's standing rule that checks compare SYMBOLS, not
    substrings, applies here too: a language name appearing inside a
    comment, a docstring example, or as a substring of an unrelated
    identifier never triggers this, only an actual string literal in the
    package's parsed AST.

    This is the half that keeps `LANGUAGE_SENSITIVE_PACKAGES` honest: a
    package can be missing from the registry (the must-fire case) or a
    package the registry already accounts for stays quiet even though it
    is full of language literals (the must-stay-quiet case) -- see the
    two fixtures this docstring's `frob:tests` directives bind.
    """
    import ast

    if known_languages is None:
        from frob.lang import supported_languages

        known_languages = frozenset(supported_languages())
    if registry is None:
        registry = LANGUAGE_SENSITIVE_PACKAGES

    hits: list[str] = []
    for package_dir in sorted(p for p in src_root.iterdir() if p.is_dir()):
        if package_dir.name.startswith("_") or package_dir.name == "lang":
            continue
        package_name = f"frob.{package_dir.name}"
        if package_name in registry:
            continue
        found_literal = False
        for py_file in sorted(package_dir.rglob("*.py")):
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError, OSError) as exc:
                _log.debug(
                    "unfaceted_packages: skipping unparseable %s: %s",
                    py_file,
                    exc,
                )
                continue
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                    and node.value in known_languages
                ):
                    found_literal = True
                    break
            if found_literal:
                break
        if found_literal:
            hits.append(package_name)
    _log.info(
        "unfaceted_packages: %d package(s) branch on language identity "
        "with no LANGUAGE_SENSITIVE_PACKAGES entry",
        len(hits),
    )
    return tuple(hits)
