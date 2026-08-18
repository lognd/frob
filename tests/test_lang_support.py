"""Tests for frob.lang._support -- the T-0405 LanguageSupport contract, plus
the T-2365 adapter-capability axis (ADAPTER_CAPABILITIES/
AdapterCapabilitySupport/derive_capability_registry)."""

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
from frob.lang._support import (
    ADAPTER_CAPABILITIES,
    AdapterCapabilitySupport,
    CapabilityRequirement,
    CapabilityStatus,
    capability_conformance_violations,
    derive_capability_registry,
)


# frob:ticket T-0405
# frob:ticket T-0406
def _full_status() -> dict[str, FacetStatus]:
    """A fully-registered set of facet statuses (fixture helper)."""
    return {
        facet: FacetStatus(state=FacetState.IMPLEMENTED, detail="ok")
        for facet in FACETS
    }


# frob:ticket T-0405
# frob:ticket T-0406
class TestDeriveLanguageRegistry:
    """`derive_language_registry` covers every `frob.lang` grammar language."""

    # frob:ticket T-0405
    # frob:ticket T-0406
    def test_covers_every_supported_language(self) -> None:
        registry = derive_language_registry()
        assert set(registry) == set(supported_languages())

    # frob:ticket T-0405
    # frob:ticket T-0406
    def test_every_language_declares_every_facet(self) -> None:
        registry = derive_language_registry()
        for support in registry.values():
            assert set(support.facets) == set(FACETS)

    # frob:ticket T-0405
    # frob:ticket T-0406
    def test_real_registry_has_no_conformance_violations(self) -> None:
        """Every cell in the real, derived registry is accounted for --
        implemented, a reasoned not-applicable, or a ticketed known gap."""
        registry = derive_language_registry()
        assert conformance_violations(registry) == ()

    # frob:ticket T-0566
    def test_c_and_cpp_docblock_facet_is_implemented(self) -> None:
        """T-0566: c/cpp used to be a known_gap on the docblock facet
        (LANG003) citing a bogus, non-existent ticket id; the new
        `_C_CPP_LANGS` bucket in `frob.gates._docblocks` makes both real
        entries in the derived registry."""
        registry = derive_language_registry()
        assert registry["c"].facets["docblock"].state == FacetState.IMPLEMENTED
        assert registry["cpp"].facets["docblock"].state == FacetState.IMPLEMENTED


# frob:ticket T-0405
# frob:ticket T-0406
class TestConformanceViolations:
    """Fixture-language counterexamples (T-0405 acceptance criteria)."""

    # frob:ticket T-0405
    # frob:ticket T-0406
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
    # frob:ticket T-0406
    def test_fully_registered_language_passes(self) -> None:
        """A fixture language with every facet implemented passes cleanly."""
        registry = {
            "fixture-lang": LanguageSupport(
                language="fixture-lang", facets=_full_status()
            )
        }
        assert conformance_violations(registry) == ()

    # frob:ticket T-0405
    # frob:ticket T-0406
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
    # frob:ticket T-0406
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


# frob:ticket T-2365
def _full_capability_status() -> dict[str, CapabilityStatus]:
    """A fully-registered set of capability statuses (fixture helper),
    mirroring `_full_status` above for the capability axis."""
    return {
        capability: CapabilityStatus(
            requirement=CapabilityRequirement.REQUIRED,
            state=FacetState.IMPLEMENTED,
            detail="ok",
        )
        for capability in ADAPTER_CAPABILITIES
    }


