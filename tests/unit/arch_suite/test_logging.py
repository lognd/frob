"""Split from tests/unit/test_arch.py (T-1201)."""

from __future__ import annotations

import pytest

from tests.unit.arch_suite.conftest import HAS_ARCH

pytestmark = pytest.mark.skipif(not HAS_ARCH, reason="frob.arch not available")


class TestUnloggedErrorPath:
    """`check_unlogged_error_path`
    (docs/modules/arch.md#logging-discipline-checks)."""

    def test_catch_with_no_nearby_log_call_flagged(self) -> None:
        from frob.arch._logging_checks import check_unlogged_error_path
        from frob.arch._normalized import (
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
        )

        func = NormalizedFunction(
            name="load_config",
            line=1,
            body_line_count=4,
            catches=[NormalizedCatch(line=3, exception_type="OSError")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_unlogged_error_path(module)
        assert len(out) == 1
        assert out[0].category == "unlogged-error-path"
        assert out[0].symref == "load_config"

    def test_catch_with_nearby_log_call_not_flagged(self) -> None:
        from frob.arch._logging_checks import check_unlogged_error_path
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
        )

        func = NormalizedFunction(
            name="load_config",
            line=1,
            body_line_count=4,
            catches=[NormalizedCatch(line=3, exception_type="OSError")],
            calls=[NormalizedCall(callee="logger.error", line=4)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_unlogged_error_path(module)
        assert out == []


class TestUnloggedBoundary:
    """`check_unlogged_boundary`
    (docs/modules/arch.md#logging-discipline-checks)."""

    def test_public_entry_point_with_no_log_call_flagged(self) -> None:
        from frob.arch._logging_checks import check_unlogged_boundary
        from frob.arch._normalized import NormalizedFunction, NormalizedModule

        func = NormalizedFunction(name="run", line=1, body_line_count=2)
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_unlogged_boundary(module)
        assert any(s.category == "unlogged-boundary" for s in out)
        assert any(s.symref == "run" for s in out)

    def test_boundary_call_with_no_nearby_log_call_flagged(self) -> None:
        from frob.arch._logging_checks import check_unlogged_boundary
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )

        func = NormalizedFunction(
            name="run",
            line=1,
            body_line_count=4,
            calls=[
                NormalizedCall(callee="logger.info", line=1),
                NormalizedCall(callee="subprocess.run", line=10),
            ],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_unlogged_boundary(module)
        assert any(s.category == "unlogged-boundary" and s.line == 10 for s in out)

    def test_private_function_not_flagged(self) -> None:
        from frob.arch._logging_checks import check_unlogged_boundary
        from frob.arch._normalized import NormalizedFunction, NormalizedModule

        func = NormalizedFunction(name="_run", line=1, body_line_count=2)
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_unlogged_boundary(module)
        assert out == []


class TestPrintAsDiagnostic:
    """`check_print_as_diagnostic`
    (docs/modules/arch.md#logging-discipline-checks)."""

    def test_print_call_flagged(self) -> None:
        from frob.arch._logging_checks import check_print_as_diagnostic
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )

        func = NormalizedFunction(
            name="run",
            line=1,
            body_line_count=2,
            calls=[NormalizedCall(callee="print", line=2)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_print_as_diagnostic(module)
        assert len(out) == 1
        assert out[0].category == "print-as-diagnostic"

    def test_print_call_in_cli_module_not_flagged(self) -> None:
        from frob.arch._logging_checks import check_print_as_diagnostic
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )

        func = NormalizedFunction(
            name="run",
            line=1,
            body_line_count=2,
            calls=[NormalizedCall(callee="print", line=2)],
        )
        module = NormalizedModule(
            path="pkg/cli.py", language="python", functions=[func]
        )
        out = check_print_as_diagnostic(module)
        assert out == []


class TestRunLoggingChecks:
    """`run_logging_checks` combines every ARCH1xx logging-discipline check
    (docs/modules/arch.md#logging-discipline-checks)."""

    def test_combines_all_three_checks(self) -> None:
        from frob.arch._logging_checks import run_logging_checks
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
        )

        catch_fn = NormalizedFunction(
            name="load_config",
            line=1,
            body_line_count=4,
            catches=[NormalizedCatch(line=3, exception_type="OSError")],
        )
        print_fn = NormalizedFunction(
            name="run",
            line=10,
            body_line_count=2,
            calls=[NormalizedCall(callee="print", line=11)],
        )
        module = NormalizedModule(
            path="pkg/mod.py",
            language="python",
            functions=[catch_fn, print_fn],
        )
        out = run_logging_checks(module)
        categories = {s.category for s in out}
        assert "unlogged-error-path" in categories
        assert "unlogged-boundary" in categories
        assert "print-as-diagnostic" in categories


class TestUnhandledResult:
    """`check_unhandled_result`
    (docs/modules/arch.md#fallibility-checks)."""

    def test_bare_statement_call_to_result_function_flagged(self) -> None:
        from frob.arch._fallibility import check_unhandled_result
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )

        load = NormalizedFunction(
            name="load", line=1, body_line_count=1, return_type="Result[Config, Err]"
        )
        run = NormalizedFunction(
            name="run",
            line=5,
            body_line_count=2,
            calls=[NormalizedCall(callee="load", line=6)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[load, run]
        )
        out = check_unhandled_result(module)
        assert len(out) == 1
        assert out[0].category == "unhandled-result"
        assert out[0].symref == "run"

    def test_returned_call_to_result_function_not_flagged(self) -> None:
        from frob.arch._fallibility import check_unhandled_result
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
            NormalizedReturn,
        )

        load = NormalizedFunction(
            name="load", line=1, body_line_count=1, return_type="Result[Config, Err]"
        )
        run = NormalizedFunction(
            name="run",
            line=5,
            body_line_count=2,
            calls=[NormalizedCall(callee="load", line=6)],
            returns=[NormalizedReturn(line=6, value_text="load()")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[load, run]
        )
        out = check_unhandled_result(module)
        assert out == []


class TestSwallowedException:
    """`check_swallowed_exception`
    (docs/modules/arch.md#fallibility-checks)."""

    def test_bare_except_with_no_reaction_flagged(self) -> None:
        from frob.arch._fallibility import check_swallowed_exception
        from frob.arch._normalized import (
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
        )

        func = NormalizedFunction(
            name="load",
            line=1,
            body_line_count=4,
            catches=[NormalizedCatch(line=3, exception_type=None)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_swallowed_exception(module)
        assert len(out) == 1
        assert out[0].category == "swallowed-exception"
        assert out[0].severity == "warning"

    def test_except_with_nearby_log_call_not_flagged(self) -> None:
        from frob.arch._fallibility import check_swallowed_exception
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
        )

        func = NormalizedFunction(
            name="load",
            line=1,
            body_line_count=4,
            catches=[NormalizedCatch(line=3, exception_type=None)],
            calls=[NormalizedCall(callee="logger.warning", line=4)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_swallowed_exception(module)
        assert out == []


class TestRecoverableErrorWrongSignature:
    """`check_recoverable_error_wrong_signature`
    (docs/modules/arch.md#fallibility-checks)."""

    def test_raises_value_error_without_result_signature_flagged(self) -> None:
        from frob.arch._fallibility import check_recoverable_error_wrong_signature
        from frob.arch._normalized import (
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        func = NormalizedFunction(
            name="parse_amount",
            line=1,
            body_line_count=2,
            return_type="int",
            raises=[NormalizedRaise(line=2, exception_type="ValueError")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_recoverable_error_wrong_signature(module)
        assert len(out) == 1
        assert out[0].category == "recoverable-error-wrong-signature"
        assert out[0].symref == "parse_amount"

    def test_raises_value_error_with_result_signature_not_flagged(self) -> None:
        from frob.arch._fallibility import check_recoverable_error_wrong_signature
        from frob.arch._normalized import (
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        func = NormalizedFunction(
            name="parse_amount",
            line=1,
            body_line_count=2,
            return_type="Result[int, ParseError]",
            raises=[NormalizedRaise(line=2, exception_type="ValueError")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_recoverable_error_wrong_signature(module)
        assert out == []


class TestOverBroadExcept:
    """`check_over_broad_except`
    (docs/modules/arch.md#fallibility-checks)."""

    def test_bare_except_flagged(self) -> None:
        from frob.arch._fallibility import check_over_broad_except
        from frob.arch._normalized import (
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
        )

        func = NormalizedFunction(
            name="load",
            line=1,
            body_line_count=3,
            catches=[NormalizedCatch(line=2, exception_type="Exception")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_over_broad_except(module)
        assert any(s.category == "over-broad-except" for s in out)

    def test_specific_except_not_flagged(self) -> None:
        from frob.arch._fallibility import check_over_broad_except
        from frob.arch._normalized import (
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
        )

        func = NormalizedFunction(
            name="load",
            line=1,
            body_line_count=3,
            catches=[NormalizedCatch(line=2, exception_type="OSError")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_over_broad_except(module)
        assert out == []

    def test_reraise_with_different_type_loses_context_flagged(self) -> None:
        from frob.arch._fallibility import check_over_broad_except
        from frob.arch._normalized import (
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        func = NormalizedFunction(
            name="load",
            line=1,
            body_line_count=4,
            catches=[NormalizedCatch(line=2, exception_type="OSError")],
            raises=[NormalizedRaise(line=3, exception_type="RuntimeError")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )
        out = check_over_broad_except(module)
        assert any(
            "losing context" in (s.message or "").lower()
            or "context" in (s.detail or "").lower()
            for s in out
        )


class TestRunFallibilityChecks:
    """`run_fallibility_checks` combines every ARCH1xx fallibility check
    (docs/modules/arch.md#fallibility-checks)."""

    def test_combines_all_four_checks(self) -> None:
        from frob.arch._fallibility import run_fallibility_checks
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        load = NormalizedFunction(
            name="load", line=1, body_line_count=1, return_type="Result[Config, Err]"
        )
        run_fn = NormalizedFunction(
            name="run",
            line=5,
            body_line_count=6,
            return_type="int",
            calls=[NormalizedCall(callee="load", line=6)],
            catches=[NormalizedCatch(line=7, exception_type=None)],
            raises=[NormalizedRaise(line=30, exception_type="ValueError")],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[load, run_fn]
        )
        out = run_fallibility_checks(module)
        categories = {s.category for s in out}
        assert "unhandled-result" in categories
        assert "swallowed-exception" in categories
        assert "recoverable-error-wrong-signature" in categories
        assert "over-broad-except" in categories
