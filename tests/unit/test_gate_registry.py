"""Unit tests for `frob.gates._registry` (T-4661): the one gate
registration interface the job list, known-rule-id set, doc rule table
and check-coverage entries are all derived from."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates import _ALL_GATES, _registry
from frob.gates._models import Severity
from frob.gates._waive import _KNOWN_GATE_RULES


@pytest.fixture(autouse=True)
def _clean_registry():
    """Every test starts from an empty registry table -- registration is
    process-global state, so tests must not see each other's entries."""
    _registry.reset_registry_for_tests()
    yield
    _registry.reset_registry_for_tests()


class TestRegisterGate:
    """`register_gate` itself: success, duplicate job, duplicate rule id,
    empty rule ids."""

    def test_register_returns_the_stored_registration(self) -> None:
        """A fresh job name registers cleanly and round-trips its fields."""
        result = _registry.register_gate(
            job="widget",
            rule_ids=["WID001"],
            stage_groups=["gates-fast"],
            severity=Severity.WARN,
            reads=("src/frob/widget.py",),
        )
        assert result.is_ok
        reg = result.danger_ok
        assert reg.job == "widget"
        assert reg.rule_ids == frozenset({"WID001"})
        assert reg.severity is Severity.WARN
        assert reg.reads == ("src/frob/widget.py",)

    def test_duplicate_job_name_is_refused(self) -> None:
        """Registering the same job name twice is `DuplicateJob`, not a
        silent overwrite of the first detector's declaration."""
        _registry.register_gate(
            job="widget", rule_ids=["WID001"], stage_groups=["gates-fast"]
        )
        result = _registry.register_gate(
            job="widget", rule_ids=["WID002"], stage_groups=["gates-fast"]
        )
        assert result.is_err
        assert result.danger_err is _registry.RegistryError.DuplicateJob

    def test_duplicate_rule_id_across_jobs_is_refused(self) -> None:
        """Two different jobs claiming the same rule id is refused --
        the reverse-index conflict `_KNOWN_GATE_RULES` could never
        detect on its own (a flat set has no owner)."""
        _registry.register_gate(
            job="widget", rule_ids=["WID001"], stage_groups=["gates-fast"]
        )
        result = _registry.register_gate(
            job="gadget", rule_ids=["WID001"], stage_groups=["gates-fast"]
        )
        assert result.is_err
        assert result.danger_err is _registry.RegistryError.DuplicateRuleId

    def test_empty_rule_ids_is_refused(self) -> None:
        """A registration declaring zero rule ids is refused -- a
        detector with no rule id is not a gate, it is a bug."""
        result = _registry.register_gate(
            job="widget", rule_ids=[], stage_groups=["gates-fast"]
        )
        assert result.is_err
        assert result.danger_err is _registry.RegistryError.EmptyRuleIds


class TestGateDecorator:
    """The `@gate(...)` decorator form used at module-import time."""

    def test_decorator_registers_and_returns_function_unchanged(self) -> None:
        """The decorated function is returned unchanged and callable, and
        its rule id is now known to the registry."""

        @_registry.gate(job="widget", rule_ids=["WID001"], stage_groups=["gates-fast"])
        def _detect() -> str:
            return "ran"

        assert _detect() == "ran"
        assert "WID001" in _registry.derive_known_rule_ids()

    def test_decorator_raises_on_conflict(self) -> None:
        """A decorator has no `Result` to hand back to an import-time
        caller, so a registration conflict is a raised `RuntimeError`."""
        _registry.register_gate(
            job="widget", rule_ids=["WID001"], stage_groups=["gates-fast"]
        )
        with pytest.raises(RuntimeError):

            @_registry.gate(
                job="widget", rule_ids=["WID002"], stage_groups=["gates-fast"]
            )
            def _detect() -> str:
                return "ran"


class TestSeedLegacyBulk:
    """The one-time legacy-baseline seed and its idempotence."""

    def test_seed_is_idempotent(self) -> None:
        """Seeding twice with identical data is a no-op Ok, not a
        DuplicateJob refusal -- multiple gate-adjacent modules may each
        want the legacy baseline present."""
        first = _registry.seed_legacy_bulk(job_names=["a", "b"], rule_ids=["R001"])
        second = _registry.seed_legacy_bulk(job_names=["a", "b"], rule_ids=["R001"])
        assert first.is_ok
        assert second.is_ok

    def test_seed_with_different_data_is_refused(self) -> None:
        """A second seed call with DIFFERENT rule ids is refused rather
        than silently replacing the first -- the bulk entry is meant to
        be written once per process."""
        _registry.seed_legacy_bulk(job_names=["a"], rule_ids=["R001"])
        result = _registry.seed_legacy_bulk(job_names=["a"], rule_ids=["R002"])
        assert result.is_err


