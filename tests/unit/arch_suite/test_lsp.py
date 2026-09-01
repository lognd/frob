"""Split from tests/unit/test_arch.py (T-1201)."""

from __future__ import annotations

import pytest

from tests.unit.arch_suite.conftest import (
    HAS_ARCH,
    _isp_module,
    _lsp_module,
    _real_method,
    _stub_method,
)

pytestmark = pytest.mark.skipif(not HAS_ARCH, reason="frob.arch not available")



class TestOverrideRaisesNotImplemented:
    """ARCH104: `check_override_raises_not_implemented`
    (docs/modules/arch.md#lsp-checks)."""

    def test_concrete_override_raising_not_implemented_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedClass,
            NormalizedFunction,
            NormalizedRaise,
            NormalizedReturn,
        )
        from frob.arch._solid import check_override_raises_not_implemented

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="greet",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    returns=[NormalizedReturn(line=3, value_text="'hi'")],
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="greet",
                    line=6,
                    body_line_count=1,
                    is_method=True,
                    raises=[
                        NormalizedRaise(line=7, exception_type="NotImplementedError")
                    ],
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_override_raises_not_implemented(module, out)
        assert len(out) == 1
        assert out[0].category == "lsp-not-implemented-override"
        assert out[0].symref == "pkg/mod.py::Sub.greet"

    def test_base_itself_raising_not_implemented_is_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedClass,
            NormalizedFunction,
            NormalizedRaise,
        )
        from frob.arch._solid import check_override_raises_not_implemented

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="greet",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    raises=[
                        NormalizedRaise(line=3, exception_type="NotImplementedError")
                    ],
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="greet",
                    line=6,
                    body_line_count=1,
                    is_method=True,
                    raises=[
                        NormalizedRaise(line=7, exception_type="NotImplementedError")
                    ],
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_override_raises_not_implemented(module, out)
        assert out == []


class TestOverrideSignatureVariance:
    """ARCH105: `check_override_signature_variance`
    (docs/modules/arch.md#lsp-checks)."""

    def test_narrower_required_params_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedClass,
            NormalizedFunction,
            NormalizedParam,
        )
        from frob.arch._solid import check_override_signature_variance

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="save",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    params=[
                        NormalizedParam(name="self"),
                        NormalizedParam(name="path"),
                        NormalizedParam(name="mode"),
                    ],
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="save",
                    line=6,
                    body_line_count=1,
                    is_method=True,
                    params=[NormalizedParam(name="self"), NormalizedParam(name="path")],
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_override_signature_variance(module, out)
        assert len(out) == 1
        assert out[0].category == "lsp-signature-variance"
        assert out[0].metric == 1

    def test_wider_return_type_flagged(self) -> None:
        from frob.arch._normalized import NormalizedClass, NormalizedFunction
        from frob.arch._solid import check_override_signature_variance

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="get",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    return_type="int",
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="get",
                    line=6,
                    body_line_count=1,
                    is_method=True,
                    return_type="str",
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_override_signature_variance(module, out)
        assert len(out) == 1
        assert out[0].category == "lsp-signature-variance"

    def test_same_shape_signature_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedClass,
            NormalizedFunction,
            NormalizedParam,
        )
        from frob.arch._solid import check_override_signature_variance

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="get",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    params=[NormalizedParam(name="self"), NormalizedParam(name="x")],
                    return_type="int",
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="get",
                    line=6,
                    body_line_count=1,
                    is_method=True,
                    params=[NormalizedParam(name="self"), NormalizedParam(name="x")],
                    return_type="int",
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_override_signature_variance(module, out)
        assert out == []


class TestOverrideStrengthenedPrecondition:
    """ARCH106: `check_override_strengthened_precondition`
    (docs/modules/arch.md#lsp-checks)."""

    def test_added_guard_raise_on_shared_param_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedClass,
            NormalizedFunction,
            NormalizedParam,
            NormalizedRaise,
        )
        from frob.arch._solid import check_override_strengthened_precondition

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="withdraw",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    params=[
                        NormalizedParam(name="self"),
                        NormalizedParam(name="amount"),
                    ],
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="withdraw",
                    line=6,
                    body_line_count=3,
                    is_method=True,
                    params=[
                        NormalizedParam(name="self"),
                        NormalizedParam(name="amount"),
                    ],
                    branches=[NormalizedBranch(line=7, condition_text="amount > 100")],
                    raises=[NormalizedRaise(line=8, exception_type="ValueError")],
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_override_strengthened_precondition(module, out)
        assert len(out) == 1
        assert out[0].category == "lsp-strengthened-precondition"
        assert out[0].metric == 1

    def test_guard_raise_present_in_base_too_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedClass,
            NormalizedFunction,
            NormalizedParam,
            NormalizedRaise,
        )
        from frob.arch._solid import check_override_strengthened_precondition

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="withdraw",
                    line=2,
                    body_line_count=3,
                    is_method=True,
                    params=[
                        NormalizedParam(name="self"),
                        NormalizedParam(name="amount"),
                    ],
                    branches=[NormalizedBranch(line=3, condition_text="amount > 100")],
                    raises=[NormalizedRaise(line=4, exception_type="ValueError")],
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=6,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="withdraw",
                    line=7,
                    body_line_count=3,
                    is_method=True,
                    params=[
                        NormalizedParam(name="self"),
                        NormalizedParam(name="amount"),
                    ],
                    branches=[NormalizedBranch(line=8, condition_text="amount > 100")],
                    raises=[NormalizedRaise(line=9, exception_type="ValueError")],
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_override_strengthened_precondition(module, out)
        assert out == []


