"""Direct (non-CLI) unit tests for frob.check's public functions and CheckResult."""

# frob:waive OPAQUE001 reason="T-1038: every setattr(...) in this file is \
# monkeypatch-style test isolation (pytest fixtures reassigning a module/object \
# attribute by a name the test itself constructs) -- deliberate test infrastructure, \
# not an evasion risk over untrusted input"

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Callable

import pytest

import frob.check as check_mod
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


# frob:ticket T-0554
class TestRunCheckCpp:
    # frob:ticket T-0554
    def test_all_stages_skipped_returns_empty_result(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/__init__.py::run_check_cpp kind="unit"
        result = run_check_cpp(
            tmp_path,
            skip_build=True,
            skip_clang_tidy=True,
            skip_clang_format=True,
            skip_tests=True,
            skip_gates=True,
        )
        assert isinstance(result, CheckResult)
        assert result.path == str(tmp_path)
        assert result.results == []

    # frob:ticket T-0554
    def test_gates_stage_runs_by_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # T-0554: docs/audits/lang-check-docs.md finding 1 -- run_check_cpp
        # used to never call _run_gates, so a pure C/C++ repo's
        # COV/DOC/DRIFT/INV/DEC/TODO gates silently never executed. The real
        # `_run_gates` spawns a `ProcessPoolExecutor` internally (T-0415) --
        # too heavy/slow for a unit test -- so this stubs it to prove only
        # that `run_check_cpp` WIRES the call in by default.
        # frob:tests src/frob/check/__init__.py::run_check_cpp kind="unit"
        calls: list[Path] = []
        monkeypatch.setattr(
            check_mod,
            "_run_gates",
            lambda root, **kw: (calls.append(root), ToolResult(tool="gates"))[1],
        )
        result = run_check_cpp(
            tmp_path,
            skip_build=True,
            skip_clang_tidy=True,
            skip_clang_format=True,
            skip_tests=True,
        )
        assert calls == [tmp_path]
        assert any(r.tool == "gates" for r in result.results)


# frob:ticket T-0554
class TestRunCheckRust:
    # frob:ticket T-0554
    def test_all_stages_skipped_returns_empty_result(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/__init__.py::run_check_rust kind="unit"
        result = run_check_rust(
            tmp_path,
            skip_check=True,
            skip_clippy=True,
            skip_fmt=True,
            skip_tests=True,
            skip_gates=True,
        )
        assert isinstance(result, CheckResult)
        assert result.path == str(tmp_path)
        assert result.results == []

    # frob:ticket T-0554
    def test_gates_stage_runs_by_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # T-0554: run_check_rust used to never call _run_gates. Stubbed for
        # the same reason as run_check_cpp's equivalent test above.
        # frob:tests src/frob/check/__init__.py::run_check_rust kind="unit"
        calls: list[Path] = []
        monkeypatch.setattr(
            check_mod,
            "_run_gates",
            lambda root, **kw: (calls.append(root), ToolResult(tool="gates"))[1],
        )
        result = run_check_rust(
            tmp_path,
            skip_check=True,
            skip_clippy=True,
            skip_fmt=True,
            skip_tests=True,
        )
        assert calls == [tmp_path]
        assert any(r.tool == "gates" for r in result.results)

    # frob:ticket T-1309
    def test_check_clippy_fmt_test_stages_all_run_and_append(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::run_check_rust kind="unit"
        # Covers the branch pair (call + non-None append) for EACH of
        # `_run_cargo` (twice: "check" and "clippy"), `_run_cargo_fmt_check`,
        # and `_run_cargo_test`, none of which any prior test exercised
        # (they were only ever run with skip_*=True).
        cargo_calls: list[tuple[str, Path]] = []

        def _fake_run_cargo(subcommand: str, root: Path, **kw: object) -> ToolResult:
            cargo_calls.append((subcommand, root))
            return ToolResult(tool=f"cargo-{subcommand}")

        monkeypatch.setattr(check_mod, "_run_cargo", _fake_run_cargo)
        monkeypatch.setattr(
            check_mod,
            "_run_cargo_fmt_check",
            lambda root: ToolResult(tool="cargo-fmt"),
        )
        monkeypatch.setattr(
            check_mod,
            "_run_cargo_test",
            lambda root, **kw: ToolResult(tool="cargo-test"),
        )
        monkeypatch.setattr(
            check_mod, "_run_gates", lambda root, **kw: ToolResult(tool="gates")
        )

        result = run_check_rust(tmp_path)
        tools = {r.tool for r in result.results}
        assert cargo_calls == [("check", tmp_path), ("clippy", tmp_path)]
        assert {"cargo-check", "cargo-clippy", "cargo-fmt", "cargo-test"} <= tools


# frob:ticket T-0554
class TestRunCheckTs:
    # frob:ticket T-0554
    def test_all_stages_skipped_returns_empty_result(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/__init__.py::run_check_ts kind="unit"
        result = run_check_ts(
            tmp_path,
            skip_tsc=True,
            skip_eslint=True,
            skip_prettier=True,
            skip_tests=True,
            skip_gates=True,
        )
        assert isinstance(result, CheckResult)
        assert result.path == str(tmp_path)
        assert result.results == []

    # frob:ticket T-0554
    def test_gates_stage_runs_by_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # T-0554: run_check_ts used to never call _run_gates. Stubbed for
        # the same reason as run_check_cpp's equivalent test above.
        # frob:tests src/frob/check/__init__.py::run_check_ts kind="unit"
        calls: list[Path] = []
        monkeypatch.setattr(
            check_mod,
            "_run_gates",
            lambda root, **kw: (calls.append(root), ToolResult(tool="gates"))[1],
        )
        result = run_check_ts(
            tmp_path,
            skip_tsc=True,
            skip_eslint=True,
            skip_prettier=True,
            skip_tests=True,
        )
        assert calls == [tmp_path]
        assert any(r.tool == "gates" for r in result.results)

    # frob:ticket T-1309
    def test_tsc_eslint_prettier_vitest_stages_all_run_and_append(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::run_check_ts kind="unit"
        # Covers the branch pair (call + non-None append) for EACH of the
        # 4 non-gates task lambdas, none of which any prior test
        # exercised (they were only ever run with skip_*=True).
        monkeypatch.setattr(
            check_mod, "_run_tsc", lambda root: ToolResult(tool="tsc")
        )
        monkeypatch.setattr(
            check_mod, "_run_eslint", lambda root: ToolResult(tool="eslint")
        )
        monkeypatch.setattr(
            check_mod, "_run_prettier", lambda root: ToolResult(tool="prettier")
        )
        monkeypatch.setattr(
            check_mod, "_run_vitest", lambda root: ToolResult(tool="vitest")
        )
        monkeypatch.setattr(check_mod, "_run_gates", lambda root, **kw: None)

        result = run_check_ts(tmp_path)
        tools = {r.tool for r in result.results}
        assert {"tsc", "eslint", "prettier", "vitest"} <= tools


# frob:ticket T-0608
class TestDispatchCheckThreadsGateSelectors:
    """T-0608: `_dispatch_check_cpp/_dispatch_check_rust/_dispatch_check_ts`
    used to drop `cfg.check_skip_gates`/`check_ticket`/`check_base`/
    `check_delta` on the floor -- only `_dispatch_check_python` threaded
    them through, even though `run_check_cpp/rust/ts` (T-0554) all accept
    them. This left CLI-level `--ticket`/`--base`/`--delta`/`--skip-gates`
    scoping silently ignored for non-Python repos. These tests fail
    against the pre-fix dispatchers (which omit the four kwargs from their
    `run_check_*` calls entirely) and pass once threaded through.
    """

    # frob:tests \
    # tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors.test_cpp_dispatch\
    # _threads_selectors kind="unit"
    def test_cpp_dispatch_threads_selectors(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import frob.app.check_runner as runner_mod
        from frob.app.config import AppConfig

        captured: dict[str, object] = {}

        def _fake_run_check_cpp(root: Path, **kw: object) -> CheckResult:
            captured.update(kw)
            return CheckResult(path=str(root), results=[])

        monkeypatch.setattr(runner_mod, "run_check_cpp", _fake_run_check_cpp)
        cfg = AppConfig(
            check_path=tmp_path,
            check_type="cpp",
            check_ticket="T-9999",
            check_base="origin/main",
            check_delta=True,
            check_skip_gates=True,
        )
        runner_mod._dispatch_check_cpp(cfg, tmp_path)
        assert captured["ticket"] == "T-9999"
        assert captured["base"] == "origin/main"
        assert captured["delta"] is True
        assert captured["skip_gates"] is True

    # frob:tests \
    # tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors.test_cpp_dispatch\
    # _default_selectors_unchanged kind="unit"
    def test_cpp_dispatch_default_selectors_unchanged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import frob.app.check_runner as runner_mod
        from frob.app.config import AppConfig

        captured: dict[str, object] = {}

        def _fake_run_check_cpp(root: Path, **kw: object) -> CheckResult:
            captured.update(kw)
            return CheckResult(path=str(root), results=[])

        monkeypatch.setattr(runner_mod, "run_check_cpp", _fake_run_check_cpp)
        cfg = AppConfig(check_path=tmp_path, check_type="cpp")
        runner_mod._dispatch_check_cpp(cfg, tmp_path)
        assert captured["ticket"] is None
        assert captured["base"] is None
        assert captured["delta"] is False
        assert captured["skip_gates"] is False

    # frob:tests \
    # tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors.test_rust_dispatc\
    # h_threads_selectors kind="unit"
    def test_rust_dispatch_threads_selectors(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import frob.app.check_runner as runner_mod
        from frob.app.config import AppConfig

        captured: dict[str, object] = {}

        def _fake_run_check_rust(root: Path, **kw: object) -> CheckResult:
            captured.update(kw)
            return CheckResult(path=str(root), results=[])

        monkeypatch.setattr(runner_mod, "run_check_rust", _fake_run_check_rust)
        cfg = AppConfig(
            check_path=tmp_path,
            check_type="rust",
            check_ticket="T-5678",
            check_base="main",
            check_delta=True,
            check_skip_gates=True,
        )
        runner_mod._dispatch_check_rust(cfg, tmp_path)
        assert captured["ticket"] == "T-5678"
        assert captured["base"] == "main"
        assert captured["delta"] is True
        assert captured["skip_gates"] is True

    # frob:tests \
    # tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors.test_rust_dispatc\
    # h_default_selectors_unchanged kind="unit"
    def test_rust_dispatch_default_selectors_unchanged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import frob.app.check_runner as runner_mod
        from frob.app.config import AppConfig

        captured: dict[str, object] = {}

        def _fake_run_check_rust(root: Path, **kw: object) -> CheckResult:
            captured.update(kw)
            return CheckResult(path=str(root), results=[])

        monkeypatch.setattr(runner_mod, "run_check_rust", _fake_run_check_rust)
        cfg = AppConfig(check_path=tmp_path, check_type="rust")
        runner_mod._dispatch_check_rust(cfg, tmp_path)
        assert captured["ticket"] is None
        assert captured["base"] is None
        assert captured["delta"] is False
        assert captured["skip_gates"] is False

    # frob:tests \
    # tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors.test_ts_dispatch_\
    # threads_selectors kind="unit"
    def test_ts_dispatch_threads_selectors(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import frob.app.check_runner as runner_mod
        from frob.app.config import AppConfig

        captured: dict[str, object] = {}

        def _fake_run_check_ts(root: Path, **kw: object) -> CheckResult:
            captured.update(kw)
            return CheckResult(path=str(root), results=[])

        monkeypatch.setattr(runner_mod, "run_check_ts", _fake_run_check_ts)
        cfg = AppConfig(
            check_path=tmp_path,
            check_type="typescript",
            check_ticket="T-9012",
            check_base="upstream/main",
            check_delta=True,
            check_skip_gates=True,
        )
        runner_mod._dispatch_check_ts(cfg, tmp_path)
        assert captured["ticket"] == "T-9012"
        assert captured["base"] == "upstream/main"
        assert captured["delta"] is True
        assert captured["skip_gates"] is True

    # frob:tests \
    # tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors.test_ts_dispatch_\
    # default_selectors_unchanged kind="unit"
    def test_ts_dispatch_default_selectors_unchanged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import frob.app.check_runner as runner_mod
        from frob.app.config import AppConfig

        captured: dict[str, object] = {}

        def _fake_run_check_ts(root: Path, **kw: object) -> CheckResult:
            captured.update(kw)
            return CheckResult(path=str(root), results=[])

        monkeypatch.setattr(runner_mod, "run_check_ts", _fake_run_check_ts)
        cfg = AppConfig(check_path=tmp_path, check_type="typescript")
        runner_mod._dispatch_check_ts(cfg, tmp_path)
        assert captured["ticket"] is None
        assert captured["base"] is None
        assert captured["delta"] is False
        assert captured["skip_gates"] is False


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

    def test_package_json_alone_is_typescript(self, tmp_path: Path) -> None:
        """T-0404 finding 11: `detect_project_type` and
        `app.check_runner._detected_types` must agree on what counts as a
        TypeScript repo -- `_detected_types` only requires `package.json`,
        so this single-winner detector must not additionally demand
        `tsconfig.json`.
        """
        (tmp_path / "package.json").write_text("{}")
        assert detect_project_type(tmp_path) == "typescript"

    def test_no_sentinel_is_unknown(self, tmp_path: Path) -> None:
        assert detect_project_type(tmp_path) == "unknown"

    def test_bare_py_file_no_pyproject_is_python(self, tmp_path: Path) -> None:
        """T-0718: a root-level `.py` file with no `pyproject.toml`/
        `setup.py` must still detect as 'python', not fall through to
        'unknown' the way it did before the extension-based fallback."""
        # frob:tests src/frob/check/__init__.py::detect_project_type kind="unit"
        (tmp_path / "pkg.py").write_text("def f() -> None:\n    pass\n")
        assert detect_project_type(tmp_path) == "python"


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
        # A load failure (this test's case) always reports as the single
        # "gates" ToolResult, never the T-0420 per-family list.
        assert isinstance(result, ToolResult)
        assert result.tool == "gates"
        assert result.exit_code != 0, (
            "a failed ticket queue load must fail the gates stage, "
            "never exit 0 with gates silently skipped"
        )
        assert "skipped" not in result.summary
        assert any(d.severity == "error" for d in result.diagnostics)


# frob:ticket T-0603
class TestDerivedStateIntegrityGate:
    """T-0603: a corrupt derived artifact must fail closed BEFORE any check
    stage (gates or otherwise) is dispatched -- and an absent artifact
    (fresh clone/post-clean) must not be mistaken for corruption.

    The precheck runs once, synchronously, before the concurrent
    `ThreadPoolExecutor` batch starts (not from inside a stage that runs
    concurrently with `arch`/`dup`, which write the same caches) -- see
    `_derived_state_integrity_result`'s docstring in
    `frob.check.__init__` for the race this avoids."""

    def test_corrupt_artifact_fails_closed_before_any_stage_runs(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::run_check kind="unit"
        (tmp_path / "tickets.md").write_text("# Tickets\n")
        frob_dir = tmp_path / ".frob"
        frob_dir.mkdir()
        (frob_dir / "cache.db").write_bytes(b"not a sqlite file at all")

        def _fail_if_called(*_args: object, **_kwargs: object) -> None:
            raise AssertionError(
                "no check stage may run once a derived artifact has "
                "already failed the integrity precheck"
            )

        monkeypatch.setattr("frob.check._python._run_ruff", _fail_if_called)
        monkeypatch.setattr("frob.check._python._run_ty", _fail_if_called)
        monkeypatch.setattr("frob.check._python._run_arch", _fail_if_called)
        monkeypatch.setattr("frob.check._python._run_dup", _fail_if_called)
        monkeypatch.setattr("frob.gates.run_gates", _fail_if_called)

        check_result = run_check(tmp_path)

        assert len(check_result.results) == 1
        result = check_result.results[0]
        assert result.tool == "derived-state-integrity"
        assert result.exit_code != 0
        assert any(d.code == "DERIVED001" for d in result.diagnostics)
        assert "cache.db" in result.summary

    def test_absent_artifact_is_not_a_violation(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/__init__.py::_derived_state_integrity_result \
        # kind="unit"
        from frob.check import _derived_state_integrity_result

        # A completely fresh tree: no .frob/ directory at all, nothing to
        # be corrupt -- this must report no violation (absent != corrupt).
        assert _derived_state_integrity_result(tmp_path) is None


class TestRunGatesDelta:
    """T-0095: --delta filters to violations new since .frob/baseline."""

    def test_no_baseline_falls_back_to_full_set_with_warning(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_gates kind="unit"
        from frob.check._python import _run_gates

        (tmp_path / "tickets.md").write_text("# Tickets\n")
        # T-0420: a successful run now reports as a list of per-family
        # ToolResults plus a trailing gate-summary line, not one "gates"
        # ToolResult -- flatten diagnostics across the list to check the
        # fallback warning landed somewhere in it.
        results = _run_gates(tmp_path, delta=True)
        assert isinstance(results, list)
        assert any(r.tool == "gate-summary" for r in results)
        all_diags = [d for r in results for d in r.diagnostics]
        assert any("no baseline found" in d.message for d in all_diags)

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
        # T-0420: same list-of-ToolResults shape as the no-baseline case above.
        results = _run_gates(tmp_path, delta=True)
        assert isinstance(results, list)
        all_diags = [d for r in results for d in r.diagnostics]
        assert any("stale" in d.message for d in all_diags)


# frob:ticket T-1346
class TestRunGatesCacheWiring:
    """T-1346: `_run_gates` now defaults `run_gates`'s `use_cache` to True
    (previously T-0602 built the cache but no `frob check` call site ever
    opted in) and `no_cache=True`/`FROB_NO_GATE_CACHE` forces it back off."""

    def test_gate_cache_enabled_default_true(self) -> None:
        # frob:tests src/frob/check/_python.py::_gate_cache_enabled kind="unit"
        from frob.check._python import _gate_cache_enabled

        assert _gate_cache_enabled(False) is True

    def test_gate_cache_enabled_false_when_no_cache_true(self) -> None:
        # frob:tests src/frob/check/_python.py::_gate_cache_enabled kind="unit"
        from frob.check._python import _gate_cache_enabled

        assert _gate_cache_enabled(True) is False

    def test_gate_cache_enabled_false_when_env_var_set(self, monkeypatch) -> None:
        # frob:tests src/frob/check/_python.py::_gate_cache_enabled kind="unit"
        from frob.check._python import _gate_cache_enabled

        monkeypatch.setenv("FROB_NO_GATE_CACHE", "1")
        assert _gate_cache_enabled(False) is False

    def test_run_gates_passes_use_cache_true_by_default(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_gates kind="unit"
        from frob.check._python import _run_gates

        (tmp_path / "tickets.md").write_text("# Tickets\n")
        seen: dict[str, object] = {}

        def fake_run_gates(cfg, *, use_cache: bool = False):  # noqa: ANN001
            seen["use_cache"] = use_cache
            from typani import Ok

            from frob.gates import GateReport, GateStats

            return Ok(GateReport(violations=(), waived=(), stats=GateStats()))

        monkeypatch.setattr("frob.gates.run_gates", fake_run_gates)
        _run_gates(tmp_path)
        assert seen["use_cache"] is True

    def test_run_gates_no_cache_forces_use_cache_false(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_gates kind="unit"
        from frob.check._python import _run_gates

        (tmp_path / "tickets.md").write_text("# Tickets\n")
        seen: dict[str, object] = {}

        def fake_run_gates(cfg, *, use_cache: bool = False):  # noqa: ANN001
            seen["use_cache"] = use_cache
            from typani import Ok

            from frob.gates import GateReport, GateStats

            return Ok(GateReport(violations=(), waived=(), stats=GateStats()))

        monkeypatch.setattr("frob.gates.run_gates", fake_run_gates)
        _run_gates(tmp_path, no_cache=True)
        assert seen["use_cache"] is False


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
            lambda cfg, *, use_cache=False: Ok(report),  # noqa: ARG005
        )
        (tmp_path / "tickets.md").write_text("# Tickets\n")
        # T-0420: the overall totals now live on the trailing gate-summary
        # ToolResult, not a single "gates" result.
        results = _run_gates(tmp_path)
        assert isinstance(results, list)
        result = next(r for r in results if r.tool == "gate-summary")

        assert result.exit_code == 0, "warn-only findings must not fail the stage"
        assert "violation" not in result.summary, (
            "warn-class findings on a passing gate must never be labeled "
            f"'violation(s)': got {result.summary!r}"
        )
        assert "1 warning" in result.summary
        assert "0 error" in result.summary
        assert "0 waived" in result.summary

    def test_cycle_summary_splits_by_severity(self) -> None:
        # T-0523: this test directly imports and calls
        # _severity_counts_summary, never _run_cycle -- the frob:tests
        # binding was stale/wrong (a COV006 finding correctly caught it).
        # frob:tests src/frob/check/_python.py::_severity_counts_summary kind="unit"  # noqa: E501
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


class TestDupArchWaiverAwareSummaries:
    """T-0375: the frob-dup and frob-arch stage summaries must subtract
    findings already covered by a reasoned `frob:waive`, mirroring the
    gates stage's error/warning/waived split -- a waived group/finding
    stays listed (as a `note` diagnostic), never hidden, but no longer
    inflates the headline count."""

    _DUP_BODY = (
        "    total = 0\n"
        "    for item in items:\n"
        "        total = total + item\n"
        "        if total > 100:\n"
        "            total = 100\n"
        "    return total\n"
    )
    _WAIVER = '# frob:waive DUP001 reason="documented shared shape, T-0375 fixture"\n'

    def _dup_source(self, *, waive_foo: bool = False, waive_bar: bool = False) -> str:
        """Two functions with an identical (exact-clone) body, either
        optionally preceded by a `frob:waive` directive."""
        foo_waiver = self._WAIVER if waive_foo else ""
        bar_waiver = self._WAIVER if waive_bar else ""
        lines = [f"{foo_waiver}def foo(items):\n{self._DUP_BODY}"]
        lines.append(f"{bar_waiver}def bar(items):\n{self._DUP_BODY}")
        return "\n\n".join(lines)

    def test_dup001_waived_group_excluded_from_headline_but_listed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_dup kind="unit"
        # Full-coverage rule (T-0375 review fix): the group has exactly two
        # fragments (foo, bar) -- waiving BOTH covers the whole group.
        from frob.check._python import _run_dup

        (tmp_path / "a.py").write_text(self._dup_source(waive_foo=True, waive_bar=True))

        result = _run_dup(tmp_path)

        assert result.summary == "0 duplicate groups (1 waived)", result.summary
        waived_diags = [d for d in result.diagnostics if d.severity == "note"]
        assert len(waived_diags) == 1
        assert "waived:" in waived_diags[0].message
        assert not any(d.severity == "warning" for d in result.diagnostics)

    def test_dup001_partial_group_waiver_does_not_hide_whole_group(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_dup kind="unit"
        # T-0375 review fix: waiving only ONE fragment of a 2-fragment group
        # must NOT mark the group waived -- an "any fragment matches"
        # (rather than "every fragment matches") rule would silently treat
        # a partially-reasoned-about group as fully accounted for.
        from frob.check._python import _run_dup

        (tmp_path / "a.py").write_text(self._dup_source(waive_foo=True))

        result = _run_dup(tmp_path)

        assert result.summary == "1 duplicate group", result.summary
        assert any(d.severity == "warning" for d in result.diagnostics)
        assert not any(d.severity == "note" for d in result.diagnostics)

    def test_dup001_waiver_on_shared_symbol_does_not_hide_distinct_superset_group(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_dup kind="unit"
        # T-0375 review fix (reviewer-reproduced regression): frob.dup's
        # legacy scanner deliberately lets one symbol sit in BOTH an exact
        # group and a DISTINCT, larger renamed-superset group --
        # `_renamed_groups` only drops a renamed group when it is WHOLLY
        # covered by a single exact group (frob/dup/_legacy.py). Here foo/
        # bar form an exact group; foo/bar/baz (alpha-renamed) form a
        # separate renamed group containing the new, un-reasoned-about baz.
        # Fully waiving DUP001 on foo+bar (covering the exact group) must
        # NOT also silently exclude the renamed group -- baz's fragment is
        # not covered by any waiver, so that group must still count.
        from frob.check._python import _run_dup

        renamed_body = (
            "    result = 0\n"
            "    for value in values:\n"
            "        result = result + value\n"
            "        if result > 100:\n"
            "            result = 100\n"
            "    return result\n"
        )
        source = (
            self._dup_source(waive_foo=True, waive_bar=True)
            + "\n\n"
            + f"def baz(values):\n{renamed_body}"
        )
        (tmp_path / "a.py").write_text(source)

        result = _run_dup(tmp_path)

        assert result.summary == "1 duplicate group (1 waived)", result.summary
        codes = {(d.severity, d.code) for d in result.diagnostics}
        assert ("note", "exact") in codes, (
            "the fully-waived exact {foo,bar} group must still be listed, "
            f"not hidden: {result.diagnostics}"
        )
        assert ("warning", "renamed") in codes, (
            "the renamed {foo,bar,baz} superset group must still count "
            f"unaccounted -- baz was never waived: {result.diagnostics}"
        )

    def test_dup001_waiving_every_fragment_of_superset_group_waives_it_too(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_dup kind="unit"
        # The flip side of the above: once baz is ALSO waived, the renamed
        # superset group is fully covered and is excluded from the
        # headline too -- full coverage, not "never waivable".
        from frob.check._python import _run_dup

        renamed_body = (
            "    result = 0\n"
            "    for value in values:\n"
            "        result = result + value\n"
            "        if result > 100:\n"
            "            result = 100\n"
            "    return result\n"
        )
        source = (
            self._dup_source(waive_foo=True, waive_bar=True)
            + "\n\n"
            + f"{self._WAIVER}def baz(values):\n{renamed_body}"
        )
        (tmp_path / "a.py").write_text(source)

        result = _run_dup(tmp_path)

        assert result.summary == "0 duplicate groups (2 waived)", result.summary
        assert not any(d.severity == "warning" for d in result.diagnostics)

    def test_dup001_unwaived_group_still_counts(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/_python.py::_run_dup kind="unit"
        from frob.check._python import _run_dup

        (tmp_path / "a.py").write_text(self._dup_source())

        result = _run_dup(tmp_path)

        assert result.summary == "1 duplicate group", result.summary
        assert any(d.severity == "warning" for d in result.diagnostics)
        assert not any(d.severity == "note" for d in result.diagnostics)

    def test_dup001_waiver_above_nested_closure_covers_it_via_enclosing_method(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_dup_group_covering_waivers kind="unit"
        # T-1035: a nested closure's `frob.dup` symref is qualified by its
        # FULL enclosing chain (`TestFoo.test_a._run_new`), but a
        # `frob:waive` comment placed directly above the nested `def` binds
        # (via `frob.graph.dsl`'s enclosing-symbol fallback) to the nearest
        # OUTER tracked symbol, `TestFoo.test_a` -- one dotted segment
        # short of an exact symref match. Before the T-1035 fix this made
        # the fragment permanently unwaivable no matter where the comment
        # was placed; `_dup_symref_covered`'s ancestor-prefix walk now
        # accepts the enclosing method's waiver as covering it. Both
        # fragments' enclosing methods are waived here (full-group
        # coverage, T-0375's rule unchanged) so the group is excluded from
        # the headline but still listed as a `note`.
        nested_body = (
            "            total = 0\n"
            "            for item in items:\n"
            "                total = total + item\n"
            "                if total > 100:\n"
            "                    total = 100\n"
            "            return total\n"
        )
        source = (
            "class TestFoo:\n"
            f"    {self._WAIVER}"
            "    def test_a(self, items):\n"
            "        def _run_new():\n"
            f"{nested_body}"
            "        return _run_new()\n"
            "\n"
            f"    {self._WAIVER}"
            "    def test_b(self, items):\n"
            "        def _run_new():\n"
            f"{nested_body}"
            "        return _run_new()\n"
        )
        (tmp_path / "a.py").write_text(source)

        from frob.check._python import _run_dup

        result = _run_dup(tmp_path)

        # Two clone groups appear here: the nested `_run_new` closures
        # themselves (the T-1035 case under test), and the two enclosing
        # `test_a`/`test_b` method bodies (near-identical since each is
        # just the nested def + a return) -- both are fully covered by the
        # same two waivers, so both are excluded from the headline.
        assert result.summary == "0 duplicate groups (2 waived)", result.summary
        assert not any(d.severity == "warning" for d in result.diagnostics)
        nested_closure_note = next(
            (
                d
                for d in result.diagnostics
                if d.severity == "note" and "_run_new" in d.message
            ),
            None,
        )
        assert nested_closure_note is not None, result.diagnostics
        assert "TestFoo.test_a" in nested_closure_note.message
        assert "TestFoo.test_b" in nested_closure_note.message

    def _arch_source(self, *, waiver: str = "") -> str:
        """A long AND structurally complex function (fires ARCH001's
        long-function rule), optionally preceded by a `frob:waive`."""
        lines = [waiver] if waiver else []
        lines += [
            "def complex_long(items):",
            '    """Long and complex."""',
            "    total = 0",
        ]
        for i in range(30):
            lines.append(
                f"    try:\n        if items[{i}] and total:\n"
                "            for x in range(3):\n"
                "                if x:\n                    total += x\n"
                "    except Exception:\n        pass"
            )
        lines.append("    return total")
        return "\n".join(lines) + "\n"

    def test_arch001_waived_long_function_excluded_from_headline_but_listed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_arch kind="unit"
        from frob.check._python import _run_arch

        (tmp_path / "src").mkdir()
        waiver = '# frob:waive ARCH001 reason="justified, T-0375 fixture"\n'
        (tmp_path / "src" / "big.py").write_text(self._arch_source(waiver=waiver))

        result = _run_arch(tmp_path / "src")

        assert "0 warnings (1 waived)" in result.summary, result.summary
        waived = [
            d
            for d in result.diagnostics
            if d.code == "long-function" and d.severity == "note"
        ]
        assert len(waived) == 1
        assert "waived:" in waived[0].message
        assert not any(
            d.code == "long-function" and d.severity == "warning"
            for d in result.diagnostics
        )

    def test_arch001_unwaived_long_function_still_counts(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/_python.py::_run_arch kind="unit"
        from frob.check._python import _run_arch

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "big.py").write_text(self._arch_source())

        result = _run_arch(tmp_path / "src")

        assert "1 warning" in result.summary
        assert "waived" not in result.summary
        assert any(
            d.code == "long-function" and d.severity == "warning"
            for d in result.diagnostics
        )

    @staticmethod
    def _calibrated_source(fn_name: str = "do_work") -> str:
        """A function long enough to trip `frob.arch.analyze_project`'s bare
        30-line `max_function_lines` default but short enough to stay under
        the calibrated 60-line default (T-0373's frob.toml [arch] table),
        and structurally complex enough (>=8 branches) to pass
        `_py_is_complex`'s cyclomatic-proxy filter. Mirrors
        `tests/test_gates.py::_complex_function_source`."""
        lines = [f"def {fn_name}(cfg):", "    result = {}"]
        for i in range(8):
            lines.append(f'    if cfg.get("flag_{i}"):')
            lines.append(f'        result["k{i}"] = {i}')
        for i in range(20):
            lines.append(f'    step_{i} = cfg.get("step_{i}", "default")')
        lines.append("    return result, " + ", ".join(f"step_{i}" for i in range(20)))
        return "\n".join(lines) + "\n"

    def test_arch_stage_uses_calibrated_default_not_library_default(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_arch kind="unit"
        # T-0442: without threading load_arch_config's calibrated 60-line
        # default through, this tool-summary stage would use
        # analyze_project's bare 30-line default and flag this ~39-line
        # function -- disagreeing with ARCH001's own T-0373-fixed gate over
        # the identical source. No frob.toml present: the calibrated
        # default alone must suppress the finding.
        from frob.arch import analyze_project
        from frob.check._python import _run_arch

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "mod.py").write_text(self._calibrated_source())

        raw_result = analyze_project(tmp_path / "src")
        assert "long-function" in {s.category for s in raw_result.suggestions}, (
            "fixture must trip the library's own bare default to prove anything"
        )

        result = _run_arch(tmp_path / "src")

        assert not any(d.code == "long-function" for d in result.diagnostics), (
            result.diagnostics
        )

    def test_arch_stage_respects_explicit_frob_toml_override(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_arch kind="unit"
        # T-0442: an explicit frob.toml [arch] override (well below both the
        # library default and the calibrated default) must still surface,
        # proving _run_arch actually reads frob.toml via load_arch_config
        # rather than a hardcoded calibrated constant.
        from frob.check._python import _run_arch

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "mod.py").write_text(self._calibrated_source())
        (tmp_path / "src" / "frob.toml").write_text("[arch]\nmax_function_lines = 20\n")

        result = _run_arch(tmp_path / "src")

        assert any(d.code == "long-function" for d in result.diagnostics), (
            result.diagnostics
        )


def test_check_run_check_arch_integration(tmp_path: Path) -> None:
    # frob:tests src/frob/check kind="integration"
    # Exercises frob.check across a real analysis boundary: run_check with the
    # arch stage drives frob.arch.analyze_project over a real source tree and
    # aggregates its diagnostics into a CheckResult. A file with a deliberately
    # over-long AND structurally complex function (T-0289: a merely long-but-
    # flat body like a linear `x0 = 0; x1 = 1; ...` block no longer fires,
    # by design) must surface a frob-arch diagnostic, proving the
    # orchestration wiring reaches the analyzer and back, not a stub.
    branches = "\n".join(
        f"    if items[{i}] and total:\n        total += items[{i}]" for i in range(30)
    )
    body = f"def huge(items):\n    total = 0\n{branches}\n    return total\n"
    (tmp_path / "big.py").write_text(body)

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


class _LockSpy:
    """Test double for `frob.process._lock.derived_state_lock` (T-0859):
    records every `(root, exclusive)` acquisition and exposes `held` so a
    probe planted at a specific call site can assert whether the lock was
    actually held at that instant -- not just that it was acquired
    somewhere during the run. Used by `TestDerivedStateLockWiring` below
    to prove `run_check`/`run_check_cpp`/`run_check_rust`/`run_check_ts`
    genuinely hold the SHARED lock across both the precheck and stage
    dispatch, closing the gap `TestDerivedStateIntegrityGate` and
    `tests/unit/test_process_lock.py`'s own tests leave: the lock
    primitive being correct in isolation does not prove any `run_check*`
    entry point actually calls it, or holds it for the right span."""

    def __init__(self) -> None:
        self.calls: list[tuple[Path, bool]] = []
        self.held = False

    def __call__(self, root: Path, *, exclusive: bool) -> "_LockSpy":
        self.calls.append((root, exclusive))
        return self

    def __enter__(self) -> None:
        self.held = True

    def __exit__(self, *exc_info: object) -> None:
        self.held = False


class TestDerivedStateLockWiring:
    """T-0859: proves each `run_check*` entry point actually acquires
    `derived_state_lock` in SHARED (`exclusive=False`) mode and holds it
    across BOTH the integrity precheck and stage dispatch/execution --
    not just one or the other, and not with the wrong mode. Every test
    here plants a probe (via `_LockSpy.held`) at the exact call sites the
    T-0859 land-preflight mutation run flagged as unproven (the `with
    derived_state_lock(...)` lines and their immediately-surrounding
    precheck/dispatch statements in each of the four entry points)."""

    def test_run_check_holds_shared_lock_across_precheck_and_stages(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_check.py::TestDerivedStateLockWiring.test_run_check_holds_shared_lock_across_precheck_and_stages  # noqa: E501
        (tmp_path / "tickets.md").write_text("# Tickets\n")
        spy = _LockSpy()
        monkeypatch.setattr(check_mod, "derived_state_lock", spy)

        precheck_states: list[bool] = []

        def fake_precheck(root: Path) -> None:
            precheck_states.append(spy.held)
            return None

        monkeypatch.setattr(check_mod, "_derived_state_integrity_result", fake_precheck)

        stage_states: list[bool] = []

        def fake_collect(tasks: object) -> list[object]:
            stage_states.append(spy.held)
            return []

        monkeypatch.setattr(check_mod, "_collect_results", fake_collect)

        run_check(tmp_path, only=frozenset({"gates"}))

        assert spy.calls == [(tmp_path, False)], (
            "run_check must acquire derived_state_lock exactly once, in "
            "SHARED (exclusive=False) mode"
        )
        assert precheck_states == [True], (
            "the integrity precheck must run while the lock is held"
        )
        assert stage_states == [True], (
            "stage dispatch must run while the SAME lock acquisition is "
            "still held, not after it was released"
        )
        assert spy.held is False, "the lock must be released once the run completes"

    def test_run_check_precheck_failure_short_circuits_under_lock(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_check.py::TestDerivedStateLockWiring.test_run_check_precheck_failure_short_circuits_under_lock  # noqa: E501
        spy = _LockSpy()
        monkeypatch.setattr(check_mod, "derived_state_lock", spy)

        fake_failure = ToolResult(
            tool="derived-state-integrity",
            exit_code=1,
            diagnostics=[],
            summary="corrupt",
        )
        monkeypatch.setattr(
            check_mod, "_derived_state_integrity_result", lambda root: fake_failure
        )

        def _fail_if_called(*_args: object, **_kwargs: object) -> list[object]:
            raise AssertionError(
                "no stage may run once the precheck under the lock has failed"
            )

        monkeypatch.setattr(check_mod, "_collect_results", _fail_if_called)

        result = run_check(tmp_path)

        assert result.results == [fake_failure]
        assert spy.calls == [(tmp_path, False)]
        assert spy.held is False

    def test_run_check_cpp_holds_shared_lock_across_precheck_and_stages(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_check.py::TestDerivedStateLockWiring.test_run_check_cpp_holds_shared_lock_across_precheck_and_stages  # noqa: E501
        spy = _LockSpy()
        monkeypatch.setattr(check_mod, "derived_state_lock", spy)

        precheck_states: list[bool] = []
        monkeypatch.setattr(
            check_mod,
            "_derived_state_integrity_result",
            lambda root: precheck_states.append(spy.held) or None,
        )

        stage_states: list[bool] = []

        def fake_run_tasks_concurrently(tasks: object) -> list[object]:
            stage_states.append(spy.held)
            return []

        monkeypatch.setattr(
            check_mod, "_run_tasks_concurrently", fake_run_tasks_concurrently
        )

        run_check_cpp(
            tmp_path,
            skip_build=True,
            skip_clang_tidy=True,
            skip_clang_format=True,
            skip_tests=True,
            skip_gates=True,
        )

        assert spy.calls == [(tmp_path, False)]
        assert precheck_states == [True]
        assert stage_states == [True]
        assert spy.held is False

    def test_run_check_cpp_build_failure_skips_tests_under_held_lock(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A failed cmake build must set `skip_tests=True` for the
        post-build stage -- and both the build call and the post-build
        stage dispatch must happen while the SAME lock acquisition is
        held. Kills mutants of the `bdir = build_dir or (root /
        "build")`, `if not skip_build`, and `if r.exit_code != 0:
        skip_tests = True` lines the T-0859 land-preflight run flagged."""

        # frob:tests tests/unit/test_check.py::TestDerivedStateLockWiring.test_run_check_cpp_build_failure_skips_tests_under_held_lock  # noqa: E501
        spy = _LockSpy()
        monkeypatch.setattr(check_mod, "derived_state_lock", spy)
        monkeypatch.setattr(
            check_mod, "_derived_state_integrity_result", lambda root: None
        )

        build_states: list[bool] = []
        seen_bdir: list[Path] = []

        def fake_cmake_build(root: Path, bdir: Path) -> ToolResult:
            build_states.append(spy.held)
            seen_bdir.append(bdir)
            return ToolResult(
                tool="cmake", exit_code=1, diagnostics=[], summary="build failed"
            )

        monkeypatch.setattr(check_mod, "_run_cmake_build", fake_cmake_build)

        captured_kwargs: dict[str, object] = {}

        def fake_post_build_tasks(
            root: Path, bdir: Path, **kwargs: object
        ) -> list[object]:
            captured_kwargs.update(kwargs)
            return []

        monkeypatch.setattr(check_mod, "_cpp_post_build_tasks", fake_post_build_tasks)

        stage_states: list[bool] = []

        def fake_run_tasks_concurrently(tasks: object) -> list[object]:
            stage_states.append(spy.held)
            return []

        monkeypatch.setattr(
            check_mod, "_run_tasks_concurrently", fake_run_tasks_concurrently
        )

        result = run_check_cpp(tmp_path, skip_build=False, skip_tests=False)

        assert spy.calls == [(tmp_path, False)]
        assert build_states == [True]
        assert stage_states == [True]
        assert seen_bdir == [tmp_path / "build"]
        assert captured_kwargs["skip_tests"] is True, (
            "a failed cmake build must force the post-build tasks to skip tests"
        )
        assert result.results[0].tool == "cmake"
        assert spy.held is False

    def test_run_check_rust_holds_shared_lock_across_precheck_and_stages(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_check.py::TestDerivedStateLockWiring.test_run_check_rust_holds_shared_lock_across_precheck_and_stages  # noqa: E501
        spy = _LockSpy()
        monkeypatch.setattr(check_mod, "derived_state_lock", spy)

        precheck_states: list[bool] = []
        monkeypatch.setattr(
            check_mod,
            "_derived_state_integrity_result",
            lambda root: precheck_states.append(spy.held) or None,
        )

        stage_states: list[bool] = []

        def fake_run_gates(
            root: Path,
            *,
            ticket: str | None = None,
            base: str | None = None,
            delta: bool = False,
            no_cache: bool = False,
        ) -> ToolResult:
            stage_states.append(spy.held)
            return ToolResult(
                tool="gate-summary", exit_code=0, diagnostics=[], summary="ok"
            )

        monkeypatch.setattr(check_mod, "_run_gates", fake_run_gates)

        run_check_rust(
            tmp_path,
            skip_check=True,
            skip_clippy=True,
            skip_fmt=True,
            skip_tests=True,
            skip_gates=False,
        )

        assert spy.calls == [(tmp_path, False)]
        assert precheck_states == [True]
        assert stage_states == [True]
        assert spy.held is False

    def test_run_check_ts_holds_shared_lock_across_precheck_and_stages(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_check.py::TestDerivedStateLockWiring.test_run_check_ts_holds_shared_lock_across_precheck_and_stages  # noqa: E501
        spy = _LockSpy()
        monkeypatch.setattr(check_mod, "derived_state_lock", spy)

        precheck_states: list[bool] = []
        monkeypatch.setattr(
            check_mod,
            "_derived_state_integrity_result",
            lambda root: precheck_states.append(spy.held) or None,
        )

        stage_states: list[bool] = []

        def fake_run_gates(
            root: Path,
            *,
            ticket: str | None = None,
            base: str | None = None,
            delta: bool = False,
            no_cache: bool = False,
        ) -> ToolResult:
            stage_states.append(spy.held)
            return ToolResult(
                tool="gate-summary", exit_code=0, diagnostics=[], summary="ok"
            )

        monkeypatch.setattr(check_mod, "_run_gates", fake_run_gates)

        run_check_ts(
            tmp_path,
            skip_tsc=True,
            skip_eslint=True,
            skip_prettier=True,
            skip_tests=True,
            skip_gates=False,
        )

        assert spy.calls == [(tmp_path, False)]
        assert precheck_states == [True]
        assert stage_states == [True]
        assert spy.held is False


class TestScopeDisclosure:
    """T-1351 (the T-1293 false-close guard): a scoped `frob check`
    invocation must say so, and say what it did not cover, rather than let
    a clean-looking count be misread as "the whole package is clean"."""

    # frob:ticket T-1351

    def test_only_names_the_gate_families_it_did_not_run(self) -> None:
        # frob:tests src/frob/check/_python.py::_scope_disclosure_note kind="unit"  # noqa: E501
        from frob.check._python import _scope_disclosure_note
        from frob.gates import _ALL_GATES

        ran = frozenset({"opaque", "drift"})
        note = _scope_disclosure_note(ticket=None, gates=ran, ran=ran)
        assert note is not None
        assert "--only" in note
        # Every gate NOT in `ran` must be named -- this is exactly the
        # T-1337 incident (INV006 invisible because gate:INV never ran).
        for name in sorted(_ALL_GATES - ran):
            assert name in note, f"{name} missing from the not-run disclosure"

    def test_ticket_flag_notes_which_families_are_actually_diff_scoped(
        self,
    ) -> None:
        # frob:tests src/frob/check/_python.py::_scope_disclosure_note kind="unit"  # noqa: E501
        from frob.check._python import _scope_disclosure_note
        from frob.gates import _ALL_GATES

        note = _scope_disclosure_note(
            ticket="T-1293", gates=frozenset(), ran=_ALL_GATES
        )
        assert note is not None
        assert "T-1293" in note
        assert "REPO-WIDE" in note

    def test_full_unfiltered_run_adds_no_disclosure(self) -> None:
        # frob:tests src/frob/check/_python.py::_scope_disclosure_note kind="unit"  # noqa: E501
        from frob.check._python import _scope_disclosure_note
        from frob.gates import _ALL_GATES

        note = _scope_disclosure_note(ticket=None, gates=frozenset(), ran=_ALL_GATES)
        assert note is None
