"""Split from tests/unit/test_arch.py (T-1201)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.arch_suite.conftest import HAS_ARCH

pytestmark = pytest.mark.skipif(not HAS_ARCH, reason="frob.arch not available")


class TestLayeringConfig:
    """`LayeringConfig.layer_for` (docs/modules/arch.md#dip-layering-contract)."""

    def test_layer_for_longest_prefix_match(self) -> None:
        from frob.arch._layering import LayeringConfig

        config = LayeringConfig(
            layers={
                "app": ["src/app"],
                "app_admin": ["src/app/admin"],
            },
            allow={},
        )
        assert config.layer_for("src/app/admin/views.py") == "app_admin"
        assert config.layer_for("src/app/main.py") == "app"

    def test_layer_for_unmatched_path_is_none(self) -> None:
        from frob.arch._layering import LayeringConfig

        config = LayeringConfig(layers={"app": ["src/app"]}, allow={})
        assert config.layer_for("src/other/mod.py") is None


class TestLoadLayeringConfig:
    """`load_layering_config` (docs/modules/arch.md#dip-layering-contract)."""

    def test_missing_frob_toml_returns_none(self, tmp_path: Path) -> None:
        from frob.arch._layering import load_layering_config

        assert load_layering_config(tmp_path) is None

    def test_parses_declared_layers_and_allow_table(self, tmp_path: Path) -> None:
        from frob.arch._layering import load_layering_config

        (tmp_path / "frob.toml").write_text(
            "[arch.layering.layers]\n"
            'app = ["src/app"]\n'
            'lang = ["src/lang"]\n\n'
            "[arch.layering.allow]\n"
            'app = ["lang"]\n'
            "lang = []\n"
        )
        config = load_layering_config(tmp_path)
        assert config is not None
        assert config.layers["app"] == ["src/app"]
        assert config.allow["app"] == ["lang"]



class TestLayeringViolations:
    """`check_layering_violations`
    (docs/modules/arch.md#dip-layering-contract)."""

    def test_disallowed_cross_layer_edge_flagged(self, tmp_path: Path) -> None:
        from frob.arch._layering import LayeringConfig, check_layering_violations

        (tmp_path / "app").mkdir()
        (tmp_path / "lang").mkdir()
        (tmp_path / "app" / "__init__.py").write_text("")
        (tmp_path / "app" / "main.py").write_text("import lang.core\n")
        (tmp_path / "lang" / "__init__.py").write_text("")
        (tmp_path / "lang" / "core.py").write_text("import app.main\n")

        config = LayeringConfig(
            layers={"app": ["app"], "lang": ["lang"]},
            allow={"app": ["lang"], "lang": []},
        )
        out = check_layering_violations(tmp_path, config)
        violations = [s for s in out if s.file == "lang/core.py"]
        assert len(violations) == 1
        assert violations[0].category == "dip-layering-violation"

    def test_allowed_cross_layer_edge_not_flagged(self, tmp_path: Path) -> None:
        from frob.arch._layering import LayeringConfig, check_layering_violations

        (tmp_path / "app").mkdir()
        (tmp_path / "lang").mkdir()
        (tmp_path / "app" / "__init__.py").write_text("")
        (tmp_path / "app" / "main.py").write_text("import lang.core\n")
        (tmp_path / "lang" / "__init__.py").write_text("")
        (tmp_path / "lang" / "core.py").write_text("")

        config = LayeringConfig(
            layers={"app": ["app"], "lang": ["lang"]},
            allow={"app": ["lang"], "lang": []},
        )
        out = check_layering_violations(tmp_path, config)
        assert [s for s in out if s.category == "dip-layering-violation"] == []

    def test_dynamic_import_in_layered_file_flagged(self, tmp_path: Path) -> None:
        from frob.arch._layering import LayeringConfig, check_layering_violations

        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "__init__.py").write_text("")
        (tmp_path / "app" / "main.py").write_text(
            "import importlib\nmod = importlib.import_module('lang.core')\n"
        )

        config = LayeringConfig(layers={"app": ["app"]}, allow={"app": []})
        out = check_layering_violations(tmp_path, config)
        hits = [s for s in out if s.file == "app/main.py"]
        assert len(hits) == 1
        assert hits[0].category == "dip-layering-violation"
        assert "dynamic import" in hits[0].message


