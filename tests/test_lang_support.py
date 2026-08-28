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

    # frob:ticket T-2906
    def test_bash_and_csharp_capability_dup_docblock_are_implemented(self) -> None:
        """T-2906: bash and csharp each registered a real `frob.lang`
        grammar/walker (T-1604/T-1600) but were not wired into the three
        OTHER FACETS-axis subsystems -- real `LANGUAGES` entries in
        `frob.vet._capability_registry`/`frob.dup._exhaustiveness` plus a
        real DOC004 fenced-language bucket for each (bash's own
        pre-existing `_CONSOLE_LANGS`, csharp's new `_CSHARP_LANGS`) close
        the gap for real, not just via a reasoned KNOWN_GAP citation."""
        registry = derive_language_registry()
        for language in ("bash", "csharp"):
            support = registry[language]
            assert support.facets["capability"].state == FacetState.IMPLEMENTED
            assert support.facets["dup"].state == FacetState.IMPLEMENTED
            assert support.facets["docblock"].state == FacetState.IMPLEMENTED
            # frob.arch's multi-language dispatch is a separate, already
            # tracked epic (T-0329) -- not this ticket's scope.
            assert support.facets["arch"].state == FacetState.KNOWN_GAP


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


# frob:ticket T-2996
class TestPackageAudit:
    """T-2996 part 2/3: `LANGUAGE_SENSITIVE_PACKAGES` (the declared
    registry) plus `unfaceted_packages` (the detection cross-check)."""

    # frob:ticket T-2996
    def test_every_measured_package_is_registered(self) -> None:
        """Every package T-2996's survey found branching on language
        identity -- plus `frob.refactor`, the invisible zero-literal
        case -- has a `LANGUAGE_SENSITIVE_PACKAGES` entry with a non-
        blank reason. A hand-built registry with a blank detail is as
        unaccountable as a missing FACETS cell."""
        from frob.lang._support import LANGUAGE_SENSITIVE_PACKAGES

        expected = {
            "frob.vet",
            "frob.dup",
            "frob.arch",
            "frob.gates",
            "frob.refactor",
            "frob.graph",
            "frob.testing",
            "frob.app",
            "frob.check",
            "frob._cli_parsers",
            "frob.strata",
            "frob.perf",
            "frob.policy",
            "frob.docs",
            "frob.xref",
            "frob.bind",
            "frob.deploy",
            "frob.natives",
        }
        assert expected <= set(LANGUAGE_SENSITIVE_PACKAGES)
        for name, audit in LANGUAGE_SENSITIVE_PACKAGES.items():
            assert audit.detail.strip(), f"{name} has a blank audit detail"

    # frob:ticket T-2996
    def test_must_fire_unregistered_language_branching(self, tmp_path) -> None:  # noqa: ANN001
        """Must-fire fixture: a package with real language branching and
        NO registry entry is flagged."""
        from frob.lang._support import unfaceted_packages

        pkg = tmp_path / "frob_widget"
        pkg.mkdir()
        (pkg / "_dispatch.py").write_text(
            "def handle(language):\n"
            "    if language == 'python':\n"
            "        return 1\n"
            "    return 0\n"
        )
        hits = unfaceted_packages(
            tmp_path, known_languages=frozenset({"python", "rust"}), registry={}
        )
        assert "frob.frob_widget" in hits

    # frob:ticket T-2996
    def test_must_stay_quiet_agnostic_package(self, tmp_path) -> None:  # noqa: ANN001
        """Must-stay-quiet fixture: a genuinely language-agnostic package
        (no language-name string literal in its AST at all) produces no
        hit, even with an empty registry -- it was never a candidate."""
        from frob.lang._support import unfaceted_packages

        pkg = tmp_path / "frob_quiet"
        pkg.mkdir()
        (pkg / "_util.py").write_text("def add(a, b):\n    return a + b\n")
        hits = unfaceted_packages(
            tmp_path, known_languages=frozenset({"python", "rust"}), registry={}
        )
        assert "frob.frob_quiet" not in hits

    # frob:ticket T-2996
    def test_registered_package_never_flagged_even_with_literals(
        self, tmp_path
    ) -> None:
        """A package WITH language literals but a registry entry already
        covering it stays quiet -- the registry, once declared, is
        trusted; only an UNregistered package with literals fires."""
        from frob.lang._support import (
            PackageAudit,
            PackageLanguageAxis,
            unfaceted_packages,
        )

        pkg = tmp_path / "frob_covered"
        pkg.mkdir()
        (pkg / "_dispatch.py").write_text("LANG = 'python'\n")
        registry = {
            "frob.frob_covered": PackageAudit(
                axis=PackageLanguageAxis.AGNOSTIC, detail="fixture: pre-registered"
            )
        }
        hits = unfaceted_packages(
            tmp_path, known_languages=frozenset({"python"}), registry=registry
        )
        assert hits == ()

    # frob:ticket T-2996
    def test_real_repo_source_tree_is_fully_registered(self) -> None:
        """The actual `src/frob` tree produces zero hits against the
        live `LANGUAGE_SENSITIVE_PACKAGES` registry -- the real-world
        instance of the must-stay-quiet property above, over frob's own
        source rather than a synthetic fixture."""
        from pathlib import Path

        from frob.lang._support import unfaceted_packages

        src_root = Path(__file__).resolve().parent.parent / "src" / "frob"
        assert unfaceted_packages(src_root) == ()


# frob:ticket T-2996
def test_refactor_adapter_languages_matches_live_registry() -> None:
    """`_REFACTOR_ADAPTER_LANGUAGES` (the hand-mirrored set `_refactor_
    status` uses to avoid a frob.lang<->frob.refactor import cycle) must
    stay in sync with `frob.refactor._module_lang.supported_languages()`
    -- the live source of truth it mirrors. This import is safe HERE
    (a test module, not `frob.lang._support` itself) precisely because
    the cycle risk is specific to `frob.lang` importing `frob.refactor`
    back, not to anything importing both."""
    from frob.lang._support import _REFACTOR_ADAPTER_LANGUAGES
    from frob.refactor._module_lang import supported_languages as refactor_languages

    assert _REFACTOR_ADAPTER_LANGUAGES == refactor_languages()
