# frob:ticket T-1309
# frob:ticket T-1507
"""Real-behavior tests for `frob.check._native`'s cargo AND cmake/clang/
ctest/valgrind runners (T-1309/T-1507 TEST005 burn-down): the success,
kill-switch-disabled, and unexpected-crash paths for
`_run_cargo`/`_run_cargo_fmt_check`/`_run_cargo_test`, and the
success/skip/missing-binary/crash paths for `_cmake_configure`/
`_run_cmake_build`/`_run_clang_tidy_cmake`/`_run_clang_format`/
`_run_ctest`/`_ctest_result`/`_run_cargo_valgrind`/
`_find_test_binary_from_cargo_json`, none of which any prior test
exercised (only the missing-binary path was covered, in
`tests/unit/test_check_tool_unavailable.py`).
"""

from __future__ import annotations

from pathlib import Path

from typani import Err, Ok

from frob.check import _native as native_mod
from frob.process._guard import ProcessGuardError
from frob.process.parsers.common import ToolResult
from tests.unit.conftest import _FakeCompletedProcess


class TestRunCargoRealPaths:
    def test_success_parses_cargo_json(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoRealPaths.test_success_parses_cargo_json  # noqa: E501
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(_FakeCompletedProcess(stdout="", returncode=0)),
        )
        result = native_mod._run_cargo("check", tmp_path)
        assert result is not None
        assert result.tool == "cargo-check"
        assert result.exit_code == 0

    def test_kill_switch_disabled(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoRealPaths.test_kill_switch_disabled  # noqa: E501
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Err(ProcessGuardError.ExecDisabled),
        )
        result = native_mod._run_cargo("clippy", tmp_path)
        assert result is not None
        assert not result.passed

    def test_unexpected_crash_is_typed_result(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoRealPaths.test_unexpected_crash_is_typed_result  # noqa: E501
        def _raise(*a, **kw):
            raise RuntimeError("simulated: unexpected crash")

        monkeypatch.setattr(native_mod, "guarded_subprocess_run", _raise)
        result = native_mod._run_cargo("check", tmp_path)
        assert result is not None
        assert not result.passed


class TestRunCargoFmtCheckRealPaths:
    def test_all_formatted_is_clean_pass(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoFmtCheckRealPaths.test_all_formatted_is_clean_pass  # noqa: E501
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(_FakeCompletedProcess(stdout="", returncode=0)),
        )
        result = native_mod._run_cargo_fmt_check(tmp_path)
        assert result is not None
        assert result.exit_code == 0
        assert "formatted" in result.summary

    def test_unformatted_lines_produce_warning_diagnostics(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoFmtCheckRealPaths.test_unformatted_lines_produce_warning_diagnostics  # noqa: E501
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(
                _FakeCompletedProcess(stdout="Diff in src/lib.rs\n", returncode=1)
            ),
        )
        result = native_mod._run_cargo_fmt_check(tmp_path)
        assert result is not None
        assert result.exit_code == 1
        assert len(result.diagnostics) == 1

    def test_kill_switch_disabled(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoFmtCheckRealPaths.test_kill_switch_disabled  # noqa: E501
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Err(ProcessGuardError.ExecDisabled),
        )
        result = native_mod._run_cargo_fmt_check(tmp_path)
        assert result is not None
        assert not result.passed


class TestRunCargoTestRealPaths:
    def test_success_parses_cargo_json(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoTestRealPaths.test_success_parses_cargo_json  # noqa: E501
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(_FakeCompletedProcess(stdout="", returncode=0)),
        )
        result = native_mod._run_cargo_test(tmp_path)
        assert result is not None
        assert result.tool == "cargo-test"

    def test_kill_switch_disabled(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoTestRealPaths.test_kill_switch_disabled  # noqa: E501
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Err(ProcessGuardError.ExecDisabled),
        )
        result = native_mod._run_cargo_test(tmp_path)
        assert result is not None
        assert not result.passed

    def test_unexpected_crash_is_typed_result(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoTestRealPaths.test_unexpected_crash_is_typed_result  # noqa: E501
        def _raise(*a, **kw):
            raise RuntimeError("simulated: unexpected crash")

        monkeypatch.setattr(native_mod, "guarded_subprocess_run", _raise)
        result = native_mod._run_cargo_test(tmp_path)
        assert result is not None
        assert not result.passed


# frob:ticket T-1507
class TestCmakeConfigureRealPaths:
    def test_success_returns_none(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestCmakeConfigureRealPaths.test_success_returns_none  # noqa: E501
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(_FakeCompletedProcess(returncode=0)),
        )
        assert native_mod._cmake_configure(tmp_path, tmp_path) is None

    def test_nonzero_exit_returns_typed_result(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestCmakeConfigureRealPaths.test_nonzero_exit_returns_typed_result  # noqa: E501
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(
                _FakeCompletedProcess(stderr="CMake Error: bad\n", returncode=1)
            ),
        )
        result = native_mod._cmake_configure(tmp_path, tmp_path)
        assert result is not None
        assert result.exit_code == 1
        assert result.diagnostics

    def test_missing_binary_is_typed_result(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestCmakeConfigureRealPaths.test_missing_binary_is_typed_result  # noqa: E501
        def _raise(*a, **kw):
            raise FileNotFoundError()

        monkeypatch.setattr(native_mod, "guarded_subprocess_run", _raise)
        result = native_mod._cmake_configure(tmp_path, tmp_path)
        assert result is not None
        assert not result.passed

    def test_unexpected_crash_is_typed_result(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestCmakeConfigureRealPaths.test_unexpected_crash_is_typed_result  # noqa: E501
        def _raise(*a, **kw):
            raise RuntimeError("simulated: unexpected crash")

        monkeypatch.setattr(native_mod, "guarded_subprocess_run", _raise)
        result = native_mod._cmake_configure(tmp_path, tmp_path)
        assert result is not None
        assert not result.passed

    def test_kill_switch_disabled(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestCmakeConfigureRealPaths.test_kill_switch_disabled  # noqa: E501
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Err(ProcessGuardError.ExecDisabled),
        )
        result = native_mod._cmake_configure(tmp_path, tmp_path)
        assert result is not None
        assert not result.passed


# frob:ticket T-1507
class TestRunCmakeBuildRealPaths:
    def test_configure_failure_short_circuits(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCmakeBuildRealPaths.test_configure_failure_short_circuits  # noqa: E501
        monkeypatch.setattr(
            native_mod,
            "_cmake_configure",
            lambda root, build_dir: ToolResult(
                tool="cmake-configure", exit_code=1, summary="configure failed"
            ),
        )
        result = native_mod._run_cmake_build(tmp_path, tmp_path / "build")
        assert result is not None
        assert result.tool == "cmake-configure"
        assert result.exit_code == 1

    def test_build_success_reports_build_succeeded(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCmakeBuildRealPaths.test_build_success_reports_build_succeeded  # noqa: E501
        monkeypatch.setattr(
            native_mod, "_cmake_configure", lambda root, build_dir: None
        )
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(_FakeCompletedProcess(returncode=0)),
        )
        result = native_mod._run_cmake_build(tmp_path, tmp_path / "build")
        assert result is not None
        assert result.tool == "cmake-build"
        assert result.exit_code == 0

    def test_missing_binary_is_typed_result(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCmakeBuildRealPaths.test_missing_binary_is_typed_result  # noqa: E501
        monkeypatch.setattr(
            native_mod, "_cmake_configure", lambda root, build_dir: None
        )

        def _raise(*a, **kw):
            raise FileNotFoundError()

        monkeypatch.setattr(native_mod, "guarded_subprocess_run", _raise)
        result = native_mod._run_cmake_build(tmp_path, tmp_path / "build")
        assert result is not None
        assert not result.passed

    def test_unexpected_crash_is_typed_result(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCmakeBuildRealPaths.test_unexpected_crash_is_typed_result  # noqa: E501
        monkeypatch.setattr(
            native_mod, "_cmake_configure", lambda root, build_dir: None
        )

        def _raise(*a, **kw):
            raise RuntimeError("simulated: unexpected crash")

        monkeypatch.setattr(native_mod, "guarded_subprocess_run", _raise)
        result = native_mod._run_cmake_build(tmp_path, tmp_path / "build")
        assert result is not None
        assert not result.passed

    def test_kill_switch_disabled(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCmakeBuildRealPaths.test_kill_switch_disabled  # noqa: E501
        monkeypatch.setattr(
            native_mod, "_cmake_configure", lambda root, build_dir: None
        )
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Err(ProcessGuardError.ExecDisabled),
        )
        result = native_mod._run_cmake_build(tmp_path, tmp_path / "build")
        assert result is not None
        assert not result.passed


# frob:ticket T-1507
class TestRunClangTidyCmakeRealPaths:
    def test_no_compile_commands_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunClangTidyCmakeRealPaths.test_no_compile_commands_is_none  # noqa: E501
        assert native_mod._run_clang_tidy_cmake(tmp_path, tmp_path / "build") is None

    def test_no_sources_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunClangTidyCmakeRealPaths.test_no_sources_is_none  # noqa: E501
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        (build_dir / "compile_commands.json").write_text("[]")
        assert native_mod._run_clang_tidy_cmake(tmp_path, build_dir) is None

    def test_success_parses_clang_tidy_output(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunClangTidyCmakeRealPaths.test_success_parses_clang_tidy_output  # noqa: E501
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        (build_dir / "compile_commands.json").write_text("[]")
        (tmp_path / "main.cpp").write_text("int main() { return 0; }\n")
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(_FakeCompletedProcess(returncode=0)),
        )
        result = native_mod._run_clang_tidy_cmake(tmp_path, build_dir)
        assert result is not None

    def test_missing_binary_is_typed_result(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunClangTidyCmakeRealPaths.test_missing_binary_is_typed_result  # noqa: E501
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        (build_dir / "compile_commands.json").write_text("[]")
        (tmp_path / "main.cpp").write_text("int main() { return 0; }\n")

        def _raise(*a, **kw):
            raise FileNotFoundError()

        monkeypatch.setattr(native_mod, "guarded_subprocess_run", _raise)
        result = native_mod._run_clang_tidy_cmake(tmp_path, build_dir)
        assert result is not None
        assert not result.passed

    def test_kill_switch_disabled(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunClangTidyCmakeRealPaths.test_kill_switch_disabled  # noqa: E501
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        (build_dir / "compile_commands.json").write_text("[]")
        (tmp_path / "main.cpp").write_text("int main() { return 0; }\n")
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Err(ProcessGuardError.ExecDisabled),
        )
        result = native_mod._run_clang_tidy_cmake(tmp_path, build_dir)
        assert result is not None
        assert not result.passed

    def test_parse_failure_is_typed_crash_result(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunClangTidyCmakeRealPaths.test_parse_failure_is_typed_crash_result  # noqa: E501
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        (build_dir / "compile_commands.json").write_text("[]")
        (tmp_path / "main.cpp").write_text("int main() { return 0; }\n")
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(_FakeCompletedProcess(returncode=0)),
        )

        def _raise_parse(*a, **kw):
            raise KeyError("simulated: malformed output")

        import frob.process.parsers as parsers_mod

        monkeypatch.setattr(parsers_mod, "parse_clang_tidy", _raise_parse)
        result = native_mod._run_clang_tidy_cmake(tmp_path, build_dir)
        assert result is not None
        assert not result.passed


# frob:ticket T-1507
class TestRunClangFormatRealPaths:
    def test_no_sources_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunClangFormatRealPaths.test_no_sources_is_none  # noqa: E501
        assert native_mod._run_clang_format(tmp_path) is None

    def test_all_formatted_is_clean_pass(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunClangFormatRealPaths.test_all_formatted_is_clean_pass  # noqa: E501
        (tmp_path / "a.cpp").write_text("int x;\n")
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(_FakeCompletedProcess(returncode=0)),
        )
        result = native_mod._run_clang_format(tmp_path)
        assert result is not None
        assert result.exit_code == 0
        assert "formatted" in result.summary

    def test_needs_format_produces_diagnostics(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunClangFormatRealPaths.test_needs_format_produces_diagnostics  # noqa: E501
        (tmp_path / "a.cpp").write_text("int   x;\n")
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(
                _FakeCompletedProcess(
                    stderr="a.cpp:1:1: warning: code should be clang-formatted\n",
                    returncode=1,
                )
            ),
        )
        result = native_mod._run_clang_format(tmp_path)
        assert result is not None
        assert result.exit_code == 1
        assert len(result.diagnostics) == 1

    def test_missing_binary_is_typed_result(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunClangFormatRealPaths.test_missing_binary_is_typed_result  # noqa: E501
        (tmp_path / "a.cpp").write_text("int x;\n")

        def _raise(*a, **kw):
            raise FileNotFoundError()

        monkeypatch.setattr(native_mod, "guarded_subprocess_run", _raise)
        result = native_mod._run_clang_format(tmp_path)
        assert result is not None
        assert not result.passed

    def test_kill_switch_disabled(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunClangFormatRealPaths.test_kill_switch_disabled  # noqa: E501
        (tmp_path / "a.cpp").write_text("int x;\n")
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Err(ProcessGuardError.ExecDisabled),
        )
        result = native_mod._run_clang_format(tmp_path)
        assert result is not None
        assert not result.passed


# frob:ticket T-1507
class TestRunCtestRealPaths:
    def test_missing_build_dir_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCtestRealPaths.test_missing_build_dir_is_none  # noqa: E501
        assert native_mod._run_ctest(tmp_path / "nope") is None

    def test_success_parses_junit_report(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCtestRealPaths.test_success_parses_junit_report  # noqa: E501
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        (build_dir / "results.xml").write_text(
            '<?xml version="1.0"?><testsuite tests="1" failures="0">'
            '<testcase name="t" classname="c"/></testsuite>'
        )
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(_FakeCompletedProcess(returncode=0)),
        )
        result = native_mod._run_ctest(build_dir)
        assert result is not None
        assert result.tool == "ctest"

    def test_falls_back_to_text_parsing_without_junit(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCtestRealPaths.test_falls_back_to_text_parsing_without_junit  # noqa: E501
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(_FakeCompletedProcess(stdout="", returncode=0)),
        )
        result = native_mod._run_ctest(build_dir)
        assert result is not None
        assert result.tool == "ctest"
        assert result.summary == "tests passed"

    def test_malformed_junit_is_typed_crash_result(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCtestRealPaths.test_malformed_junit_is_typed_crash_result  # noqa: E501
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        (build_dir / "results.xml").write_text("not xml at all <<<")
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(_FakeCompletedProcess(returncode=1)),
        )
        result = native_mod._run_ctest(build_dir)
        assert result is not None
        assert not result.passed

    def test_missing_binary_is_typed_result(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCtestRealPaths.test_missing_binary_is_typed_result  # noqa: E501
        build_dir = tmp_path / "build"
        build_dir.mkdir()

        def _raise(*a, **kw):
            raise FileNotFoundError()

        monkeypatch.setattr(native_mod, "guarded_subprocess_run", _raise)
        result = native_mod._run_ctest(build_dir)
        assert result is not None
        assert not result.passed

    def test_unexpected_crash_is_typed_result(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCtestRealPaths.test_unexpected_crash_is_typed_result  # noqa: E501
        build_dir = tmp_path / "build"
        build_dir.mkdir()

        def _raise(*a, **kw):
            raise RuntimeError("simulated: unexpected crash")

        monkeypatch.setattr(native_mod, "guarded_subprocess_run", _raise)
        result = native_mod._run_ctest(build_dir)
        assert result is not None
        assert not result.passed

    def test_kill_switch_disabled(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCtestRealPaths.test_kill_switch_disabled  # noqa: E501
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Err(ProcessGuardError.ExecDisabled),
        )
        result = native_mod._run_ctest(build_dir)
        assert result is not None
        assert not result.passed


# frob:ticket T-1507
class TestFindTestBinaryFromCargoJson:
    def test_finds_test_executable(self) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestFindTestBinaryFromCargoJson.test_finds_test_executable  # noqa: E501
        stdout = (
            '{"reason": "compiler-artifact", "profile": {"test": true}, '
            '"executable": "/tmp/foo-abc123"}\n'
        )
        binary = native_mod._find_test_binary_from_cargo_json(stdout)
        assert binary is not None
        assert str(binary) == "/tmp/foo-abc123"

    def test_ignores_non_test_artifacts(self) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestFindTestBinaryFromCargoJson.test_ignores_non_test_artifacts  # noqa: E501
        stdout = (
            '{"reason": "compiler-artifact", "profile": {"test": false}, '
            '"executable": "/tmp/foo"}\n'
        )
        assert native_mod._find_test_binary_from_cargo_json(stdout) is None

    def test_skips_malformed_json_lines(self) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestFindTestBinaryFromCargoJson.test_skips_malformed_json_lines  # noqa: E501
        stdout = "not json\n"
        assert native_mod._find_test_binary_from_cargo_json(stdout) is None

    def test_no_matching_message_is_none(self) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestFindTestBinaryFromCargoJson.test_no_matching_message_is_none  # noqa: E501
        assert native_mod._find_test_binary_from_cargo_json("") is None


# frob:ticket T-1507
class TestRunCargoValgrindRealPaths:
    def test_no_test_binary_found_is_none(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoValgrindRealPaths.test_no_test_binary_found_is_none  # noqa: E501
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Ok(_FakeCompletedProcess(stdout="", returncode=0)),
        )
        assert native_mod._run_cargo_valgrind(tmp_path) is None

    def test_missing_cargo_binary_is_typed_result(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoValgrindRealPaths.test_missing_cargo_binary_is_typed_result  # noqa: E501
        def _raise(*a, **kw):
            raise FileNotFoundError()

        monkeypatch.setattr(native_mod, "guarded_subprocess_run", _raise)
        result = native_mod._run_cargo_valgrind(tmp_path)
        assert result is not None
        assert not result.passed

    def test_build_kill_switch_disabled(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoValgrindRealPaths.test_build_kill_switch_disabled  # noqa: E501
        monkeypatch.setattr(
            native_mod,
            "guarded_subprocess_run",
            lambda *a, **kw: Err(ProcessGuardError.ExecDisabled),
        )
        result = native_mod._run_cargo_valgrind(tmp_path)
        assert result is not None
        assert not result.passed

    def test_valgrind_success_parses_output(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoValgrindRealPaths.test_valgrind_success_parses_output  # noqa: E501
        binary_json = (
            '{"reason": "compiler-artifact", "profile": {"test": true}, '
            '"executable": "/tmp/foo-test"}\n'
        )
        calls = {"n": 0}

        def _fake_run(*a, **kw):
            calls["n"] += 1
            if calls["n"] == 1:
                return Ok(_FakeCompletedProcess(stdout=binary_json, returncode=0))
            return Ok(_FakeCompletedProcess(stdout="", returncode=0))

        monkeypatch.setattr(native_mod, "guarded_subprocess_run", _fake_run)
        result = native_mod._run_cargo_valgrind(tmp_path)
        assert result is not None
        assert result.tool == "cargo-test(valgrind)"

    def test_missing_valgrind_binary_is_typed_result(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoValgrindRealPaths.test_missing_valgrind_binary_is_typed_result  # noqa: E501
        binary_json = (
            '{"reason": "compiler-artifact", "profile": {"test": true}, '
            '"executable": "/tmp/foo-test"}\n'
        )
        calls = {"n": 0}

        def _fake_run(*a, **kw):
            calls["n"] += 1
            if calls["n"] == 1:
                return Ok(_FakeCompletedProcess(stdout=binary_json, returncode=0))
            raise FileNotFoundError()

        monkeypatch.setattr(native_mod, "guarded_subprocess_run", _fake_run)
        result = native_mod._run_cargo_valgrind(tmp_path)
        assert result is not None
        assert not result.passed

    def test_run_kill_switch_disabled(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests tests/unit/test_check_native_cargo_runners.py::TestRunCargoValgrindRealPaths.test_run_kill_switch_disabled  # noqa: E501
        binary_json = (
            '{"reason": "compiler-artifact", "profile": {"test": true}, '
            '"executable": "/tmp/foo-test"}\n'
        )
        calls = {"n": 0}

        def _fake_run(*a, **kw):
            calls["n"] += 1
            if calls["n"] == 1:
                return Ok(_FakeCompletedProcess(stdout=binary_json, returncode=0))
            return Err(ProcessGuardError.ExecDisabled)

        monkeypatch.setattr(native_mod, "guarded_subprocess_run", _fake_run)
        result = native_mod._run_cargo_valgrind(tmp_path)
        assert result is not None
        assert not result.passed