class TestDerivedViewsMatchLegacyExactly:
    """Acceptance [0]: the job-list and known-rule-id derived views equal
    today's hand-maintained `_ALL_GATES`/`_KNOWN_GATE_RULES` exactly, no
    rule gained or lost, once the legacy baseline is seeded."""

    def test_derived_job_names_equal_all_gates(self) -> None:
        """`derive_job_names()` seeded from `_ALL_GATES` equals it exactly."""
        _registry.seed_legacy_bulk(job_names=_ALL_GATES, rule_ids=_KNOWN_GATE_RULES)
        assert _registry.derive_job_names() == frozenset(_ALL_GATES)

    def test_derived_known_rule_ids_equal_known_gate_rules(self) -> None:
        """`derive_known_rule_ids()` seeded from `_KNOWN_GATE_RULES`
        equals it exactly -- no rule gained, none lost."""
        _registry.seed_legacy_bulk(job_names=_ALL_GATES, rule_ids=_KNOWN_GATE_RULES)
        assert _registry.derive_known_rule_ids() == frozenset(_KNOWN_GATE_RULES)


class TestAddingADetectorTouchesOneFile:
    """POSITIVE CONTROL (acceptance [1]): a brand-new fake detector,
    registered through the registry alone, with no edit to
    `gates/__init__.py` or `_waive.py`, appears in every derived view.
    Fails on dev today (no registry exists at all; the fake rule id
    would be reported as unregistered against `_KNOWN_GATE_RULES`)."""

    def test_adding_a_detector_touches_one_file(self) -> None:
        """Registering `FAKE_T4661_001` via `register_gate` alone makes it
        appear in the derived job list, known-rule-id set, and
        check-coverage view -- proving the four views are genuinely
        derived, not independently hand-maintained."""
        _registry.seed_legacy_bulk(job_names=_ALL_GATES, rule_ids=_KNOWN_GATE_RULES)
        result = _registry.register_gate(
            job="fake_t4661_detector",
            rule_ids=["FAKE_T4661_001"],
            stage_groups=["gates-fast"],
        )
        assert result.is_ok

        assert "fake_t4661_detector" in _registry.derive_job_names()
        assert "FAKE_T4661_001" in _registry.derive_known_rule_ids()
        coverage_ids = {entry.id for entry in _registry.derive_check_coverage_entries()}
        assert "CHK-GATE-FAKE_T4661_001" in coverage_ids
        assert "FAKE_T4661_001" in _registry.derive_doc_rule_table()

        # The fake rule id was never written into either hotspot file.
        waive_src = Path("src/frob/gates/_waive.py").read_text(encoding="utf-8")
        init_src = Path("src/frob/gates/__init__.py").read_text(encoding="utf-8")
        assert "FAKE_T4661_001" not in waive_src
        assert "FAKE_T4661_001" not in init_src


class TestUnregisteredLiveRuleIsReported:
    """Acceptance [2]: a rule id live in a detector but absent from the
    registry is reported, not silently accepted -- the existing
    `_rule_id_scan` behaviour, now sourced from this registry."""

    def test_registered_ids_are_not_reported(self) -> None:
        """A candidate scan that only finds already-registered ids
        reports nothing unregistered."""
        _registry.register_gate(
            job="widget", rule_ids=["WID001"], stage_groups=["gates-fast"]
        )
        unregistered = _registry.find_unregistered_live_rule_ids(
            repo_root=Path("."),
            scan_candidates=lambda root: {"WID001": "widget.py:1"},
        )
        assert unregistered == frozenset()

    def test_unregistered_live_rule_is_reported(self) -> None:
        """A candidate id absent from the registry is reported, not
        silently accepted -- this is what would have caught T-3997/
        T-3953/T-3964 shipping unwired."""
        _registry.register_gate(
            job="widget", rule_ids=["WID001"], stage_groups=["gates-fast"]
        )
        unregistered = _registry.find_unregistered_live_rule_ids(
            repo_root=Path("."),
            scan_candidates=lambda root: {
                "WID001": "widget.py:1",
                "GHOST001": "ghost.py:9",
            },
        )
        assert unregistered == frozenset({"GHOST001"})


class TestGateRegistrationDocDescribesTheFourDerivedViews:
    """Acceptance [3]: `docs/modules/gate-registration.md` describes the
    registration interface and the four derived views."""

    def test_doc_describes_registration_interface_and_derived_views(self) -> None:
        """The doc names `register_gate`, and all four `derive_*` view
        functions, so a reader lands on the real symbols this leaf ships."""
        doc = Path("docs/modules/gate-registration.md").read_text(encoding="utf-8")
        assert "register_gate" in doc
        assert "derive_job_names" in doc
        assert "derive_known_rule_ids" in doc
        assert "derive_doc_rule_table" in doc
        assert "derive_check_coverage_entries" in doc
