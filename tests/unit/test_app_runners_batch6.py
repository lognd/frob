"""Direct-call coverage for batch-6 app/*_runner.py CLI entry points (T-0160).

Same rationale as `test_app_runners.py`/`test_app_runners_batch5.py`:
CLI-subprocess tests don't attribute coverage back to the running process,
so these tests call each runner's `run(cfg)` directly against a hand-built
`AppConfig`, exercising both success and error branches. Modules covered
this batch: graph_runner.py, perf_runner.py, check_runner.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typani import Err, Ok

from frob.app.check_runner import run as check_run
from frob.app.config import AppConfig
from frob.app.graph_runner import run as graph_run
from frob.app.perf_runner import run as perf_run
from frob.check import CheckResult
from frob.process.parsers.common import ToolResult


# frob:waive DUP001 reason="parallel App runner batch tests: independent \
# per-command cases sharing an arrange-act scaffold across the batch test \
# files; extracting would obscure per-case intent"
def _make_py_project(tmp_path: Path) -> Path:
    """Create a tiny single-file Python project fixture under tmp_path."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "mod.py").write_text(
        "def hello():\n    '''Say hi.'''\n    return 'hi'\n"
    )
    return tmp_path


def _make_workload_script(tmp_path: Path, *, exit_code: int | None = None) -> str:
    """A tiny `workload.py` script `profile_command` can spawn directly
    (`_harness.py` only understands a script path or `-m module`, not
    `python -c ...`) -- optionally exiting with `exit_code`."""
    body = "total = 0\nfor i in range(100):\n    total += i\n"
    if exit_code is not None:
        body += f"import sys\nsys.exit({exit_code})\n"
    (tmp_path / "workload.py").write_text(body)
    return "workload.py"