class TestNoDiConstructionSmell:
    """`check_no_di_construction`
    (docs/modules/arch.md#no-di-construction-smell)."""

    def test_inline_construction_outside_init_flagged(self) -> None:
        from frob.arch._layering import check_no_di_construction
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedClass,
            NormalizedFunction,
            NormalizedModule,
        )

        service = NormalizedClass(name="Emailer", line=1, methods=[])
        worker = NormalizedClass(
            name="Worker",
            line=5,
            methods=[
                NormalizedFunction(
                    name="run",
                    line=6,
                    body_line_count=2,
                    is_method=True,
                    calls=[NormalizedCall(callee="Emailer", line=7)],
                )
            ],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", classes=[service, worker]
        )
        out = check_no_di_construction(module)
        assert len(out) == 1
        assert out[0].category == "no-di-construction"
        assert out[0].symref == "pkg/mod.py::Worker.run"

    def test_construction_inside_init_not_flagged(self) -> None:
        from frob.arch._layering import check_no_di_construction
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedClass,
            NormalizedFunction,
            NormalizedModule,
        )

        service = NormalizedClass(name="Emailer", line=1, methods=[])
        worker = NormalizedClass(
            name="Worker",
            line=5,
            methods=[
                NormalizedFunction(
                    name="__init__",
                    line=6,
                    body_line_count=2,
                    is_method=True,
                    calls=[NormalizedCall(callee="Emailer", line=7)],
                )
            ],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", classes=[service, worker]
        )
        out = check_no_di_construction(module)
        assert out == []

    def test_construction_inside_factory_function_not_flagged(self) -> None:
        from frob.arch._layering import check_no_di_construction
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedClass,
            NormalizedFunction,
            NormalizedModule,
        )

        service = NormalizedClass(name="Emailer", line=1, methods=[])
        factory = NormalizedFunction(
            name="make_emailer",
            line=5,
            body_line_count=1,
            calls=[NormalizedCall(callee="Emailer", line=6)],
        )
        module = NormalizedModule(
            path="pkg/mod.py",
            language="python",
            classes=[service],
            functions=[factory],
        )
        out = check_no_di_construction(module)
        assert out == []


