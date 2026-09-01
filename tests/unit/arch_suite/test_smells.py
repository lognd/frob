"""Split from tests/unit/test_arch.py (T-1201)."""

from __future__ import annotations

import pytest

from tests.unit.arch_suite.conftest import HAS_ARCH

pytestmark = pytest.mark.skipif(not HAS_ARCH, reason="frob.arch not available")


class TestMutableDefaultArg:
    """`check_mutable_default_arg`
    (docs/modules/arch.md#misc-design-smells)."""

    def test_list_literal_default_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
        )
        from frob.arch._smells import check_mutable_default_arg

        func = NormalizedFunction(
            name="add_item",
            line=1,
            body_line_count=1,
            params=[NormalizedParam(name="items", has_default=True, default_text="[]")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_mutable_default_arg(module)
        assert len(out) == 1
        assert out[0].category == "mutable-default-arg"

    def test_none_default_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
        )
        from frob.arch._smells import check_mutable_default_arg

        func = NormalizedFunction(
            name="add_item",
            line=1,
            body_line_count=1,
            params=[
                NormalizedParam(name="items", has_default=True, default_text="None")
            ],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_mutable_default_arg(module)
        assert out == []


class TestFeatureEnvy:
    """`check_feature_envy` (docs/modules/arch.md#misc-design-smells)."""

    def test_method_calling_other_receiver_more_than_self_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedClass,
            NormalizedFunction,
            NormalizedModule,
        )
        from frob.arch._smells import check_feature_envy

        method = NormalizedFunction(
            name="render",
            line=2,
            body_line_count=4,
            is_method=True,
            calls=[
                NormalizedCall(callee="other.a", line=3),
                NormalizedCall(callee="other.b", line=4),
                NormalizedCall(callee="self.helper", line=5),
            ],
        )
        cls = NormalizedClass(name="Widget", line=1, methods=[method])
        module = NormalizedModule(path="pkg/mod.py", language="python", classes=[cls])
        out = check_feature_envy(module)
        assert len(out) == 1
        assert out[0].category == "feature-envy"

    def test_method_calling_self_more_than_others_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedClass,
            NormalizedFunction,
            NormalizedModule,
        )
        from frob.arch._smells import check_feature_envy

        method = NormalizedFunction(
            name="render",
            line=2,
            body_line_count=4,
            is_method=True,
            calls=[
                NormalizedCall(callee="self.a", line=3),
                NormalizedCall(callee="self.b", line=4),
                NormalizedCall(callee="other.helper", line=5),
            ],
        )
        cls = NormalizedClass(name="Widget", line=1, methods=[method])
        module = NormalizedModule(path="pkg/mod.py", language="python", classes=[cls])
        out = check_feature_envy(module)
        assert out == []


