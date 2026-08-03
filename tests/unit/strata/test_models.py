"""Unit tests for the strata kernel data model (docs/strata/kernel.md)."""

from __future__ import annotations

import pytest

from frob.strata import (
    LABELS,
    TRUST,
    Capacity,
    KernelModel,
    Lattice,
    Quantity,
    StrataError,
)


class TestLattice:
    # frob:tests src/frob/strata/_models.py::Lattice.elements kind="unit"
    def test_elements_collects_every_level(self):
        assert TRUST.elements() == {"foreign", "authenticated", "trusted"}
        assert LABELS.elements() == {"Public", "Internal", "Pii", "Secret"}

    # frob:tests src/frob/strata/_models.py::Lattice.leq kind="unit"
    def test_leq_is_reflexive_transitive_and_ordered(self):
        assert TRUST.leq("foreign", "foreign").danger_ok is True
        assert TRUST.leq("foreign", "trusted").danger_ok is True  # transitive
        assert TRUST.leq("trusted", "foreign").danger_ok is False
        assert LABELS.leq("Public", "Secret").danger_ok is True

    # frob:tests src/frob/strata/_models.py::Lattice.leq kind="unit"
    def test_leq_unknown_level_is_an_error_not_false(self):
        result = TRUST.leq("foreign", "root")
        assert result.is_err
        assert result.danger_err is StrataError.UnknownLevel

    # frob:tests src/frob/strata/_models.py::Lattice.leq kind="unit"
    def test_leq_incomparable_elements_are_false_both_ways(self):
        diamond = Lattice(name="d", order=(("bot", "a"), ("bot", "b")))
        assert diamond.leq("a", "b").danger_ok is False
        assert diamond.leq("b", "a").danger_ok is False


class TestQuantity:
    # frob:tests src/frob/strata/_models.py::Quantity.dimension kind="unit"
    def test_dimension_resolves_and_rejects_unknown_units(self):
        assert Quantity(value=1, unit="ms").dimension().danger_ok == "time"
        assert Quantity(value=1, unit="req/s").dimension().danger_ok == "rate"
        bad = Quantity(value=1, unit="furlong").dimension()
        assert bad.is_err
        assert bad.danger_err is StrataError.UnknownUnit

    # frob:tests src/frob/strata/_models.py::Quantity.base_value kind="unit"
    def test_base_value_converts_to_base_unit(self):
        assert Quantity(value=250, unit="ms").base_value().danger_ok == 0.25
        assert Quantity(value=2, unit="KiB").base_value().danger_ok == 2048.0
        assert Quantity(
            value=60, unit="req/min"
        ).base_value().danger_ok == pytest.approx(1.0)

    # frob:tests src/frob/strata/_models.py::Quantity.leq kind="unit"
    def test_leq_compares_across_units_of_one_dimension(self):
        fast = Quantity(value=250, unit="ms")
        slow = Quantity(value=1, unit="s")
        assert fast.leq(slow).danger_ok is True
        assert slow.leq(fast).danger_ok is False

    # frob:tests src/frob/strata/_models.py::Quantity.leq kind="unit"
    def test_leq_across_dimensions_is_an_error_not_false(self):
        time = Quantity(value=1, unit="s")
        size = Quantity(value=1, unit="B")
        result = time.leq(size)
        assert result.is_err
        assert result.danger_err is StrataError.UnitMismatch

    # frob:tests src/frob/strata/_models.py::Quantity.base_value kind="unit"
    def test_base_value_unknown_unit_is_an_error(self):
        bad = Quantity(value=1, unit="furlong")
        result = bad.base_value()
        assert result.is_err
        assert result.danger_err is StrataError.UnknownUnit

    # frob:tests src/frob/strata/_models.py::Quantity.leq kind="unit"
    def test_leq_propagates_unknown_unit_error_from_self(self):
        bad = Quantity(value=1, unit="furlong")
        ok = Quantity(value=1, unit="s")
        result = bad.leq(ok)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownUnit

    # frob:tests src/frob/strata/_models.py::Quantity.leq kind="unit"
    def test_leq_propagates_unknown_unit_error_from_other(self):
        ok = Quantity(value=1, unit="s")
        bad = Quantity(value=1, unit="furlong")
        result = ok.leq(bad)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownUnit


class TestCapacity:
    # frob:tests src/frob/strata/_models.py::Capacity.singleton kind="unit"
    def test_singleton_iff_replicas_cannot_exceed_one(self):
        one = Capacity(service_rate=Quantity(value=100, unit="req/s"))
        many = Capacity(
            service_rate=Quantity(value=100, unit="req/s"),
            replicas_min=2,
            replicas_max=32,
        )
        assert one.singleton is True
        assert many.singleton is False


class TestKernelModel:
    # frob:tests src/frob/strata/_models.py::KernelModel kind="unit"
    def test_defaults_are_empty_with_builtin_lattices(self):
        model = KernelModel()
        assert model.nodes == ()
        assert model.trust is TRUST
        assert model.labels is LABELS

    # frob:tests src/frob/strata/_models.py::KernelModel kind="unit"
    def test_frozen_models_compare_by_value(self):
        assert KernelModel() == KernelModel()
        assert Quantity(value=1, unit="s") == Quantity(value=1, unit="s")