class TestIllegalStatesRepresentable:
    """`check_illegal_states_representable`
    (docs/modules/arch.md#type-driven-design-checks)."""

    def test_bool_field_cross_field_guard_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedClass,
            NormalizedField,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )
        from frob.arch._typedesign import check_illegal_states_representable

        cls = NormalizedClass(
            name="Payment",
            line=1,
            fields=[
                NormalizedField(name="is_refund", line=2, type="bool"),
                NormalizedField(name="amount", line=3, type="int"),
            ],
            methods=[
                NormalizedFunction(
                    name="__init__",
                    line=4,
                    body_line_count=3,
                    is_method=True,
                    branches=[
                        NormalizedBranch(
                            line=5, condition_text="is_refund and amount > 0"
                        )
                    ],
                    raises=[NormalizedRaise(line=6, exception_type="ValueError")],
                )
            ],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", classes=[cls])
        out = check_illegal_states_representable(module)
        assert len(out) == 1
        assert out[0].category == "illegal-states-representable"
        assert out[0].symref == "pkg/mod.py::Payment.__init__"

    def test_bool_field_alone_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedClass,
            NormalizedField,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )
        from frob.arch._typedesign import check_illegal_states_representable

        cls = NormalizedClass(
            name="Payment",
            line=1,
            fields=[NormalizedField(name="is_refund", line=2, type="bool")],
            methods=[
                NormalizedFunction(
                    name="__init__",
                    line=4,
                    body_line_count=3,
                    is_method=True,
                    branches=[NormalizedBranch(line=5, condition_text="is_refund")],
                    raises=[NormalizedRaise(line=6, exception_type="ValueError")],
                )
            ],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", classes=[cls])
        out = check_illegal_states_representable(module)
        assert out == []


class TestPrimitiveObsession:
    """`check_primitive_obsession`
    (docs/modules/arch.md#type-driven-design-checks)."""

    def test_three_plus_raw_params_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
        )
        from frob.arch._typedesign import check_primitive_obsession

        func = NormalizedFunction(
            name="make_address",
            line=1,
            body_line_count=1,
            params=[
                NormalizedParam(name="street", type="str"),
                NormalizedParam(name="city", type="str"),
                NormalizedParam(name="zip_code", type="str"),
            ],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_primitive_obsession(module)
        assert len(out) == 1
        assert out[0].category == "primitive-obsession"
        assert out[0].metric == 3

    def test_two_raw_params_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
        )
        from frob.arch._typedesign import check_primitive_obsession

        func = NormalizedFunction(
            name="add",
            line=1,
            body_line_count=1,
            params=[
                NormalizedParam(name="a", type="int"),
                NormalizedParam(name="b", type="int"),
            ],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_primitive_obsession(module)
        assert out == []


class TestParseDontValidate:
    """`check_parse_dont_validate`
    (docs/modules/arch.md#type-driven-design-checks)."""

    def test_validates_then_returns_same_type_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
            NormalizedRaise,
        )
        from frob.arch._typedesign import check_parse_dont_validate

        func = NormalizedFunction(
            name="validate_email",
            line=1,
            body_line_count=3,
            params=[NormalizedParam(name="email", type="str")],
            return_type="str",
            branches=[NormalizedBranch(line=2, condition_text="'@' not in email")],
            raises=[NormalizedRaise(line=3, exception_type="ValueError")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_parse_dont_validate(module)
        assert len(out) == 1
        assert out[0].category == "parse-dont-validate"
        assert out[0].symref == "validate_email"

    def test_validates_then_returns_refined_type_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
            NormalizedRaise,
        )
        from frob.arch._typedesign import check_parse_dont_validate

        func = NormalizedFunction(
            name="parse_email",
            line=1,
            body_line_count=3,
            params=[NormalizedParam(name="email", type="str")],
            return_type="EmailAddress",
            branches=[NormalizedBranch(line=2, condition_text="'@' not in email")],
            raises=[NormalizedRaise(line=3, exception_type="ValueError")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_parse_dont_validate(module)
        assert out == []


class TestBooleanFlagParam:
    """`check_boolean_flag_param`
    (docs/modules/arch.md#type-driven-design-checks)."""

    def test_public_function_branching_on_bool_param_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
        )
        from frob.arch._typedesign import check_boolean_flag_param

        func = NormalizedFunction(
            name="save",
            line=1,
            body_line_count=2,
            params=[NormalizedParam(name="overwrite", type="bool")],
            branches=[NormalizedBranch(line=2, condition_text="overwrite")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_boolean_flag_param(module)
        assert len(out) == 1
        assert out[0].category == "boolean-flag-param"
        assert out[0].metric == 1

    def test_private_function_not_flagged(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
        )
        from frob.arch._typedesign import check_boolean_flag_param

        func = NormalizedFunction(
            name="_save",
            line=1,
            body_line_count=2,
            params=[NormalizedParam(name="overwrite", type="bool")],
            branches=[NormalizedBranch(line=2, condition_text="overwrite")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_boolean_flag_param(module)
        assert out == []


class TestRunTypeDesignChecks:
    """`run_typedesign_checks` combines every ARCH1xx type-driven-design
    check (docs/modules/arch.md#type-driven-design-checks)."""

    def test_combines_all_four_checks(self) -> None:
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedClass,
            NormalizedField,
            NormalizedFunction,
            NormalizedModule,
            NormalizedParam,
            NormalizedRaise,
        )
        from frob.arch._typedesign import run_typedesign_checks

        payment = NormalizedClass(
            name="Payment",
            line=1,
            fields=[
                NormalizedField(name="is_refund", line=2, type="bool"),
                NormalizedField(name="amount", line=3, type="int"),
            ],
            methods=[
                NormalizedFunction(
                    name="__init__",
                    line=4,
                    body_line_count=3,
                    is_method=True,
                    branches=[
                        NormalizedBranch(
                            line=5, condition_text="is_refund and amount > 0"
                        )
                    ],
                    raises=[NormalizedRaise(line=6, exception_type="ValueError")],
                )
            ],
        )
        save_fn = NormalizedFunction(
            name="save",
            line=10,
            body_line_count=2,
            params=[NormalizedParam(name="overwrite", type="bool")],
            branches=[NormalizedBranch(line=11, condition_text="overwrite")],
        )
        module = NormalizedModule(
            path="pkg/mod.py",
            language="python",
            classes=[payment],
            functions=[save_fn],
        )
        out = run_typedesign_checks(module)
        categories = {s.category for s in out}
        assert "illegal-states-representable" in categories
        assert "boolean-flag-param" in categories
