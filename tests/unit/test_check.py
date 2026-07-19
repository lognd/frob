"""Direct (non-CLI) unit tests for frob.check's public functions and CheckResult."""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Callable

from frob.check import (
    CheckResult,
    _collect_results,
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


class TestRunGatesQueueFailure:
    """T-0102: a malformed ticket queue must fail check loudly, not vanish."""

    def test_malformed_tickets_md_is_hard_error_not_silent_skip(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_gates kind="unit"
        from frob.check._python import _run_gates

        # Deliberately malformed: a `## T-0001` marker with no ```yaml
        # frontmatter fence at all -- exactly the class of hand-edit that
        # made load_queue fail during the T-0067/68 review.
        (tmp_path / "tickets.md").write_text(
            "# Tickets\n\n<!-- ticket:T-0001 -->\nnot even close to yaml\n"
        )
        result = _run_gates(tmp_path)
        assert result.tool == "gates"
        assert result.exit_code != 0, (
            "a failed ticket queue load must fail the gates stage, "
            "never exit 0 with gates silently skipped"
        )
        assert "skipped" not in result.summary
        assert any(d.severity == "error" for d in result.diagnostics)


class TestRunGatesDelta:
    """T-0095: --delta filters to violations new since .frob/baseline."""

    def test_no_baseline_falls_back_to_full_set_with_warning(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_gates kind="unit"
        from frob.check._python import _run_gates

        (tmp_path / "tickets.md").write_text("# Tickets\n")
        result = _run_gates(tmp_path, delta=True)
        assert result.tool == "gates"
        assert any("no baseline found" in d.message for d in result.diagnostics)

    def test_stale_baseline_falls_back_to_full_set_with_warning(
        self, tmp_path: Path
    ) -> None:
        from frob.check._python import _run_gates
        from frob.gates import Severity, Violation, stamp_baseline

        (tmp_path / "tickets.md").write_text("# Tickets\n")
        (tmp_path / "a.py").write_text("x = 1\n")
        stamp_baseline(
            tmp_path,
            (
                Violation(
                    rule="R1", severity=Severity.WARN, file="a.py", line=1, message="m"
                ),
            ),
        )
        (tmp_path / "a.py").write_text("x = 2\n")
        result = _run_gates(tmp_path, delta=True)
        assert any("stale" in d.message for d in result.diagnostics)


class TestSummarySeverityHonesty:
    """T-0228: a passing gate must never render its warn-class findings as a
    bare, alarming 'violation(s)' count -- every summary line splits into
    errors/warnings (and waived, for gates)."""

    def test_warn_only_gate_summary_splits_errors_and_warnings(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_gates kind="unit"
        from typani import Ok

        from frob.check._python import _run_gates
        from frob.gates import GateReport, GateStats, Severity, Violation

        report = GateReport(
            violations=(
                Violation(
                    rule="R1",
                    severity=Severity.WARN,
                    file="a.py",
                    line=1,
                    message="warn finding",
                ),
            ),
            waived=(),
            stats=GateStats(),
        )
        monkeypatch.setattr(
            "frob.gates.run_gates",
            lambda cfg: Ok(report),  # noqa: ARG005
        )
        (tmp_path / "tickets.md").write_text("# Tickets\n")
        result = _run_gates(tmp_path)

        assert result.exit_code == 0, "warn-only findings must not fail the stage"
        assert "violation" not in result.summary, (
            "warn-class findings on a passing gate must never be labeled "
            f"'violation(s)': got {result.summary!r}"
        )
        assert "1 warning" in result.summary
        assert "0 error" in result.summary
        assert "0 waived" in result.summary

    def test_cycle_summary_splits_by_severity(self) -> None:
        # frob:tests src/frob/check/_python.py::_run_cycle kind="unit"
        from frob.check._python import _severity_counts_summary
        from frob.process.parsers.common import Diagnostic

        diags = [Diagnostic(severity="warning", message="import cycle: a -> b -> c")]
        summary = _severity_counts_summary(diags, no_issues="no cycles")

        assert "violation" not in summary
        assert "found" not in summary, (
            "a bare 'N cycle(s) found' phrasing reads as alarming even when "
            "the finding is only warn-class"
        )
        assert summary == "1 warning"


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


class TestCollectResultsLogLevelRace:
    """T-0122: concurrent check tasks racing the shared stdout log handler
    must never leave it stuck, or `run_check`'s caller silently loses its
    final summary log with no exception and exit code 0 (the vacuous-pass
    class T-0102 targets)."""

    def test_racing_tasks_restore_original_stdout_handler_level(self) -> None:
        # frob:tests src/frob/check/__init__.py::_collect_results kind="unit"
        # Mirrors the real bug: frob.arch.analyze_project and
        # frob.dup.find_duplicates each save/restore the shared root
        # logger's stdout handler level around their work (to keep
        # frob.lang's per-parse INFO logs off stdout). Two such
        # save/restore blocks racing on DIFFERENT threads, with staggered
        # timing, can interleave so the LAST one to exit restores a level
        # that was already stale -- leaving the handler stuck. This
        # reproduces that interleaving directly against `_collect_results`
        # (no need for the real, slow arch/dup analyses).
        root_logger = logging.getLogger()
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        root_logger.addHandler(handler)
        try:

            def racy_quiet(delay_before: float, delay_after: float):
                def _task() -> None:
                    saved = handler.level
                    handler.setLevel(logging.WARNING)
                    time.sleep(delay_before)
                    time.sleep(delay_after)
                    handler.setLevel(saved)

                return _task

            # Task A enters first and exits LAST (long inner sleep) --
            # task B enters second (sees A's WARNING as its "saved" level)
            # and exits FIRST. B's restore is a no-op (WARNING->WARNING);
            # A's restore correctly puts DEBUG back... UNLESS B starts
            # after A already flipped the level, which is exactly what
            # the stagger below forces, leaving the classic stuck case
            # when three or more overlap. Assert on the OUTCOME, not the
            # interleaving mechanics: after _collect_results returns, the
            # level must equal what it was before the batch ran no matter
            # how the tasks raced.
            tasks: list[Callable[[], ToolResult | list[ToolResult] | None]] = [
                lambda: (racy_quiet(0.05, 0.0)(), None)[1],
                lambda: (racy_quiet(0.0, 0.05)(), None)[1],
                lambda: (racy_quiet(0.02, 0.02)(), None)[1],
            ]
            before = handler.level
            _collect_results(tasks)
            assert handler.level == before, (
                "_collect_results must restore the stdout handler level "
                "after racing tasks, or the caller's own summary log can "
                "be silently swallowed"
            )
        finally:
            root_logger.removeHandler(handler)

    def test_all_none_tasks_still_restore_level(self) -> None:
        # frob:tests src/frob/check/__init__.py::_collect_results kind="unit"
        root_logger = logging.getLogger()
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        root_logger.addHandler(handler)
        try:

            def flip_and_leave_stuck() -> None:
                handler.setLevel(logging.WARNING)

            before = handler.level
            _collect_results([lambda: (flip_and_leave_stuck(), None)[1]])
            assert handler.level == before
        finally:
            root_logger.removeHandler(handler)


class TestCheckBuildsGraphOnce:
    """T-0122: `frob check` must build the obligation graph exactly once
    per invocation, never once per stage that happens to touch it."""

    def test_run_check_calls_build_graph_exactly_once(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::run_check kind="unit"
        import frob.gates as gates_mod

        (tmp_path / "tickets.md").write_text("# Tickets\n")
        calls: list[int] = []
        real_build_graph = gates_mod.build_graph

        def counting_build_graph(*args, **kwargs):
            calls.append(1)
            return real_build_graph(*args, **kwargs)

        monkeypatch.setattr(gates_mod, "build_graph", counting_build_graph)

        run_check(tmp_path, only=frozenset({"gates", "arch", "dup"}))

        assert len(calls) == 1, (
            f"build_graph called {len(calls)} times in one frob check run "
            "(expected exactly 1) -- a stage is rebuilding the graph "
            "instead of reusing the one build"
        )
