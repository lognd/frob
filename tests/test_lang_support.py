"""Tests for frob.lang._support -- the T-0405 LanguageSupport contract."""

from __future__ import annotations

from frob.lang import (
    FACETS,
    FacetState,
    FacetStatus,
    LanguageSupport,
    conformance_violations,
    derive_language_registry,
    supported_languages,
)


# frob:ticket T-0405
def _full_status() -> dict[str, FacetStatus]:
    """A fully-registered set of facet statuses (fixture helper)."""
    return {
        facet: FacetStatus(state=FacetState.IMPLEMENTED, detail="ok")
        for facet in FACETS
    }


# frob:ticket T-0405
class TestDeriveLanguageRegistry:
    """`derive_language_registry` covers every `frob.lang` grammar language."""

    # frob:ticket T-0405
    def test_covers_every_supported_language(self) -> None:
        registry = derive_language_registry()
        assert set(registry) == set(supported_languages())

    # frob:ticket T-0405
    def test_every_language_declares_every_facet(self) -> None:
        registry = derive_language_registry()
        for support in registry.values():
            assert set(support.facets) == set(FACETS)

    # frob:ticket T-0405
    def test_real_registry_has_no_conformance_violations(self) -> None:
        """Every cell in the real, derived registry is accounted for --
        implemented, a reasoned not-applicable, or a ticketed known gap."""
        registry = derive_language_registry()
        assert conformance_violations(registry) == ()


# frob:ticket T-0405
class TestConformanceViolations:
    """Fixture-language counterexamples (T-0405 acceptance criteria)."""

    # frob:ticket T-0405
    def test_missing_facet_fails(self) -> None:
        """A fixture language registered with a missing facet (the
        resolver-omission incident class) FAILS conformance, naming the
        missing facet."""
        incomplete = dict(_full_status())
        del incomplete["arch"]
        registry = {
            "fixture-lang": LanguageSupport(language="fixture-lang", facets=incomplete)
        }
        violations = conformance_violations(registry)
        assert len(violations) == 1
        assert "fixture-lang" in violations[0]
        assert "arch" in violations[0]

    # frob:ticket T-0405
    def test_fully_registered_language_passes(self) -> None:
        """A fixture language with every facet implemented passes cleanly."""
        registry = {
            "fixture-lang": LanguageSupport(
                language="fixture-lang", facets=_full_status()
            )
        }
        assert conformance_violations(registry) == ()

    # frob:ticket T-0405
    def test_unreasoned_known_gap_fails(self) -> None:
        """A KNOWN_GAP/NOT_APPLICABLE cell with a blank detail is exactly
        as unaccountable as a missing cell."""
        facets = dict(_full_status())
        facets["dup"] = FacetStatus(state=FacetState.KNOWN_GAP, detail="")
        registry = {
            "fixture-lang": LanguageSupport(language="fixture-lang", facets=facets)
        }
        violations = conformance_violations(registry)
        assert len(violations) == 1
        assert "dup" in violations[0]

    # frob:ticket T-0405
    def test_reasoned_known_gap_passes(self) -> None:
        """A KNOWN_GAP cell WITH a reason is accounted for, not a violation."""
        facets = dict(_full_status())
        facets["dup"] = FacetStatus(
            state=FacetState.KNOWN_GAP, detail="tracked by T-0001"
        )
        registry = {
            "fixture-lang": LanguageSupport(language="fixture-lang", facets=facets)
        }
        assert conformance_violations(registry) == ()