class TestGraphRunner:
    """`frob graph build|query|why`."""

    def test_unknown_command_exits_1(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(graph_command="bogus", graph_path=tmp_path)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            graph_run(cfg)
        assert exc.value.code == 1
        assert "usage: frob graph" in caplog.text

    def test_build_success_logs_stats(self, tmp_path: Path, caplog) -> None:
        _make_py_project(tmp_path)
        cfg = AppConfig(graph_command="build", graph_path=tmp_path)
        with caplog.at_level("INFO"):
            graph_run(cfg)
        assert "graph build:" in caplog.text

    def test_query_requires_ref(self, tmp_path: Path) -> None:
        cfg = AppConfig(graph_command="query", graph_path=tmp_path)
        with pytest.raises(SystemExit) as exc:
            graph_run(cfg)
        assert exc.value.code == 1

    # frob:waive DUP001 reason="parallel App runner batch tests: \
    # independent per-command cases sharing an arrange-act scaffold across \
    # the batch test files; extracting would obscure per-case intent"
    def test_query_unresolvable_ref_exits_1(self, tmp_path: Path) -> None:
        _make_py_project(tmp_path)
        cfg = AppConfig(
            graph_command="query", graph_path=tmp_path, graph_ref="pkg/mod.py::ghost"
        )
        with pytest.raises(SystemExit) as exc:
            graph_run(cfg)
        assert exc.value.code == 1

    def test_query_text_mode_prints_record(self, tmp_path: Path, caplog) -> None:
        _make_py_project(tmp_path)
        cfg = AppConfig(
            graph_command="query", graph_path=tmp_path, graph_ref="pkg/mod.py::hello"
        )
        with caplog.at_level("INFO"):
            graph_run(cfg)
        assert "kind=" in caplog.text

    # frob:waive DUP001 reason="parallel App runner batch tests: \
    # independent per-command cases sharing an arrange-act scaffold across \
    # the batch test files; extracting would obscure per-case intent"
    def test_query_json_mode_prints_json(self, tmp_path: Path, caplog) -> None:
        _make_py_project(tmp_path)
        cfg = AppConfig(
            graph_command="query",
            graph_path=tmp_path,
            graph_ref="pkg/mod.py::hello",
            graph_json=True,
        )
        with caplog.at_level("INFO"):
            graph_run(cfg)
        assert '"ref":' in caplog.text

    def test_why_requires_ref(self, tmp_path: Path) -> None:
        cfg = AppConfig(graph_command="why", graph_path=tmp_path)
        with pytest.raises(SystemExit) as exc:
            graph_run(cfg)
        assert exc.value.code == 1

    # frob:waive DUP001 reason="parallel App runner batch tests: \
    # independent per-command cases sharing an arrange-act scaffold across \
    # the batch test files; extracting would obscure per-case intent"
    def test_why_unresolvable_ref_exits_1(self, tmp_path: Path) -> None:
        _make_py_project(tmp_path)
        cfg = AppConfig(
            graph_command="why", graph_path=tmp_path, graph_ref="pkg/mod.py::ghost"
        )
        with pytest.raises(SystemExit) as exc:
            graph_run(cfg)
        assert exc.value.code == 1

    def test_why_text_mode_not_acked(self, tmp_path: Path, caplog) -> None:
        _make_py_project(tmp_path)
        cfg = AppConfig(
            graph_command="why", graph_path=tmp_path, graph_ref="pkg/mod.py::hello"
        )
        with caplog.at_level("INFO"):
            graph_run(cfg)
        assert "why: pkg/mod.py::hello" in caplog.text
        assert "not acked" in caplog.text

    # frob:waive DUP001 reason="parallel App runner batch tests: \
    # independent per-command cases sharing an arrange-act scaffold across \
    # the batch test files; extracting would obscure per-case intent"
    def test_why_json_mode_prints_json(self, tmp_path: Path, caplog) -> None:
        _make_py_project(tmp_path)
        cfg = AppConfig(
            graph_command="why",
            graph_path=tmp_path,
            graph_ref="pkg/mod.py::hello",
            graph_json=True,
        )
        with caplog.at_level("INFO"):
            graph_run(cfg)
        assert '"ref":' in caplog.text

    def test_build_failure_exits_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import frob.graph as graph_mod
        from frob.graph import GraphError

        monkeypatch.setattr(
            graph_mod, "build_graph", lambda root, cache: Err(GraphError.CacheStale)
        )
        cfg = AppConfig(graph_command="build", graph_path=tmp_path)
        with pytest.raises(SystemExit) as exc:
            graph_run(cfg)
        assert exc.value.code == 1

    # frob:waive DUP001 reason="parallel App runner batch tests: \
    # independent per-command cases sharing an arrange-act scaffold across \
    # the batch test files; extracting would obscure per-case intent"
    def test_query_snapshot_unavailable_exits_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import frob.graph as graph_mod
        from frob.graph import GraphError

        monkeypatch.setattr(
            graph_mod, "load_graph", lambda cache: Err(GraphError.CacheStale)
        )
        monkeypatch.setattr(
            graph_mod, "build_graph", lambda root, cache: Err(GraphError.CacheStale)
        )
        cfg = AppConfig(graph_command="query", graph_path=tmp_path, graph_ref="ghost")
        with pytest.raises(SystemExit) as exc:
            graph_run(cfg)
        assert exc.value.code == 1

    def test_query_with_edges_renders_both_directions(
        self, tmp_path: Path, caplog
    ) -> None:
        (tmp_path / "pkg2").mkdir()
        (tmp_path / "pkg2" / "__init__.py").write_text("")
        (tmp_path / "pkg2" / "mod2.py").write_text(
            "def inner():\n    '''Inner.'''\n    return 1\n\n\n"
            "def outer():\n    '''Outer.'''\n    return inner()\n"
        )
        cfg = AppConfig(
            graph_command="query",
            graph_path=tmp_path,
            graph_ref="pkg2/mod2.py::outer",
        )
        with caplog.at_level("INFO"):
            graph_run(cfg)
        assert "edges from:" in caplog.text
        assert "edges to:" in caplog.text

    def test_why_lock_load_failure_exits_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import frob.graph.lock as lock_mod
        from frob.graph import GraphError

        monkeypatch.setattr(
            lock_mod, "load_lock", lambda path: Err(GraphError.CacheStale)
        )
        _make_py_project(tmp_path)
        cfg = AppConfig(
            graph_command="why", graph_path=tmp_path, graph_ref="pkg/mod.py::hello"
        )
        with pytest.raises(SystemExit) as exc:
            graph_run(cfg)
        assert exc.value.code == 1

    # frob:waive DUP001 reason="parallel App runner batch tests: \
    # independent per-command cases sharing an arrange-act scaffold across \
    # the batch test files; extracting would obscure per-case intent"
    def test_why_snapshot_unavailable_exits_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import frob.graph as graph_mod
        from frob.graph import GraphError

        monkeypatch.setattr(
            graph_mod, "load_graph", lambda cache: Err(GraphError.CacheStale)
        )
        monkeypatch.setattr(
            graph_mod, "build_graph", lambda root, cache: Err(GraphError.CacheStale)
        )
        cfg = AppConfig(graph_command="why", graph_path=tmp_path, graph_ref="ghost")
        with pytest.raises(SystemExit) as exc:
            graph_run(cfg)
        assert exc.value.code == 1

    def test_why_acked_stale_dangling_render_lines(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        import frob.app.graph_runner as graph_runner_mod

        class _FakeEntry:
            facet = "sig"
            digest = "abc123def456"
            ref = "pkg/mod.py::hello"

        class _FakeStale:
            entry = _FakeEntry()
            current = "def456abc123"
            dependents = ("pkg/mod.py::other",)

        class _FakeEdge:
            src = "pkg/mod.py::hello"
            target = "pkg/mod.py::hello"

        class _FakeDangling:
            edge = _FakeEdge()
            candidates = ("pkg/mod.py::hello2",)

        monkeypatch.setattr(
            graph_runner_mod,
            "_why_drift_facts",
            lambda root, snapshot, ref: (
                None,
                [_FakeEntry()],
                [_FakeStale()],
                [_FakeDangling()],
            ),
        )
        _make_py_project(tmp_path)
        cfg = AppConfig(
            graph_command="why", graph_path=tmp_path, graph_ref="pkg/mod.py::hello"
        )
        with caplog.at_level("INFO"):
            graph_run(cfg)
        assert "acked facet=sig" in caplog.text
        assert "STALE facet=sig" in caplog.text
        assert "DANGLING edge" in caplog.text


class TestPerfRunner:
    """`frob perf profile|heat`."""

    def test_unknown_command_exits_1(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(perf_command="bogus", perf_path=tmp_path)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            perf_run(cfg)
        assert exc.value.code == 1
        assert "usage: frob perf" in caplog.text

    def test_profile_requires_argv_or_tests(self, tmp_path: Path) -> None:
        cfg = AppConfig(perf_command="profile", perf_path=tmp_path, perf_argv=[])
        with pytest.raises(SystemExit) as exc:
            perf_run(cfg)
        assert exc.value.code == 1

    def test_profile_and_heat_round_trip(self, tmp_path: Path, capsys) -> None:
        script = _make_workload_script(tmp_path)
        cfg = AppConfig(
            perf_command="profile", perf_path=tmp_path, perf_argv=["--", script]
        )
        perf_run(cfg)
        profiled_out = capsys.readouterr().out
        assert "profiled" in profiled_out

        heat_cfg = AppConfig(perf_command="heat", perf_path=tmp_path)
        perf_run(heat_cfg)
        heat_out = capsys.readouterr()
        assert "unattributed" in (heat_out.out + heat_out.err)

    def test_heat_json_mode(self, tmp_path: Path, capsys) -> None:
        script = _make_workload_script(tmp_path)
        profile_cfg = AppConfig(
            perf_command="profile", perf_path=tmp_path, perf_argv=["--", script]
        )
        perf_run(profile_cfg)
        capsys.readouterr()

        heat_cfg = AppConfig(perf_command="heat", perf_path=tmp_path, perf_json=True)
        perf_run(heat_cfg)
        out = capsys.readouterr().out
        assert out.strip().startswith("{")

    def test_heat_top_and_smells(self, tmp_path: Path, capsys) -> None:
        script = _make_workload_script(tmp_path)
        profile_cfg = AppConfig(
            perf_command="profile", perf_path=tmp_path, perf_argv=["--", script]
        )
        perf_run(profile_cfg)
        capsys.readouterr()

        heat_cfg = AppConfig(
            perf_command="heat", perf_path=tmp_path, perf_top=1, perf_smells=True
        )
        perf_run(heat_cfg)
        out = capsys.readouterr()
        assert "unattributed" in (out.out + out.err)

    def test_heat_annotate_writes_gutters(self, tmp_path: Path, capsys) -> None:
        script = _make_workload_script(tmp_path)
        profile_cfg = AppConfig(
            perf_command="profile", perf_path=tmp_path, perf_argv=["--", script]
        )
        perf_run(profile_cfg)
        capsys.readouterr()

        heat_cfg = AppConfig(
            perf_command="heat",
            perf_path=tmp_path,
            perf_annotate=tmp_path / script,
        )
        perf_run(heat_cfg)
        out = capsys.readouterr().out
        assert "total = 0" in out

    def test_heat_no_artifact_exits_1(self, tmp_path: Path) -> None:
        _make_py_project(tmp_path)
        cfg = AppConfig(perf_command="heat", perf_path=tmp_path)
        with pytest.raises(SystemExit) as exc:
            perf_run(cfg)
        assert exc.value.code == 1

    def test_heat_annotate_missing_file_exits_1(self, tmp_path: Path, capsys) -> None:
        script = _make_workload_script(tmp_path)
        profile_cfg = AppConfig(
            perf_command="profile", perf_path=tmp_path, perf_argv=["--", script]
        )
        perf_run(profile_cfg)
        capsys.readouterr()

        heat_cfg = AppConfig(
            perf_command="heat",
            perf_path=tmp_path,
            perf_annotate=tmp_path / "does_not_exist.py",
        )
        with pytest.raises(SystemExit) as exc:
            perf_run(heat_cfg)
        assert exc.value.code == 1

    def test_profile_failure_propagates_workload_exit_code(
        self, tmp_path: Path, capsys
    ) -> None:
        script = _make_workload_script(tmp_path, exit_code=3)
        cfg = AppConfig(
            perf_command="profile", perf_path=tmp_path, perf_argv=["--", script]
        )
        with pytest.raises(SystemExit) as exc:
            perf_run(cfg)
        assert exc.value.code == 3

    def test_profile_command_error_exits_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import frob.perf as perf_mod
        from frob.perf import PerfError

        monkeypatch.setattr(
            perf_mod, "profile_command", lambda argv, root: Err(PerfError.SpawnFailed)
        )
        cfg = AppConfig(
            perf_command="profile",
            perf_path=tmp_path,
            perf_argv=["--", "does-not-matter"],
        )
        with pytest.raises(SystemExit) as exc:
            perf_run(cfg)
        assert exc.value.code == 1

    def test_profile_tests_flag_builds_pytest_argv(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        import frob.perf as perf_mod

        seen_argv: list[str] = []

        def _fake_profile_command(argv, root):  # noqa: ANN001, ANN202
            seen_argv.extend(argv)
            import datetime as _dt

            from frob.perf import ProfileArtifact

            return Ok(
                ProfileArtifact(
                    sha="deadbeef",
                    argv=tuple(argv),
                    created=_dt.datetime(2026, 7, 17, tzinfo=_dt.UTC),
                    total_s=0.01,
                    exit_code=0,
                )
            )

        monkeypatch.setattr(perf_mod, "profile_command", _fake_profile_command)
        cfg = AppConfig(perf_command="profile", perf_path=tmp_path, perf_tests=True)
        perf_run(cfg)
        assert seen_argv == ["-m", "pytest", "-q"]
        assert "profiled" in capsys.readouterr().out

    def test_heat_snapshot_build_failure_exits_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        script = _make_workload_script(tmp_path)
        profile_cfg = AppConfig(
            perf_command="profile", perf_path=tmp_path, perf_argv=["--", script]
        )
        perf_run(profile_cfg)

        import frob.graph as graph_mod
        from frob.graph import GraphError

        monkeypatch.setattr(
            graph_mod, "build_graph", lambda root, cache: Err(GraphError.CacheStale)
        )
        heat_cfg = AppConfig(perf_command="heat", perf_path=tmp_path)
        with pytest.raises(SystemExit) as exc:
            perf_run(heat_cfg)
        assert exc.value.code == 1

    def test_heat_annotate_unreadable_file_exits_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        script = _make_workload_script(tmp_path)
        profile_cfg = AppConfig(
            perf_command="profile", perf_path=tmp_path, perf_argv=["--", script]
        )
        perf_run(profile_cfg)

        target = tmp_path / script

        real_read_text = Path.read_text

        def _boom_read_text(self, *a, **kw):  # noqa: ANN001, ANN002, ANN003, ANN202
            if self == target:
                raise OSError("permission denied")
            return real_read_text(self, *a, **kw)

        monkeypatch.setattr(Path, "read_text", _boom_read_text)
        heat_cfg = AppConfig(
            perf_command="heat", perf_path=tmp_path, perf_annotate=target
        )
        with pytest.raises(SystemExit) as exc:
            perf_run(heat_cfg)
        assert exc.value.code == 1

    def test_heat_annotate_outside_root_uses_absolute_path(
        self, tmp_path: Path, capsys
    ) -> None:
        script = _make_workload_script(tmp_path)
        profile_cfg = AppConfig(
            perf_command="profile", perf_path=tmp_path, perf_argv=["--", script]
        )
        perf_run(profile_cfg)
        capsys.readouterr()

        outside = tmp_path.parent / f"outside-{tmp_path.name}.py"
        outside.write_text("x = 1\n")
        try:
            heat_cfg = AppConfig(
                perf_command="heat", perf_path=tmp_path, perf_annotate=outside
            )
            perf_run(heat_cfg)
            out = capsys.readouterr().out
            assert "x = 1" in out
        finally:
            outside.unlink(missing_ok=True)


def _make_check_result(errors: int = 0, warnings: int = 0) -> CheckResult:
    """A synthetic `CheckResult` with `errors` error-severity and `warnings`
    warning-severity diagnostics on a single fake tool, for check_runner
    dispatch tests that don't need a real toolchain run."""
    from frob.process.parsers.common import Diagnostic

    diagnostics = [Diagnostic(severity="error", message="e") for _ in range(errors)]
    diagnostics += [
        Diagnostic(severity="warning", message="w") for _ in range(warnings)
    ]
    return CheckResult(
        path=".",
        results=[
            ToolResult(
                tool="fake", exit_code=1 if errors else 0, diagnostics=diagnostics
            )
        ],
    )


class TestCheckRunner:
    """`frob check`: path validation, stamp modes, dispatch, and reporting."""

    def test_nonexistent_path_exits_1(self, tmp_path: Path, caplog) -> None:
        cfg = AppConfig(check_path=tmp_path / "ghost")
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            check_run(cfg)
        assert exc.value.code == 1
        assert "path does not exist" in caplog.text

    def test_stamp_coverage_mode_calls_stamp_and_returns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        import frob.gates as gates_mod

        monkeypatch.setattr(gates_mod, "stamp_coverage", lambda root: Ok(None))
        cfg = AppConfig(check_path=tmp_path, check_stamp_coverage=True)
        with caplog.at_level("INFO"):
            check_run(cfg)
        assert "coverage stamp written" in caplog.text

    def test_stamp_coverage_failure_exits_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import frob.gates as gates_mod
        from frob.gates import GateError

        monkeypatch.setattr(
            gates_mod, "stamp_coverage", lambda root: Err(GateError.QueueUnavailable)
        )
        cfg = AppConfig(check_path=tmp_path, check_stamp_coverage=True)
        with pytest.raises(SystemExit) as exc:
            check_run(cfg)
        assert exc.value.code == 1

    def test_stamp_baseline_mode_calls_stamp_and_returns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        import frob.gates as gates_mod
        from frob.gates import GateReport
        from frob.gates._models import GateStats

        monkeypatch.setattr(
            gates_mod,
            "run_gates",
            lambda cfg: Ok(GateReport(violations=(), waived=(), stats=GateStats())),
        )
        monkeypatch.setattr(gates_mod, "stamp_baseline", lambda root, v: Ok(None))
        cfg = AppConfig(check_path=tmp_path, check_stamp_baseline=True)
        with caplog.at_level("INFO"):
            check_run(cfg)
        assert "baseline stamp written" in caplog.text

    def test_stamp_baseline_gate_error_exits_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import frob.gates as gates_mod
        from frob.gates import GateError

        monkeypatch.setattr(
            gates_mod, "run_gates", lambda cfg: Err(GateError.QueueUnavailable)
        )
        cfg = AppConfig(check_path=tmp_path, check_stamp_baseline=True)
        with pytest.raises(SystemExit) as exc:
            check_run(cfg)
        assert exc.value.code == 1

    def test_auto_detected_python_stage_dispatches_and_passes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        import frob.app.check_runner as check_mod

        _make_py_project(tmp_path)
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
        monkeypatch.setattr(
            check_mod, "run_check", lambda root, **kw: _make_check_result()
        )
        cfg = AppConfig(check_path=tmp_path)
        check_run(cfg)
        out = capsys.readouterr().out
        assert out

    def test_json_mode_prints_json_and_errors_exit_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        import frob.app.check_runner as check_mod

        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
        monkeypatch.setattr(
            check_mod, "run_check", lambda root, **kw: _make_check_result(errors=1)
        )
        cfg = AppConfig(check_path=tmp_path, check_json=True)
        with pytest.raises(SystemExit) as exc:
            check_run(cfg)
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert out.strip().startswith("{")

    def test_pinned_type_warns_polyglot_and_skips_others(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        import frob.app.check_runner as check_mod

        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
        (tmp_path / "package.json").write_text("{}")
        monkeypatch.setattr(
            check_mod, "run_check", lambda root, **kw: _make_check_result()
        )
        cfg = AppConfig(check_path=tmp_path, check_type="python")
        check_run(cfg)
        out = capsys.readouterr().out
        assert "SKIPPED: typescript" in out

    # frob:waive DUP001 reason="parallel App runner batch tests: \
    # independent per-command cases sharing an arrange-act scaffold across \
    # the batch test files; extracting would obscure per-case intent"
    def test_pinned_cpp_dispatches_run_check_cpp(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        import frob.app.check_runner as check_mod

        monkeypatch.setattr(
            check_mod, "run_check_cpp", lambda root, **kw: _make_check_result()
        )
        cfg = AppConfig(check_path=tmp_path, check_type="cpp")
        check_run(cfg)
        out = capsys.readouterr().out
        assert out

    # frob:waive DUP001 reason="parallel App runner batch tests: \
    # independent per-command cases sharing an arrange-act scaffold across \
    # the batch test files; extracting would obscure per-case intent"
    def test_pinned_rust_dispatches_run_check_rust(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        import frob.app.check_runner as check_mod

        monkeypatch.setattr(
            check_mod, "run_check_rust", lambda root, **kw: _make_check_result()
        )
        cfg = AppConfig(check_path=tmp_path, check_type="rust")
        check_run(cfg)
        out = capsys.readouterr().out
        assert out

    # frob:waive DUP001 reason="parallel App runner batch tests: \
    # independent per-command cases sharing an arrange-act scaffold across \
    # the batch test files; extracting would obscure per-case intent"
    def test_pinned_typescript_dispatches_run_check_ts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        import frob.app.check_runner as check_mod

        monkeypatch.setattr(
            check_mod, "run_check_ts", lambda root, **kw: _make_check_result()
        )
        cfg = AppConfig(check_path=tmp_path, check_type="typescript")
        check_run(cfg)
        out = capsys.readouterr().out
        assert out

    def test_frob_toml_defaults_applied(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        import frob.app.check_runner as check_mod

        (tmp_path / "frob.toml").write_text(
            'check_base = "main"\n[check]\nskip = ["ruff"]\n'
        )
        monkeypatch.setattr(
            check_mod, "run_check_cpp", lambda root, **kw: _make_check_result()
        )
        cfg = AppConfig(check_path=tmp_path, check_type="cpp")
        check_run(cfg)
        out = capsys.readouterr().out
        assert out

    def test_frob_toml_unreadable_warns_and_continues(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, caplog
    ) -> None:
        import frob.app.check_runner as check_mod

        (tmp_path / "frob.toml").write_text("this is not [ valid toml\n")
        monkeypatch.setattr(
            check_mod, "run_check_cpp", lambda root, **kw: _make_check_result()
        )
        cfg = AppConfig(check_path=tmp_path, check_type="cpp")
        with caplog.at_level("WARNING"):
            check_run(cfg)
        assert "frob.toml unreadable" in caplog.text

    def test_deploy_stages_appended_when_deploy_dir_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        import frob.app.check_runner as check_mod
        import frob.deploy as deploy_mod

        (tmp_path / "deploy").mkdir()
        monkeypatch.setattr(
            check_mod, "run_check_cpp", lambda root, **kw: _make_check_result()
        )
        monkeypatch.setattr(deploy_mod, "deploy_drift_violations", lambda root: [])
        monkeypatch.setattr(
            deploy_mod, "deploy_conformance_violations", lambda root: []
        )
        cfg = AppConfig(check_path=tmp_path, check_type="cpp")
        check_run(cfg)
        out = capsys.readouterr().out
        assert "deploy-drift" in out
        assert "deploy-conformance" in out

    def test_verbose_levels_do_not_crash(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        import frob.app.check_runner as check_mod

        monkeypatch.setattr(
            check_mod, "run_check_cpp", lambda root, **kw: _make_check_result()
        )
        for verbosity in (0, 1, 2):
            cfg = AppConfig(
                check_path=tmp_path, check_type="cpp", check_verbose=verbosity
            )
            check_run(cfg)
        capsys.readouterr()
