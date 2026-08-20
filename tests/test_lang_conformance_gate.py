"""Tests for frob.gates._lang_conformance -- LANG001-LANG004 (T-0405/T-0406/
T-2365)."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._lang_conformance import (
    _BEHAVIORALLY_CHECKED_CAPABILITIES,
    _behavioral_capability_check,
    _behaviorally_checked_languages,
    capability_conformance_gate,
    lang_conformance_gate,
    project_lang_conformance_gate,
)
from frob.gates._models import Severity
from frob.lang import supported_languages
from frob.lang._support import FacetState, derive_capability_registry


# frob:ticket T-0405
class TestLangConformanceGate:
    """LANG001 over the live, real `frob.lang` language-support registry."""

    # frob:ticket T-0405
    def test_real_registry_is_clean(self) -> None:
        """The repo's own registered languages are all fully accounted
        for today -- this gate is clean, not just wired-but-untested."""
        assert lang_conformance_gate() == ()

    # frob:ticket T-0405
    def test_missing_facet_becomes_error_violation(self, monkeypatch) -> None:
        """A stand-in registry with one language missing a facet turns
        into exactly one ERROR-severity LANG001 violation."""
        import frob.gates._lang_conformance as module
        from frob.lang import FacetState, FacetStatus, LanguageSupport

        def _fake_registry():
            facets = {
                "grammar": FacetStatus(state=FacetState.IMPLEMENTED, detail="ok"),
            }
            return {"kotlin": LanguageSupport(language="kotlin", facets=facets)}

        monkeypatch.setattr(module, "derive_language_registry", _fake_registry)
        violations = module.lang_conformance_gate()
        assert len(violations) >= 1
        assert all(v.rule == "LANG001" for v in violations)
        assert all(v.severity is Severity.ERROR for v in violations)
        assert any("kotlin" in v.message for v in violations)


# frob:ticket T-0406
class TestProjectLangConformanceGate:
    """LANG002/LANG003 over a synthetic downstream repo tree (T-0406)."""

    # frob:ticket T-0406
    def test_unregistered_language_file_fails(self, tmp_path: Path) -> None:
        """A Swift file in a downstream repo -- a language frob has NO
        grammar registration for at all -- fails LANG002 by name.

        T-1234: was a `.kt` (kotlin) fixture until T-0723 gave kotlin a
        real `frob.lang` grammar registration, which made this test's own
        premise wrong (kotlin is no longer "a language frob has NO
        grammar registration for at all"). Swift stays genuinely
        unregistered, so it is the fixture now."""
        (tmp_path / "Main.swift").write_text("func main() {}\n", encoding="utf-8")
        violations = project_lang_conformance_gate(tmp_path)
        lang002 = [v for v in violations if v.rule == "LANG002"]
        assert len(lang002) == 1
        assert lang002[0].severity is Severity.ERROR
        assert "swift" in lang002[0].message
        assert lang002[0].file == "Main.swift"

    # frob:ticket T-1234
    def test_kotlin_file_no_longer_flagged_by_lang002(self, tmp_path: Path) -> None:
        """A kotlin file must NOT fire LANG002 -- kotlin has had a real
        `frob.lang` grammar registration since T-0723, so it is not one
        of `_UNREGISTERED_CANDIDATE_LANGUAGES`'s "no coverage at all"
        cases any more (the T-1234 regression: the dict still listed
        `.kt`/`.kts` after the grammar landed)."""
        (tmp_path / "Main.kt").write_text("fun main() {}\n", encoding="utf-8")
        violations = project_lang_conformance_gate(tmp_path)
        lang002 = [v for v in violations if v.rule == "LANG002"]
        assert lang002 == []

    # frob:ticket T-0406
    def test_all_conformant_project_passes(self, tmp_path: Path) -> None:
        """A repo containing only python (every facet implemented) has no
        LANG002/LANG003 findings at all."""
        (tmp_path / "app.py").write_text("def f() -> None: ...\n", encoding="utf-8")
        violations = project_lang_conformance_gate(tmp_path)
        assert violations == ()

    # frob:ticket T-0406
    # frob:ticket T-0823
    def test_present_known_gap_with_open_ticket_warns(self, tmp_path: Path) -> None:
        """A repo containing rust files (arch facet is a KNOWN_GAP naming
        the still-open T-0329, per frob's own shipped `KNOWN_GAP_TRACKING_
        TICKETS`) gets a WARN, not silence and not an error -- and this is
        true regardless of whether `tmp_path` has any ticket queue at all
        (T-0823: no queue is ever consulted)."""
        (tmp_path / "lib.rs").write_text("fn main() {}\n", encoding="utf-8")
        violations = project_lang_conformance_gate(tmp_path)
        lang003 = [v for v in violations if v.rule == "LANG003"]
        assert any(v.severity is Severity.WARN for v in lang003)
        assert not any(v.severity is Severity.ERROR for v in lang003)

    # frob:ticket T-0823
    def test_adopter_repo_with_no_frob_internal_tickets_does_not_error(
        self, tmp_path: Path
    ) -> None:
        """T-0823's core regression: `tmp_path` here is exactly the
        adopter shape -- a downstream repo with no `tickets.md` at all
        (frob-internal ticket ids like T-0329 are structurally
        unresolvable). LANG003 must not hard-error over that; the rust
        KNOWN_GAP cell still verifies cleanly against frob's own shipped
        registry, same WARN as `test_present_known_gap_with_open_ticket_
        warns` above -- proving the fix is not merely "no queue passed",
        but "no queue was ever the right thing to consult"."""
        assert not (tmp_path / "tickets.md").exists()
        (tmp_path / "lib.rs").write_text("fn main() {}\n", encoding="utf-8")
        violations = project_lang_conformance_gate(tmp_path)
        lang003 = [v for v in violations if v.rule == "LANG003"]
        assert lang003
        assert all(v.severity is Severity.WARN for v in lang003)

    # frob:ticket T-0406
    # frob:ticket T-0823
    def test_present_known_gap_with_bad_ticket_ref_errors(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """The same rust KNOWN_GAP cell, checked once frob's own
        `KNOWN_GAP_TRACKING_TICKETS` registry marks T-0329 resolved,
        escalates to ERROR -- a claimed-but-no-longer-real gap is unsound
        coverage, not tracked coverage. T-0823: this is now frob's own
        shipped fact, not the checked repo's queue -- flip the constant,
        not a queue entry, to prove the anti-lie check still fires."""
        import frob.gates._lang_conformance as module

        monkeypatch.setitem(module.KNOWN_GAP_TRACKING_TICKETS, "T-0329", False)
        (tmp_path / "lib.rs").write_text("fn main() {}\n", encoding="utf-8")
        violations = project_lang_conformance_gate(tmp_path)
        lang003 = [v for v in violations if v.rule == "LANG003"]
        assert any(v.severity is Severity.ERROR for v in lang003)


# frob:ticket T-2365
# The (language, capability) pairs derive_capability_registry() marks
# IMPLEMENTED for a behaviorally-checked capability TODAY -- the honest-
# tree parametrization every one of these must pass against a real
# per-language fixture, no skips (T-2365 acceptance criterion 2).
def _implemented_behavioral_cells() -> list[tuple[str, str]]:
    registry = derive_capability_registry()
    cells: list[tuple[str, str]] = []
    # frob:waive PERF004 reason="support.capabilities is this loop's own per-language \
    # distinct mapping (7 languages x 7 capabilities, module-collection time only), \
    # not a shared re-sort -- same reasoning as src/frob/gates/_lang_conformance.py's \
    # own identical-shape support.facets sort"
    for language, support in sorted(registry.items()):
        for capability, status in sorted(support.capabilities.items()):
            if capability not in _BEHAVIORALLY_CHECKED_CAPABILITIES:
                continue
            if status.state is not FacetState.IMPLEMENTED:
                continue
            allowed = _behaviorally_checked_languages(capability)
            if allowed is not None and language not in allowed:
                continue
            cells.append((language, capability))
    return cells


# frob:ticket T-2365
class TestBehavioralCapabilityCheck:
    """`_behavioral_capability_check` actually EXERCISES a capability
    against a real per-language fixture -- distinct from `TestDeriveCapabil
    ityRegistry`/`TestCapabilityConformanceViolations`
    (tests/test_lang_support.py), which test the REGISTRY's own
    declarations, never whether the claim holds. This is the load-bearing
    suite T-2365 exists to build: a conformance suite that asks nothing
    would still pass every prior test in this repo."""

    # frob:ticket T-2365
    def test_every_registered_language_is_covered(self) -> None:
        """T-2365 acceptance: the suite runs against EVERY registered
        adapter -- no language silently excluded from parametrization."""
        covered = {language for language, _cap in _implemented_behavioral_cells()}
        # Every language has at least symbol_walk/publicness/doc_extract
        # IMPLEMENTED today (derive_capability_registry's own honest-tree
        # state) -- this is a real, not vacuous, universal-coverage check.
        assert covered == set(supported_languages())

    # frob:ticket T-2365
    @pytest.mark.parametrize("language,capability", _implemented_behavioral_cells())
    def test_implemented_capability_behaves_as_claimed(
        self, tmp_path: Path, language: str, capability: str
    ) -> None:
        """Every (language, capability) cell the live registry claims
        IMPLEMENTED actually works against a real fixture -- the honest-
        tree, must-PASS half."""
        ok, detail = _behavioral_capability_check(language, capability, tmp_path)
        assert ok, f"{language}/{capability}: {detail}"

    # frob:ticket T-2365
    def test_directive_continuation_folds_correctly_not_just_present(
        self, tmp_path: Path
    ) -> None:
        """T-2365's own named sharpest test case: the `frob:tests \\`
        multi-line directive continuation must FOLD to the exact target
        string, for every language whose fixture actually exercises a
        continuation (python/typescript/rust/kotlin/strata -- c/cpp's
        fixture is deliberately single-line, see `_CAPABILITY_FIXTURE_
        SOURCES`'s own comment on the C-grammar line-splice quirk this
        test discovered) -- a checker that merely looked for the
        substring `frob:tests` on the first physical line would pass even
        if `_fold_continuations` silently truncated the target."""
        import frob.gates._lang_conformance as module

        registry = derive_capability_registry()
        checked = False
        for language, support in sorted(registry.items()):
            if language in {"c", "cpp"}:
                continue
            status = support.capabilities.get("directive_parse")
            if status is None or status.state is not FacetState.IMPLEMENTED:
                continue
            assert language == "strata" or "\\\n" in module._CAPABILITY_FIXTURE_SOURCES.get(
                language, ""
            ), f"{language}'s fixture has no continuation"
            ok, detail = _behavioral_capability_check(
                language, "directive_parse", tmp_path
            )
            assert ok, f"{language}: {detail}"
            checked = True
        assert checked, "no language had directive_parse IMPLEMENTED to check"

    # frob:ticket T-2365
    def test_broken_continuation_fixture_is_caught_not_rubber_stamped(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """MUST-FAIL POSITIVE CONTROL (T-2365 acceptance criterion 2): a
        deliberately non-conforming fixture -- python's own source, but
        with the `frob:tests \\` continuation's second physical line
        DROPPED, so the directive can never fold to the real target --
        must make `_behavioral_capability_check` report failure, not
        success. Without this test, a checker that always returns
        `(True, ...)` would pass every other test in this file."""
        import frob.gates._lang_conformance as module

        broken_source = (
            '"""Capability fixture module docstring."""\n\n\n'
            "def public_fn():\n"
            '    """A public function."""\n'
            "    return 1\n\n\n"
            "# frob:tests \\\n"
            "def _private_fn():\n"
            "    return 2\n"
        )
        monkeypatch.setitem(module._CAPABILITY_FIXTURE_SOURCES, "python", broken_source)
        ok, detail = _behavioral_capability_check(
            "python", "directive_parse", tmp_path
        )
        assert not ok, f"broken fixture was wrongly reported as passing: {detail}"

    # frob:ticket T-2365
    def test_no_symbols_fixture_is_caught_not_rubber_stamped(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """A second, independent MUST-FAIL positive control: an empty
        python fixture (no symbols at all) must fail `symbol_walk`'s
        behavioral check, proving that check genuinely inspects the parse
        result rather than always returning success."""
        import frob.gates._lang_conformance as module

        monkeypatch.setitem(
            module._CAPABILITY_FIXTURE_SOURCES, "python", "# just a comment\n"
        )
        ok, detail = _behavioral_capability_check("python", "symbol_walk", tmp_path)
        assert not ok, f"empty fixture was wrongly reported as passing: {detail}"

    # frob:ticket T-2365
    def test_unchecked_capability_is_named_not_silently_true(
        self, tmp_path: Path
    ) -> None:
        """Per epic T-2391's doctrine: a capability this module does not
        (yet) behaviorally check must be reported explicitly as such
        (`ok=False` naming the gap), never silently read as a pass. T-1599
        moved call_graph/import_graph into the checked set; T-2682 moved
        test_discovery in too, but ONLY for python -- a capability name
        entirely outside `_CAPABILITY_CHECKERS` (a made-up one, standing
        in for "a future 8th capability nobody wired a checker for yet")
        is still the genuine unchecked case at the `_behavioral_
        capability_check` level today."""
        ok, detail = _behavioral_capability_check(
            "python", "not_a_real_capability", tmp_path
        )
        assert not ok
        assert "no behavioral check" in detail

    # frob:ticket T-2682
    # frob:ticket T-2698
    def test_test_discovery_is_not_behaviorally_checked_outside_python_and_rust(
        self,
    ) -> None:
        """T-2682's own cost-driven scope decision must be LOUD and
        verifiable, not just prose in a comment: typescript/c/cpp/kotlin
        all have `test_discovery` IMPLEMENTED in the live registry
        (T-2499), but `_behaviorally_checked_languages` restricts the
        behavioral check to python/rust (T-2698 added rust) -- so none of
        the remaining four appear in `_implemented_behavioral_cells()`'s
        own parametrization, confirmed directly rather than assumed."""
        registry = derive_capability_registry()
        remaining_implemented = {
            language
            for language, support in registry.items()
            if language not in ("python", "rust")
            and support.capabilities["test_discovery"].state
            is FacetState.IMPLEMENTED
        }
        # A real, non-vacuous set: at least typescript/kotlin/c/cpp are
        # IMPLEMENTED today (T-2499's own live derivation).
        assert remaining_implemented
        cells = set(_implemented_behavioral_cells())
        for language in remaining_implemented:
            assert (language, "test_discovery") not in cells

    # frob:ticket T-2698
    def test_rust_test_discovery_is_behaviorally_checked(self) -> None:
        """T-2698's own positive control, the mirror of the negative
        control above: rust IS in `_implemented_behavioral_cells()`'s own
        parametrization now, proving the widened dispatch actually
        reaches rust rather than the docstring/comment claiming it does
        while the dispatch dict silently still excludes it."""
        cells = set(_implemented_behavioral_cells())
        assert ("rust", "test_discovery") in cells

    # frob:ticket T-2698
    def test_rust_test_discovery_passes_on_a_real_discoverable_fixture(
        self, tmp_path: Path
    ) -> None:
        """Positive control: the real rust fixture builder
        (`_check_test_discovery_rust`) writes a genuine `#[test]` fn and
        `collect_rust_tests` (`cargo test --lib -- --list`) finds it --
        proves the adapter's own real toolchain integration works, not
        just that a checker function exists."""
        ok, detail = _behavioral_capability_check("rust", "test_discovery", tmp_path)
        assert ok, detail
        assert "test_capability_fixture_discoverable" in detail

    # frob:ticket T-2698
    def test_rust_test_discovery_fails_when_the_crate_cannot_compile(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """MUST-FAIL positive control (the rust analogue of `test_no_
        symbols_fixture_is_caught_not_rubber_stamped` above): a `Cargo.
        toml` with no `[package]` table is not a real crate, so `cargo
        test --lib -- --list` cannot discover anything from it --
        `collect_rust_tests` must report failure/emptiness, and this
        check must propagate that as `ok=False`, proving it genuinely
        inspects `collect_rust_tests`'s own result rather than always
        reporting success once cargo runs at all."""
        import frob.gates._lang_conformance as module

        def _broken_rust_project(project: Path) -> tuple[bool, str]:
            # No [package] table at all -- cargo has nothing to build or
            # list tests for, the rust-toolchain equivalent of the
            # "no symbols" python fixture above.
            (project / "Cargo.toml").write_text("", encoding="utf-8")
            from frob.testing import collect_rust_tests

            collected = collect_rust_tests(project)
            if collected.is_err:
                return False, f"collect_rust_tests failed: {collected.danger_err}"
            node_ids = collected.danger_ok.node_ids
            ok = any("test_capability_fixture_discoverable" in n for n in node_ids)
            return ok, f"{len(node_ids)} node id(s) collected: {sorted(node_ids)}"

        monkeypatch.setitem(
            module._TEST_DISCOVERY_BUILDERS, ".rs", _broken_rust_project
        )
        ok, detail = _behavioral_capability_check("rust", "test_discovery", tmp_path)
        assert not ok, f"unbuildable crate was wrongly reported as passing: {detail}"


# frob:ticket T-2365
class TestCapabilityConformanceGate:
    """LANG004 (T-2365): the behavioral half of the adapter-capability axis
    -- exercised through the real `capability_conformance_gate` entrypoint,
    not just the underlying checker (`TestBehavioralCapabilityCheck` above)."""

    # frob:ticket T-2365
    def test_real_registry_is_behaviorally_clean(self) -> None:
        """The repo's own registered adapters all behave as their
        registry claims today -- this gate is clean, not just wired-but-
        untested. Called against frob's OWN repo root: T-2706's scoping
        must NOT silence this real self-conformance check here."""
        repo_root = Path(__file__).resolve().parents[1]
        assert capability_conformance_gate(repo_root) == ()

    # frob:ticket T-2365
    def test_wrong_implemented_claim_fails(self, monkeypatch) -> None:
        """MUST-FAIL POSITIVE CONTROL, gate level (T-2365 acceptance
        criterion 3): corrupt python's directive_parse fixture (drop the
        continuation's second physical line, the SAME broken shape
        `TestBehavioralCapabilityCheck.test_broken_continuation_fixture_
        is_caught_not_rubber_stamped` proves the checker catches) while
        the LIVE registry still claims python's directive_parse is
        IMPLEMENTED -- `capability_conformance_gate` must turn that
        disagreement into a real ERROR violation, not pass silently."""
        import frob.gates._lang_conformance as module

        broken_source = (
            '"""Capability fixture module docstring."""\n\n\n'
            "def public_fn():\n"
            '    """A public function."""\n'
            "    return 1\n\n\n"
            "# frob:tests \\\n"
            "def _private_fn():\n"
            "    return 2\n"
        )
        monkeypatch.setitem(module._CAPABILITY_FIXTURE_SOURCES, "python", broken_source)
        repo_root = Path(__file__).resolve().parents[1]
        violations = module.capability_conformance_gate(repo_root)
        assert len(violations) >= 1
        assert all(v.rule == "LANG004" for v in violations)
        assert all(v.severity is Severity.ERROR for v in violations)
        assert any(
            "python" in v.message and "directive_parse" in v.message
            for v in violations
        )

    # frob:ticket T-2706
    def test_consumer_repo_is_silent_even_with_a_broken_claim(
        self, tmp_path, monkeypatch
    ) -> None:
        """MUST-FAIL POSITIVE CONTROL for the OTHER direction (T-2706
        acceptance criterion): a repo whose `pyproject.toml` declares a
        project name OTHER than 'frob' must get zero LANG004 findings --
        even with the SAME broken python fixture that
        `test_wrong_implemented_claim_fails` proves fires a real
        violation in frob's own repo. This is the exact defect a
        downstream consumer (aprog-public) reported: four errors anchored
        at `src/frob/lang/_support.py`, a path that does not exist in
        their tree and that nothing in their repo can fix."""
        import frob.gates._lang_conformance as module

        broken_source = (
            '"""Capability fixture module docstring."""\n\n\n'
            "def public_fn():\n"
            '    """A public function."""\n'
            "    return 1\n\n\n"
            "# frob:tests \\\n"
            "def _private_fn():\n"
            "    return 2\n"
        )
        monkeypatch.setitem(module._CAPABILITY_FIXTURE_SOURCES, "python", broken_source)
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "aprog-public"\nversion = "0.1.0"\n'
        )
        assert module.capability_conformance_gate(tmp_path) == ()

    # frob:ticket T-2706
    def test_repo_root_with_no_pyproject_is_silent(self, tmp_path) -> None:
        """A repo with no `pyproject.toml` at all (no declared project
        identity) is not frob's own repo either -- silent, not a crash."""
        assert capability_conformance_gate(tmp_path) == ()


# frob:ticket T-2411
class TestCapabilityConformanceWiring:
    """LANG004 (T-2365) was built but never added to `frob.gates._ALL_
    GATES`/the check job table, so no real `frob check` run ever
    evaluated it -- the exact catalogued-is-not-enforced defect this
    session repeatedly found elsewhere (T-2397's identical FLAGCOV001
    lesson, cited directly in `frob.gates.__init__`'s own registration
    comment). T-2411 wires it in; these tests lock that registration so
    it cannot silently regress back to registered-but-unreachable."""

    def test_capability_conformance_is_registered_in_all_gates(self) -> None:
        """Mirrors `TestDeprecatedGate.test_deprecated_is_registered_in_
        all_gates`'s own precedent for the identical defect class."""
        # frob:tests tests/test_lang_conformance_gate.py::TestCapabilityConformanceWiring.test_capability_conformance_is_registered_in_all_gates  # noqa: E501
        from frob.gates import _ALL_GATES, _CANONICAL_GATE_ORDER

        assert "capability_conformance" in _ALL_GATES
        assert "capability_conformance" in _CANONICAL_GATE_ORDER

    def test_capability_conformance_fires_through_real_gate_dispatch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """End-to-end `run_gates` pass (no `--only` filter, the default
        gate selection) with the registry-vs-fixture disagreement
        `TestCapabilityConformanceGateEndToEnd.test_wrong_implemented_
        claim_fails` already proves at the gate-function level -- this
        proves the SAME disagreement surfaces through the real dispatch
        path, not just direct-call, confirming the wiring is live rather
        than merely present in `_ALL_GATES`."""
        # frob:tests tests/test_lang_conformance_gate.py::TestCapabilityConformanceWiring.test_capability_conformance_fires_through_real_gate_dispatch  # noqa: E501
        import subprocess
        from datetime import date

        from frob.gates import GateConfig, run_gates
        from frob.tickets._models import Origin, Ticket, TicketKind, TicketState

        import frob.gates._lang_conformance as module

        broken_source = (
            '"""Capability fixture module docstring."""\n\n\n'
            "def public_fn():\n"
            '    """A public function."""\n'
            "    return 1\n\n\n"
            "# frob:tests \\\n"
            "def _private_fn():\n"
            "    return 2\n"
        )
        monkeypatch.setitem(module._CAPABILITY_FIXTURE_SOURCES, "python", broken_source)

        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@example.com"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
        # T-2706: capability_conformance_gate now scopes itself to frob's
        # OWN repo (`is_frob_own_repo`) -- this fixture must declare
        # itself as "frob" so this test still exercises the real
        # dispatch path for the finding, rather than proving the T-2706
        # scoping (that direction is
        # TestCapabilityConformanceGate.test_consumer_repo_is_silent_
        # even_with_a_broken_claim instead).
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "frob"\nversion = "0.0.0"\n', encoding="utf-8"
        )
        (tmp_path / "tickets.md").write_text("# Tickets\n", encoding="utf-8")
        ticket = Ticket(
            id="T-0001",
            title="Sample",
            state=TicketState.QUEUED,
            kind=TicketKind.FEATURE,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            scope=(),
            evidence=(),
            attachments=(),
            body="## Description\nx\n\n## Done report\ndone\n",
        )
        from frob.tickets._store import write_ticket

        write_ticket(tmp_path, ticket)
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "base"], cwd=tmp_path, check=True
        )

        cfg = GateConfig(root=str(tmp_path), base="main")
        result = run_gates(cfg)
        assert result.is_ok
        report = result.danger_ok
        lang004_hits = [v for v in report.violations if v.rule == "LANG004"]
        assert lang004_hits, (
            "LANG004 did not fire through real run_gates dispatch -- "
            "capability_conformance is registered but not actually reached"
        )