class TestDataClumps:
    """`check_data_clumps` (docs/modules/arch.md#misc-design-smells)."""

    def test_same_three_keyword_group_at_three_sites_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCallArg,
            NormalizedFunction,
            NormalizedModule,
        )
        from frob.arch._smells import check_data_clumps

        args = [
            NormalizedCallArg(keyword="street"),
            NormalizedCallArg(keyword="city"),
            NormalizedCallArg(keyword="zip_code"),
        ]
        func = NormalizedFunction(
            name="run",
            line=1,
            body_line_count=3,
            calls=[
                NormalizedCall(callee="make_address", line=2, args=args),
                NormalizedCall(callee="make_address", line=3, args=args),
                NormalizedCall(callee="make_address", line=4, args=args),
            ],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_data_clumps(module)
        assert len(out) == 1
        assert out[0].category == "data-clumps"
        assert out[0].metric == 3

    def test_group_at_two_sites_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCallArg,
            NormalizedFunction,
            NormalizedModule,
        )
        from frob.arch._smells import check_data_clumps

        args = [
            NormalizedCallArg(keyword="street"),
            NormalizedCallArg(keyword="city"),
            NormalizedCallArg(keyword="zip_code"),
        ]
        func = NormalizedFunction(
            name="run",
            line=1,
            body_line_count=2,
            calls=[
                NormalizedCall(callee="make_address", line=2, args=args),
                NormalizedCall(callee="make_address", line=3, args=args),
            ],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_data_clumps(module)
        assert out == []


class TestMagicLiteral:
    """`check_magic_literal` (docs/modules/arch.md#misc-design-smells)."""

    def test_bare_number_in_condition_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedFunction,
            NormalizedModule,
        )
        from frob.arch._smells import check_magic_literal

        func = NormalizedFunction(
            name="run",
            line=1,
            body_line_count=2,
            branches=[NormalizedBranch(line=2, condition_text="retries > 42")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_magic_literal(module)
        assert len(out) == 1
        assert out[0].category == "magic-literal"

    def test_zero_and_one_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedFunction,
            NormalizedModule,
        )
        from frob.arch._smells import check_magic_literal

        func = NormalizedFunction(
            name="run",
            line=1,
            body_line_count=2,
            branches=[NormalizedBranch(line=2, condition_text="count > 0 and n == 1")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_magic_literal(module)
        assert out == []


class TestDeadPrivateCode:
    """`check_dead_private_code`
    (docs/modules/arch.md#misc-design-smells)."""

    def test_unreferenced_private_function_flagged(self) -> None:
        from frob.arch._normalized import NormalizedFunction, NormalizedModule
        from frob.arch._smells import check_dead_private_code

        func = NormalizedFunction(name="_helper", line=1, body_line_count=1)
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_dead_private_code(module)
        assert len(out) == 1
        assert out[0].category == "dead-private-code"

    def test_referenced_private_function_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )
        from frob.arch._smells import check_dead_private_code

        helper = NormalizedFunction(name="_helper", line=1, body_line_count=1)
        run = NormalizedFunction(
            name="run",
            line=5,
            body_line_count=1,
            calls=[NormalizedCall(callee="_helper", line=6)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[helper, run]
        )
        out = check_dead_private_code(module)
        assert out == []


class TestDeepInheritance:
    """`check_deep_inheritance` (docs/modules/arch.md#misc-design-smells)."""

    def test_chain_beyond_threshold_flagged(self) -> None:
        from frob.arch._normalized import NormalizedClass, NormalizedModule
        from frob.arch._smells import check_deep_inheritance

        classes = [
            NormalizedClass(name="A", line=1),
            NormalizedClass(name="B", line=2, bases=["A"]),
            NormalizedClass(name="C", line=3, bases=["B"]),
            NormalizedClass(name="D", line=4, bases=["C"]),
            NormalizedClass(name="E", line=5, bases=["D"]),
        ]
        module = NormalizedModule(path="pkg/mod.py", language="python", classes=classes)
        out = check_deep_inheritance(module)
        assert any(s.symref == "pkg/mod.py::E" for s in out)

    def test_shallow_chain_not_flagged(self) -> None:
        from frob.arch._normalized import NormalizedClass, NormalizedModule
        from frob.arch._smells import check_deep_inheritance

        classes = [
            NormalizedClass(name="A", line=1),
            NormalizedClass(name="B", line=2, bases=["A"]),
        ]
        module = NormalizedModule(path="pkg/mod.py", language="python", classes=classes)
        out = check_deep_inheritance(module)
        assert out == []


class TestTemporalCoupling:
    """`check_temporal_coupling`
    (docs/modules/arch.md#misc-design-smells)."""

    def test_guard_clause_on_initialized_flag_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedClass,
            NormalizedField,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )
        from frob.arch._smells import check_temporal_coupling

        method = NormalizedFunction(
            name="use",
            line=5,
            body_line_count=3,
            is_method=True,
            branches=[NormalizedBranch(line=6, condition_text="not self._initialized")],
            raises=[NormalizedRaise(line=7, exception_type="RuntimeError")],
        )
        cls = NormalizedClass(
            name="Service",
            line=1,
            fields=[NormalizedField(name="_initialized", line=2, type="bool")],
            methods=[method],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", classes=[cls])
        out = check_temporal_coupling(module)
        assert len(out) == 1
        assert out[0].category == "temporal-coupling"

    def test_field_not_guarded_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedClass,
            NormalizedField,
            NormalizedFunction,
            NormalizedModule,
        )
        from frob.arch._smells import check_temporal_coupling

        method = NormalizedFunction(
            name="use", line=5, body_line_count=1, is_method=True
        )
        cls = NormalizedClass(
            name="Service",
            line=1,
            fields=[NormalizedField(name="_initialized", line=2, type="bool")],
            methods=[method],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", classes=[cls])
        out = check_temporal_coupling(module)
        assert out == []


class TestRunSmellChecks:
    """`run_smell_checks` combines every ARCH1xx misc design-smell check
    (docs/modules/arch.md#misc-design-smells)."""

    def test_combines_all_seven_checks(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedCall,
            NormalizedCallArg,
            NormalizedClass,
            NormalizedField,
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
            NormalizedRaise,
        )
        from frob.arch._smells import run_smell_checks

        args = [
            NormalizedCallArg(keyword="a"),
            NormalizedCallArg(keyword="b"),
            NormalizedCallArg(keyword="c"),
        ]
        top_fn = NormalizedFunction(
            name="run",
            line=1,
            body_line_count=8,
            params=[NormalizedParam(name="items", has_default=True, default_text="[]")],
            branches=[NormalizedBranch(line=2, condition_text="retries > 42")],
            calls=[
                NormalizedCall(callee="make_thing", line=3, args=args),
                NormalizedCall(callee="make_thing", line=4, args=args),
                NormalizedCall(callee="make_thing", line=5, args=args),
            ],
        )
        dead_fn = NormalizedFunction(name="_dead", line=20, body_line_count=1)
        method = NormalizedFunction(
            name="use",
            line=30,
            body_line_count=3,
            is_method=True,
            branches=[
                NormalizedBranch(line=31, condition_text="not self._initialized")
            ],
            raises=[NormalizedRaise(line=32, exception_type="RuntimeError")],
            calls=[
                NormalizedCall(callee="other.a", line=31),
                NormalizedCall(callee="other.b", line=32),
            ],
        )
        cls = NormalizedClass(
            name="Service",
            line=25,
            fields=[NormalizedField(name="_initialized", line=26, type="bool")],
            methods=[method],
        )
        module = NormalizedModule(
            path="pkg/mod.py",
            language="python",
            functions=[top_fn, dead_fn],
            classes=[cls],
        )
        out = run_smell_checks(module)
        categories = {s.category for s in out}
        assert "mutable-default-arg" in categories
        assert "data-clumps" in categories
        assert "magic-literal" in categories
        assert "dead-private-code" in categories
        assert "temporal-coupling" in categories
        assert "feature-envy" in categories