# frob:ticket T-2365
class TestDeriveCapabilityRegistry:
    """`derive_capability_registry` covers every `frob.lang` grammar
    language, the capability-axis analogue of `TestDeriveLanguageRegistry`."""

    # frob:ticket T-2365
    def test_covers_every_supported_language(self) -> None:
        registry = derive_capability_registry()
        assert set(registry) == set(supported_languages())

    # frob:ticket T-2365
    def test_every_language_declares_every_capability(self) -> None:
        registry = derive_capability_registry()
        for support in registry.values():
            assert set(support.capabilities) == set(ADAPTER_CAPABILITIES)

    # frob:ticket T-2365
    def test_real_registry_has_no_conformance_violations(self) -> None:
        """Every cell in the real, derived capability registry is
        accounted for -- implemented, a reasoned not-applicable, or a
        ticketed known gap. This is the STRUCTURAL half of T-2365's
        acceptance criteria; the BEHAVIORAL half lives in
        tests/test_lang_conformance_gate.py's TestCapabilityConformanceGate."""
        registry = derive_capability_registry()
        assert capability_conformance_violations(registry) == ()

    # frob:ticket T-2365
    def test_strata_call_graph_is_not_applicable(self) -> None:
        """strata design constructs are not 'calls' -- a reasoned
        not-applicable, not a gap (per epic T-2391's doctrine, never a
        silent skip)."""
        registry = derive_capability_registry()
        status = registry["strata"].capabilities["call_graph"]
        assert status.state == FacetState.NOT_APPLICABLE
        assert status.detail.strip()

    # frob:ticket T-2494
    def test_typescript_import_graph_is_implemented(self) -> None:
        """T-2494: typescript has a real frob.lang._extract._IMPORT_
        WALKERS entry (T-2408) -- this capability derives its
        implemented-language set from that dict's own keys, so it
        reports IMPLEMENTED, not KNOWN_GAP, the moment a walker exists.
        Anti-regression for the exact T-2408/T-2494 incident: a walker
        landed while this status function's own hardcoded membership set
        still reported the language KNOWN_GAP because nothing forced the
        two to stay in sync."""
        registry = derive_capability_registry()
        status = registry["typescript"].capabilities["import_graph"]
        assert status.state == FacetState.IMPLEMENTED

    # frob:ticket T-2494
    def test_import_graph_known_gap_tracks_a_language_absent_from_walkers(
        self,
    ) -> None:
        """A language genuinely absent from `_IMPORT_WALKERS` still
        reports KNOWN_GAP (never silently IMPLEMENTED) -- proves the
        derivation is a real membership check against the live dict,
        not a function that always returns IMPLEMENTED regardless."""
        from unittest.mock import patch

        with patch("frob.lang._extract._IMPORT_WALKERS", {}):
            registry = derive_capability_registry()
            status = registry["typescript"].capabilities["import_graph"]
            assert status.state == FacetState.KNOWN_GAP
            assert "absent from frob.lang._extract._IMPORT_WALKERS" in status.detail

    # frob:ticket T-2499
    def test_kotlin_test_discovery_is_implemented(self) -> None:
        """T-2499: kotlin has a real `frob.testing.collect_kotlin_tests`
        collector (T-2409) -- this capability derives its implemented-
        language set from `_TEST_DISCOVERY_COLLECTORS`' own keys, so it
        reports IMPLEMENTED, not KNOWN_GAP, the moment a collector
        exists. Anti-regression for the exact T-2408/T-2494 incident
        class repeating here: a collector landed the same day this
        status function's own hardcoded `{"python", "rust", "typescript",
        "c", "cpp"}` membership set still reported kotlin KNOWN_GAP."""
        registry = derive_capability_registry()
        status = registry["kotlin"].capabilities["test_discovery"]
        assert status.state == FacetState.IMPLEMENTED

    # frob:ticket T-2499
    def test_test_discovery_known_gap_tracks_a_language_absent_from_registry(
        self,
    ) -> None:
        """A language genuinely absent from `_TEST_DISCOVERY_COLLECTORS`
        still reports KNOWN_GAP (never silently IMPLEMENTED) -- proves
        the derivation is a real membership check against the live
        dict, not a function that always returns IMPLEMENTED."""
        from unittest.mock import patch

        with patch("frob.lang._support._TEST_DISCOVERY_COLLECTORS", {}):
            registry = derive_capability_registry()
            status = registry["kotlin"].capabilities["test_discovery"]
            assert status.state == FacetState.KNOWN_GAP
            assert (
                "absent from frob.lang._support._TEST_DISCOVERY_COLLECTORS"
                in status.detail
            )

    # frob:ticket T-2499
    def test_test_discovery_known_gap_when_registry_entry_is_stale(self) -> None:
        """A `_TEST_DISCOVERY_COLLECTORS` entry naming a `frob.testing`
        attribute that no longer exists reports KNOWN_GAP, not a stale
        IMPLEMENTED -- the registry entry itself is verified LIVE against
        `frob.testing`, not trusted as a string alone."""
        from unittest.mock import patch

        with patch(
            "frob.lang._support._TEST_DISCOVERY_COLLECTORS",
            {"kotlin": "frob.testing.collect_nonexistent_tests"},
        ):
            registry = derive_capability_registry()
            status = registry["kotlin"].capabilities["test_discovery"]
            assert status.state == FacetState.KNOWN_GAP
            assert "no longer resolves" in status.detail


# frob:ticket T-2365
class TestCapabilityConformanceViolations:
    """Fixture-language counterexamples for the capability axis (T-2365
    acceptance criteria), mirroring `TestConformanceViolations`."""

    # frob:waive DUP001 reason="deliberate structural mirror of \
    # TestConformanceViolations.test_missing_facet_fails, matching \
    # capability_conformance_violations' own deliberate mirror of \
    # conformance_violations (see that function's DUP001 waiver in \
    # src/frob/lang/_support.py) -- proving the two axes' fail-closed behavior stays \
    # in parity is the point, not incidental copy-paste"
    # frob:ticket T-2365
    def test_missing_capability_fails(self) -> None:
        incomplete = dict(_full_capability_status())
        del incomplete["call_graph"]
        registry = {
            "fixture-lang": AdapterCapabilitySupport(
                language="fixture-lang", capabilities=incomplete
            )
        }
        violations = capability_conformance_violations(registry)
        assert len(violations) == 1
        assert "fixture-lang" in violations[0]
        assert "call_graph" in violations[0]

    # frob:ticket T-2365
    def test_fully_registered_language_passes(self) -> None:
        registry = {
            "fixture-lang": AdapterCapabilitySupport(
                language="fixture-lang", capabilities=_full_capability_status()
            )
        }
        assert capability_conformance_violations(registry) == ()

    # frob:ticket T-2365
    def test_unreasoned_known_gap_fails(self) -> None:
        """T-2365's own stated core risk: a conformance suite that passes
        because it asks nothing. A fixture adapter that DECLARES
        `symbol_walk` as `KNOWN_GAP` with NO reason (the exact shape a
        half-added adapter would produce) must fail here, not pass
        silently -- the structural half of the must-fail positive control
        (`tests/test_lang_conformance_gate.py::TestCapabilityConformanceGate`
        carries the BEHAVIORAL half: a capability that claims IMPLEMENTED
        but does not actually work)."""
        capabilities = dict(_full_capability_status())
        capabilities["symbol_walk"] = CapabilityStatus(
            requirement=CapabilityRequirement.REQUIRED,
            state=FacetState.KNOWN_GAP,
            detail="",
        )
        registry = {
            "fixture-lang": AdapterCapabilitySupport(
                language="fixture-lang", capabilities=capabilities
            )
        }
        violations = capability_conformance_violations(registry)
        assert len(violations) == 1
        assert "symbol_walk" in violations[0]
