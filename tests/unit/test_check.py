"""Direct (non-CLI) unit tests for frob.check's public functions and CheckResult."""

from __future__ import annotations

from pathlib import Path

from frob.check import (
    CheckResult,
    detect_project_type,
    run_check,
    run_check_cpp,
    run_check_rust,
    run_check_ts,
)
from frob.process.parsers.common import Diagnostic, ToolResult


class TestCheckResultCounts:
    def test_total_errors_sums_across_results(self) -> None:
        # frob:tests src/frob/check/__init__.py::CheckResult.total_errors kind="unit"
        result = CheckResult(
            path=".",
            results=[
                ToolResult(
                    tool="a",
                    diagnostics=[
                        Diagnostic(severity="error", message="x"),
                        Diagnostic(severity="warning", message="y"),
                    ],
                ),
                ToolResult(
                    tool="b",
                    diagnostics=[Diagnostic(severity="error", message="z")],
                ),
            ],
        )
        assert result.total_errors == 2

    def test_total_warnings_sums_across_results(self) -> None:
        # frob:tests src/frob/check/__init__.py::CheckResult.total_warnings kind="unit"
        result = CheckResult(
            path=".",
            results=[
                ToolResult(
                    tool="a",
                    diagnostics=[
                        Diagnostic(severity="warning", message="x"),
                        Diagnostic(severity="warning", message="y"),
                    ],
                ),
                ToolResult(tool="b", diagnostics=[]),
            ],
        )
        assert result.total_warnings == 2

    def test_zero_results_is_zero(self) -> None:
        result = CheckResult(path=".", results=[])
        assert result.total_errors == 0
        assert result.total_warnings == 0


class TestRunCheck:
    def test_all_stages_skipped_returns_empty_result_for_root(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/__init__.py::run_check kind="unit"
        result = run_check(
            tmp_path,
            skip_ruff=True,
            skip_ty=True,
            skip_arch=True,
            skip_cycle=True,
            skip_dup=True,
            skip_bind=True,
            skip_exports=True,
            skip_gates=True,
        )
        assert isinstance(result, CheckResult)
        assert result.path == str(tmp_path)
        assert result.results == []
        assert result.total_errors == 0


class TestRunCheckCpp:
    def test_all_stages_skipped_returns_empty_result(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/__init__.py::run_check_cpp kind="unit"
        result = run_check_cpp(
            tmp_path,
            skip_build=True,
            skip_clang_tidy=True,
            skip_clang_format=True,
            skip_tests=True,
        )
        assert isinstance(result, CheckResult)
        assert result.path == str(tmp_path)
        assert result.results == []


class TestRunCheckRust:
    def test_all_stages_skipped_returns_empty_result(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/__init__.py::run_check_rust kind="unit"
        result = run_check_rust(
            tmp_path,
            skip_check=True,
            skip_clippy=True,
            skip_fmt=True,
            skip_tests=True,
        )
        assert isinstance(result, CheckResult)
        assert result.path == str(tmp_path)
        assert result.results == []


class TestRunCheckTs:
    def test_all_stages_skipped_returns_empty_result(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/__init__.py::run_check_ts kind="unit"
        result = run_check_ts(
            tmp_path,
            skip_tsc=True,
            skip_eslint=True,
            skip_prettier=True,
            skip_tests=True,
        )
        assert isinstance(result, CheckResult)
        assert result.path == str(tmp_path)
        assert result.results == []


class TestDetectProjectType:
    def test_cargo_toml_is_rust(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/__init__.py::detect_project_type kind="unit"
        (tmp_path / "Cargo.toml").write_text("[package]\n")
        assert detect_project_type(tmp_path) == "rust"

    def test_cmakelists_is_cpp(self, tmp_path: Path) -> None:
        (tmp_path / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.20)\n"
        )
        assert detect_project_type(tmp_path) == "cpp"

    def test_pyproject_is_python(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
        assert detect_project_type(tmp_path) == "python"

    def test_package_json_and_tsconfig_is_typescript(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / "tsconfig.json").write_text("{}")
        assert detect_project_type(tmp_path) == "typescript"

    def test_no_sentinel_is_unknown(self, tmp_path: Path) -> None:
        assert detect_project_type(tmp_path) == "unknown"


def test_check_run_check_arch_integration(tmp_path: Path) -> None:
    # frob:tests src/frob/check kind="integration"
    # Exercises frob.check across a real analysis boundary: run_check with the
    # arch stage drives frob.arch.analyze_project over a real source tree and
    # aggregates its diagnostics into a CheckResult. A file with a deliberately
    # over-long function must surface a frob-arch diagnostic, proving the
    # orchestration wiring reaches the analyzer and back, not a stub.
    long_body = "\n".join(f"    x{i} = {i}" for i in range(80))
    (tmp_path / "big.py").write_text(f"def huge():\n{long_body}\n    return x0\n")

    result = run_check(tmp_path, only=frozenset({"arch"}))
    assert isinstance(result, CheckResult)
    arch_results = [r for r in result.results if r.tool in {"frob-arch"}]
    assert arch_results, "arch stage should have produced a ToolResult"
    codes = {d.code for r in arch_results for d in r.diagnostics}
    assert "long-function" in codes
