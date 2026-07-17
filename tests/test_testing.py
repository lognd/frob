"""Tests for frob.testing -- touched-set test selection and execution (docs/modules/testing.md)."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

from frob.gitio import Diff, Hunk, ProcResult, working_diff
from frob.graph import build_graph
from frob.testing import (
    RunnerSpec,
    SelectConfig,
    TestingError,
    load_runners,
    run_selected,
    select_tests,
)
from frob.testing._select import ALL_SENTINEL, extension_language


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text))
    return path


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    )


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "checkout", "-q", "-b", "main")


def _commit(root: Path, message: str) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)


class TestSelect:
    def test_direct_hit(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_select.py::select_tests
        _write(
            tmp_path,
            "src/foo.py",
            """
            def widget() -> int:
                return 1
            """,
        )
        _write(
            tmp_path,
            "tests/test_foo.py",
            """
            def test_widget() -> None:
                # frob:tests src/foo.py::widget
                pass
            """,
        )
        snapshot = build_graph(tmp_path, tmp_path / ".frob" / "cache.db").danger_ok
        diff = Diff(base="deadbeef", hunks=(Hunk(file="src/foo.py", span=(1, 2)),))
        report = select_tests(snapshot, diff, SelectConfig())
        assert "src/foo.py::widget" in report.touched
        assert "tests/test_foo.py::test_widget" in report.selected["python"]

    def test_class_level_target(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "src/foo.py",
            """
            class Widget:
                def render(self) -> int:
                    return 1
            """,
        )
        _write(
            tmp_path,
            "tests/test_foo.py",
            """
            def test_widget() -> None:
                # frob:tests src/foo.py::Widget
                pass
            """,
        )
        snapshot = build_graph(tmp_path, tmp_path / ".frob" / "cache.db").danger_ok
        render = next(
            s for s in snapshot.symbols.values() if s.id.qualname == "Widget.render"
        )
        diff = Diff(base="deadbeef", hunks=(Hunk(file="src/foo.py", span=render.span),))
        report = select_tests(snapshot, diff, SelectConfig())
        assert "tests/test_foo.py::test_widget" in report.selected["python"]

    def test_file_and_package_target(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "src/pkg/foo.py",
            """
            def widget() -> int:
                return 1
            """,
        )
        _write(
            tmp_path,
            "tests/test_pkg.py",
            """
            def test_package() -> None:
                # frob:tests src/pkg kind="integration"
                pass
            """,
        )
        snapshot = build_graph(tmp_path, tmp_path / ".frob" / "cache.db").danger_ok
        diff = Diff(base="deadbeef", hunks=(Hunk(file="src/pkg/foo.py", span=(1, 2)),))
        report = select_tests(snapshot, diff, SelectConfig())
        assert "tests/test_pkg.py::test_package" in report.selected["python"]

    def test_one_hop_ripple(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "src/contract.py",
            """
            def provide() -> int:
                return 1
            """,
        )
        _write(
            tmp_path,
            "src/consumer.py",
            """
            def use() -> int:
                # frob:uses-contract src/contract.py::provide
                return 1
            """,
        )
        _write(
            tmp_path,
            "tests/test_consumer.py",
            """
            def test_use() -> None:
                # frob:tests src/consumer.py::use
                pass
            """,
        )
        snapshot = build_graph(tmp_path, tmp_path / ".frob" / "cache.db").danger_ok
        diff = Diff(base="deadbeef", hunks=(Hunk(file="src/contract.py", span=(1, 2)),))
        report = select_tests(snapshot, diff, SelectConfig())
        assert "src/consumer.py::use" in report.ripple
        assert "tests/test_consumer.py::test_use" in report.selected["python"]

    def test_touched_test_file_self_selects(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "tests/test_lonely.py",
            """
            def test_lonely() -> None:
                pass
            """,
        )
        snapshot = build_graph(tmp_path, tmp_path / ".frob" / "cache.db").danger_ok
        diff = Diff(
            base="deadbeef", hunks=(Hunk(file="tests/test_lonely.py", span=(1, 2)),)
        )
        report = select_tests(snapshot, diff, SelectConfig())
        assert "tests/test_lonely.py" in report.selected["python"]
        assert not report.unbound

    def test_unbound_fallback_package(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "src/pkg/orphan.py",
            """
            def orphan() -> int:
                return 1
            """,
        )
        snapshot = build_graph(tmp_path, tmp_path / ".frob" / "cache.db").danger_ok
        diff = Diff(
            base="deadbeef", hunks=(Hunk(file="src/pkg/orphan.py", span=(1, 2)),)
        )
        report = select_tests(snapshot, diff, SelectConfig(fallback="package"))
        assert "src/pkg/orphan.py" in report.unbound
        assert "src/pkg" in report.selected["python"]

    def test_unbound_fallback_suite(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "src/pkg/orphan.py",
            """
            def orphan() -> int:
                return 1
            """,
        )
        snapshot = build_graph(tmp_path, tmp_path / ".frob" / "cache.db").danger_ok
        diff = Diff(
            base="deadbeef", hunks=(Hunk(file="src/pkg/orphan.py", span=(1, 2)),)
        )
        report = select_tests(snapshot, diff, SelectConfig(fallback="suite"))
        assert ALL_SENTINEL in report.selected["python"]

    def test_unbound_fallback_warn(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "src/pkg/orphan.py",
            """
            def orphan() -> int:
                return 1
            """,
        )
        snapshot = build_graph(tmp_path, tmp_path / ".frob" / "cache.db").danger_ok
        diff = Diff(
            base="deadbeef", hunks=(Hunk(file="src/pkg/orphan.py", span=(1, 2)),)
        )
        report = select_tests(snapshot, diff, SelectConfig(fallback="warn"))
        assert "src/pkg/orphan.py" in report.unbound
        assert report.selected == {}


class TestExtensionLanguage:
    def test_known_and_unknown(self) -> None:
        # frob:tests src/frob/testing/_select.py::extension_language
        assert extension_language("a/b.py") == "python"
        assert extension_language("a/b.rs") == "rust"
        assert extension_language("a/b.unknown") is None


class TestRunners:
    def _spec(self, placeholder: str, **kwargs) -> RunnerSpec:
        return RunnerSpec(
            language="python",
            command=("pytest", placeholder),
            all_command=("pytest",),
            **kwargs,
        )

    def test_placeholder_ids(self, tmp_path: Path) -> None:
        from frob.testing._runners import _render_command

        spec = self._spec("{ids}")
        argv = _render_command(spec, ("tests/test_foo.py::Widget.render",))
        assert argv == ("pytest", "tests/test_foo.py::Widget::render")

    def test_placeholder_files(self) -> None:
        from frob.testing._runners import _render_command

        spec = self._spec("{files}")
        argv = _render_command(spec, ("tests/test_foo.py", "tests/test_bar.py"))
        assert argv == ("pytest", "tests/test_foo.py", "tests/test_bar.py")

    def test_placeholder_filters(self) -> None:
        from frob.testing._runners import _render_command

        spec = self._spec("{filters}")
        argv = _render_command(spec, ("foo", "bar"))
        assert argv == ("pytest", "foo bar")

    def test_placeholder_regex(self) -> None:
        from frob.testing._runners import _render_command

        spec = self._spec("{regex}")
        argv = _render_command(spec, ("foo", "bar"))
        assert argv == ("pytest", "foo|bar")

    def test_no_runner_error(self, tmp_path: Path) -> None:
        from frob.testing._models import SelectionReport

        selection = SelectionReport(
            touched=(),
            selected={"python": ("x",)},
            ripple=(),
            unbound=(),
            fallback="package",
        )
        result = run_selected(selection, (), tmp_path)
        assert result.is_err
        assert result.danger_err == TestingError.NoRunner

    def test_bad_runner_spec_zero_placeholders(self, tmp_path: Path) -> None:
        toml_text = """
        [[test.runner]]
        language = "python"
        command = ["pytest"]
        all_command = ["pytest"]
        """
        (tmp_path / "frob.toml").write_text(textwrap.dedent(toml_text))
        result = load_runners(tmp_path)
        assert result.is_err
        assert result.danger_err == TestingError.BadRunnerSpec

    def test_bad_runner_spec_two_placeholders(self, tmp_path: Path) -> None:
        toml_text = """
        [[test.runner]]
        language = "python"
        command = ["pytest", "{ids}", "{files}"]
        all_command = ["pytest"]
        """
        (tmp_path / "frob.toml").write_text(textwrap.dedent(toml_text))
        result = load_runners(tmp_path)
        assert result.is_err
        assert result.danger_err == TestingError.BadRunnerSpec

    def test_missing_frob_toml_is_ok_empty(self, tmp_path: Path) -> None:
        result = load_runners(tmp_path)
        assert result.is_ok
        assert result.danger_ok == ()

    def test_valid_runner_loaded(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_runners.py::load_runners
        toml_text = """
        [[test.runner]]
        language = "python"
        command = ["pytest", "-q", "{ids}"]
        all_command = ["pytest", "-q"]
        cwd = "."
        """
        (tmp_path / "frob.toml").write_text(textwrap.dedent(toml_text))
        result = load_runners(tmp_path)
        assert result.is_ok
        specs = result.danger_ok
        assert len(specs) == 1
        assert specs[0].language == "python"

    def test_exit_code_is_data(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_runners.py::run_selected
        from frob.testing._models import SelectionReport

        script = tmp_path / "fail.py"
        script.write_text("import sys\nsys.exit(1)\n")
        spec = RunnerSpec(
            language="python",
            command=(
                sys.executable,
                str(script),
                "{files}",
            ),
            all_command=(
                sys.executable,
                str(script),
            ),
        )
        selection = SelectionReport(
            touched=(),
            selected={"python": ("dummy",)},
            ripple=(),
            unbound=(),
            fallback="package",
        )
        result = run_selected(selection, (spec,), tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert report.ok is False
        assert report.outcomes[0].exit_code == 1

    def test_spawn_failed_nonexistent_binary(self, tmp_path: Path) -> None:
        from frob.testing._models import SelectionReport

        spec = RunnerSpec(
            language="python",
            command=(
                "/no/such/binary",
                "{files}",
            ),
            all_command=("/no/such/binary",),
        )
        selection = SelectionReport(
            touched=(),
            selected={"python": ("dummy",)},
            ripple=(),
            unbound=(),
            fallback="package",
        )
        result = run_selected(selection, (spec,), tmp_path)
        assert result.is_err
        assert result.danger_err == TestingError.SpawnFailed

    def test_spawn_failed_timeout(self, tmp_path: Path) -> None:
        from frob.testing._models import SelectionReport

        script = tmp_path / "sleepy.py"
        script.write_text("import time\ntime.sleep(5)\n")
        spec = RunnerSpec(
            language="python",
            command=(
                sys.executable,
                str(script),
                "{files}",
            ),
            all_command=(
                sys.executable,
                str(script),
            ),
            timeout_s=0.5,
        )
        selection = SelectionReport(
            touched=(),
            selected={"python": ("dummy",)},
            ripple=(),
            unbound=(),
            fallback="package",
        )
        result = run_selected(selection, (spec,), tmp_path)
        assert result.is_err
        assert result.danger_err == TestingError.SpawnFailed


class TestWorktree:
    def test_select_and_run_in_linked_worktree(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _init_repo(repo)
        _write(
            repo,
            "src/foo.py",
            """
            def widget() -> int:
                return 1
            """,
        )
        _write(
            repo,
            "tests/test_foo.py",
            """
            def test_widget() -> None:
                # frob:tests src/foo.py::widget
                assert True
            """,
        )
        _commit(repo, "init")

        wt = tmp_path / "wt"
        _git(repo, "worktree", "add", "-b", "feature", str(wt))

        _write(
            wt,
            "src/foo.py",
            """
            def widget() -> int:
                return 2
            """,
        )
        _commit(wt, "change widget")

        snapshot = build_graph(wt, wt / ".frob" / "cache.db").danger_ok
        diff = working_diff(wt, "main").danger_ok
        report = select_tests(snapshot, diff, SelectConfig())
        assert "tests/test_foo.py::test_widget" in report.selected["python"]


class TestCollectPythonTests:
    def test_parses_node_ids_and_caches_on_content_hash(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_python_tests
        from typani import Ok

        import frob.testing._collect as collect_mod

        _write(
            tmp_path,
            "tests/test_thing.py",
            """
            def test_a() -> None:
                assert True

            def test_b() -> None:
                assert True
            """,
        )

        calls: list[tuple] = []

        def fake_run_argv(argv, *, cwd=None, timeout_s=300.0):
            calls.append(tuple(argv))
            stdout = "tests/test_thing.py::test_a\ntests/test_thing.py::test_b\n"
            return Ok(
                ProcResult(argv=tuple(argv), returncode=0, stdout=stdout, stderr="")
            )

        monkeypatch.setattr(collect_mod, "run_argv", fake_run_argv)

        result = collect_mod.collect_python_tests(tmp_path)
        assert result.is_ok
        node_ids = result.danger_ok.node_ids
        assert node_ids == frozenset(
            {"tests/test_thing.py::test_a", "tests/test_thing.py::test_b"}
        )
        assert len(calls) == 1
        cache_path = tmp_path / ".frob" / "pytest-collect.json"
        assert cache_path.exists()

        # Second call with unchanged test files must be a cache hit: no
        # second spawn, same node ids -- the whole point of content-hash
        # keyed caching.
        result2 = collect_mod.collect_python_tests(tmp_path)
        assert result2.is_ok
        assert result2.danger_ok.node_ids == node_ids
        assert len(calls) == 1