class TestOverrideWeakenedPostcondition:
    """ARCH107: `check_override_weakened_postcondition`
    (docs/modules/arch.md#lsp-checks)."""

    def test_bare_return_where_base_always_returns_value_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedClass,
            NormalizedFunction,
            NormalizedReturn,
        )
        from frob.arch._solid import check_override_weakened_postcondition

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="find",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    returns=[NormalizedReturn(line=3, value_text="item")],
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="find",
                    line=6,
                    body_line_count=2,
                    is_method=True,
                    returns=[NormalizedReturn(line=7, value_text=None)],
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_override_weakened_postcondition(module, out)
        assert len(out) == 1
        assert out[0].category == "lsp-weakened-postcondition"

    def test_override_also_always_returning_value_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedClass,
            NormalizedFunction,
            NormalizedReturn,
        )
        from frob.arch._solid import check_override_weakened_postcondition

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="find",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    returns=[NormalizedReturn(line=3, value_text="item")],
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="find",
                    line=6,
                    body_line_count=1,
                    is_method=True,
                    returns=[NormalizedReturn(line=7, value_text="other_item")],
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_override_weakened_postcondition(module, out)
        assert out == []


class TestNoOpOverride:
    """ARCH108: `check_noop_override` (docs/modules/arch.md#lsp-checks)."""

    def test_empty_body_override_of_value_returning_base_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedClass,
            NormalizedFunction,
            NormalizedReturn,
        )
        from frob.arch._solid import check_noop_override

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="compute",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    returns=[NormalizedReturn(line=3, value_text="42")],
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="compute",
                    line=6,
                    body_line_count=1,
                    is_method=True,
                    returns=[],
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_noop_override(module, out)
        assert len(out) == 1
        assert out[0].category == "lsp-noop-override"

    def test_override_with_real_body_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedClass,
            NormalizedFunction,
            NormalizedReturn,
        )
        from frob.arch._solid import check_noop_override

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="compute",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    returns=[NormalizedReturn(line=3, value_text="42")],
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="compute",
                    line=6,
                    body_line_count=2,
                    is_method=True,
                    calls=[NormalizedCall(callee="super().compute", line=7)],
                    returns=[NormalizedReturn(line=7, value_text="43")],
                )
            ],
        )
        module = _lsp_module(base, override)
        out: list = []
        check_noop_override(module, out)
        assert out == []


class TestRunLspChecks:
    """`run_lsp_checks` combines every ARCH1xx LSP check
    (docs/modules/arch.md#lsp-checks)."""

    def test_combines_multiple_checks(self) -> None:
        from frob.arch._normalized import (
            NormalizedClass,
            NormalizedFunction,
            NormalizedRaise,
            NormalizedReturn,
        )
        from frob.arch._solid import run_lsp_checks

        base = NormalizedClass(
            name="Base",
            line=1,
            methods=[
                NormalizedFunction(
                    name="greet",
                    line=2,
                    body_line_count=1,
                    is_method=True,
                    returns=[NormalizedReturn(line=3, value_text="'hi'")],
                )
            ],
        )
        override = NormalizedClass(
            name="Sub",
            line=5,
            bases=["Base"],
            methods=[
                NormalizedFunction(
                    name="greet",
                    line=6,
                    body_line_count=1,
                    is_method=True,
                    raises=[
                        NormalizedRaise(line=7, exception_type="NotImplementedError")
                    ],
                )
            ],
        )
        module = _lsp_module(base, override)
        out = run_lsp_checks(module)
        categories = {s.category for s in out}
        assert "lsp-not-implemented-override" in categories


class TestFatInterface:
    """ARCH109: `check_fat_interface` (docs/modules/arch.md#isp-checks)."""

    def test_mostly_stubbed_implementers_flag_fat_interface(self) -> None:
        from frob.arch._normalized import NormalizedClass
        from frob.arch._solid import check_fat_interface

        interface = NormalizedClass(
            name="Repo",
            line=1,
            bases=["ABC"],
            methods=[
                _stub_method("create", 2),
                _stub_method("read", 3),
                _stub_method("update", 4),
                _stub_method("delete", 5),
            ],
        )
        impl_a = NormalizedClass(
            name="ImplA",
            line=10,
            bases=["Repo"],
            methods=[
                _stub_method("create", 11),
                _stub_method("read", 12),
                _stub_method("update", 13),
                _real_method("delete", 14),
            ],
        )
        impl_b = NormalizedClass(
            name="ImplB",
            line=20,
            bases=["Repo"],
            methods=[
                _stub_method("create", 21),
                _stub_method("read", 22),
                _stub_method("update", 23),
                _real_method("delete", 24),
            ],
        )
        module = _isp_module(interface, impl_a, impl_b)
        out: list = []
        check_fat_interface(module, out)
        assert len(out) == 1
        assert out[0].category == "fat-interface"
        assert out[0].symref == "Repo"
        assert out[0].metric == 6  # 3 stubbed methods x 2 implementers

    def test_mostly_implemented_methods_not_flagged(self) -> None:
        from frob.arch._normalized import NormalizedClass
        from frob.arch._solid import check_fat_interface

        interface = NormalizedClass(
            name="Repo",
            line=1,
            bases=["ABC"],
            methods=[
                _stub_method("create", 2),
                _stub_method("read", 3),
                _stub_method("update", 4),
                _stub_method("delete", 5),
            ],
        )
        impl_a = NormalizedClass(
            name="ImplA",
            line=10,
            bases=["Repo"],
            methods=[
                _real_method("create", 11),
                _real_method("read", 12),
                _real_method("update", 13),
                _stub_method("delete", 14),
            ],
        )
        impl_b = NormalizedClass(
            name="ImplB",
            line=20,
            bases=["Repo"],
            methods=[
                _real_method("create", 21),
                _real_method("read", 22),
                _real_method("update", 23),
                _stub_method("delete", 24),
            ],
        )
        module = _isp_module(interface, impl_a, impl_b)
        out: list = []
        check_fat_interface(module, out)
        assert out == []


class TestNarrowClientUsage:
    """ARCH110: `check_narrow_client_usage`
    (docs/modules/arch.md#isp-checks)."""

    def test_client_using_small_method_subset_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedClass,
            NormalizedFunction,
            NormalizedParam,
        )
        from frob.arch._solid import check_narrow_client_usage

        wide = NormalizedClass(
            name="Client",
            line=1,
            methods=[
                _stub_method("connect", 2),
                _stub_method("read", 3),
                _stub_method("write", 4),
                _stub_method("close", 5),
                _stub_method("flush", 6),
            ],
        )
        user_fn = NormalizedFunction(
            name="save_once",
            line=10,
            body_line_count=2,
            params=[NormalizedParam(name="client", type="Client")],
            calls=[NormalizedCall(callee="client.write", line=11)],
        )
        from frob.arch._normalized import NormalizedModule

        module = NormalizedModule(
            path="pkg/mod.py", language="python", classes=[wide], functions=[user_fn]
        )
        out: list = []
        check_narrow_client_usage(module, out)
        assert len(out) == 1
        assert out[0].category == "narrow-client-usage"
        assert out[0].symref == "save_once"
        assert out[0].metric == 4  # 5 methods - 1 used

    def test_client_using_most_of_interface_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedClass,
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
        )
        from frob.arch._solid import check_narrow_client_usage

        wide = NormalizedClass(
            name="Client",
            line=1,
            methods=[
                _stub_method("connect", 2),
                _stub_method("read", 3),
                _stub_method("write", 4),
                _stub_method("close", 5),
                _stub_method("flush", 6),
            ],
        )
        user_fn = NormalizedFunction(
            name="save_everything",
            line=10,
            body_line_count=5,
            params=[NormalizedParam(name="client", type="Client")],
            calls=[
                NormalizedCall(callee="client.connect", line=11),
                NormalizedCall(callee="client.write", line=12),
                NormalizedCall(callee="client.flush", line=13),
                NormalizedCall(callee="client.close", line=14),
            ],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", classes=[wide], functions=[user_fn]
        )
        out: list = []
        check_narrow_client_usage(module, out)
        assert out == []


class TestRunIspChecks:
    """`run_isp_checks` combines every ARCH1xx ISP check
    (docs/modules/arch.md#isp-checks)."""

    def test_combines_both_checks(self) -> None:
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedClass,
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
        )
        from frob.arch._solid import run_isp_checks

        interface = NormalizedClass(
            name="Repo",
            line=1,
            bases=["ABC"],
            methods=[
                _stub_method("create", 2),
                _stub_method("read", 3),
                _stub_method("update", 4),
                _stub_method("delete", 5),
            ],
        )
        impl_a = NormalizedClass(
            name="ImplA",
            line=10,
            bases=["Repo"],
            methods=[_stub_method("create", 11), _stub_method("read", 12)],
        )
        impl_b = NormalizedClass(
            name="ImplB",
            line=20,
            bases=["Repo"],
            methods=[_stub_method("create", 21), _stub_method("read", 22)],
        )
        user_fn = NormalizedFunction(
            name="save_once",
            line=30,
            body_line_count=2,
            params=[NormalizedParam(name="repo", type="Repo")],
            calls=[NormalizedCall(callee="repo.create", line=31)],
        )
        module = NormalizedModule(
            path="pkg/mod.py",
            language="python",
            classes=[interface, impl_a, impl_b],
            functions=[user_fn],
        )
        out = run_isp_checks(module)
        categories = {s.category for s in out}
        assert "fat-interface" in categories
        assert "narrow-client-usage" in categories
