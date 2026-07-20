"""Tests for frob.testing -- touched-set test selection and execution (docs/modules/testing.md)."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

from typani import Err, Ok

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


def _write_files(root: Path, files: dict[str, str]) -> None:
    """Write several `{rel_path: text}` fixture files under `root` in one call."""
    for rel, text in files.items():
        _write(root, rel, text)


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
        _write_files(
            tmp_path,
            {
                "src/contract.py": """
                    def provide() -> int:
                        return 1
                    """,
                "src/consumer.py": """
                    def use() -> int:
                        # frob:uses-contract src/contract.py::provide
                        return 1
                    """,
                "tests/test_consumer.py": """
                    def test_use() -> None:
                        # frob:tests src/consumer.py::use
                        pass
                    """,
            },
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

    def test_reversed_directive_never_selects_the_source_symbol(
        self, tmp_path: Path
    ) -> None:
        """T-0137 regression: a `frob:tests` directive written above the
        SOURCE symbol (naming the test as its target, reversed from every
        other fixture in this class) must never leak that source symbol
        into `selected`, even when a touched test file makes the edge's
        target look "touched" (e.g. the test file is new)."""
        _write_files(
            tmp_path,
            {
                "src/foo2.py": """
                    # frob:tests tests/test_foo2.py::test_widget2
                    def widget2() -> int:
                        return 1
                    """,
                "tests/test_foo2.py": """
                    def test_widget2() -> None:
                        pass
                    """,
            },
        )
        snapshot = build_graph(tmp_path, tmp_path / ".frob" / "cache.db").danger_ok
        test_fn = next(
            s for s in snapshot.symbols.values() if s.id.qualname == "test_widget2"
        )
        diff = Diff(
            base="deadbeef", hunks=(Hunk(file="tests/test_foo2.py", span=test_fn.span),)
        )
        selected_python = select_tests(snapshot, diff, SelectConfig()).selected.get(
            "python", ()
        )
        assert not any("src/foo2.py" in item for item in selected_python)
        assert "tests/test_foo2.py" in selected_python

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

    # frob:waive DUP001 reason="parallel test methods within \
    # test_testing.py (2 sites) sharing an arrange-act scaffold typical of \
    # exhaustive per-case coverage; extracting would obscure per-case \
    # intent"
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

    # frob:waive DUP001 reason="parallel test methods within \
    # test_testing.py (2 sites) sharing an arrange-act scaffold typical of \
    # exhaustive per-case coverage; extracting would obscure per-case \
    # intent"
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

    def test_pytest_exit_5_no_tests_collected_is_neutral_not_fail(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/testing/_runners.py::run_selected
        # frob:tests src/frob/testing/_runners.py::_is_neutral_outcome
        # T-0210: a package-fallback selection landing on a package with a
        # source edit but zero tests must degrade to the same neutral
        # outcome the empty-selection path prints, not [FAIL].
        from frob.testing._models import SelectionReport

        script = tmp_path / "no_tests.py"
        script.write_text("import sys\nsys.exit(5)\n")
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
        assert report.ok is True
        assert report.outcomes[0].exit_code == 5

    def test_package_fallback_with_zero_tests_is_ok_end_to_end(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/testing/_runners.py::run_selected
        # T-0210 regression: a real fixture package with a source edit and
        # zero tests, selected via fallback="package" and run through the
        # real `pytest` runner, must come back ok=True (pytest's genuine
        # exit 5), not ok=False.
        from frob.testing._models import SelectionReport

        pkg = tmp_path / "activities" / "git-heist"
        pkg.mkdir(parents=True)
        (pkg / "core.py").write_text("def widget() -> int:\n    return 1\n")

        spec = RunnerSpec(
            language="python",
            command=(sys.executable, "-m", "pytest", "{files}"),
            all_command=(sys.executable, "-m", "pytest"),
        )
        selection = SelectionReport(
            touched=(str(pkg / "core.py"),),
            selected={"python": (str(pkg),)},
            ripple=(),
            unbound=(str(pkg / "core.py"),),
            fallback="package",
        )
        result = run_selected(selection, (spec,), tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert report.outcomes[0].exit_code == 5
        assert report.ok is True

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


class TestNativeStrataAudit:
    """T-0242: a touched `.strata` selection runs `frob sys audit` natively,
    with no `[[test.runner]] language = "strata"` entry at all -- the
    exact zero-config gap the malmberg pilot P3 hit (`NoRunner`, then a
    dummy-`{ids}`-placeholder `BadRunnerSpec` workaround)."""

    _MODEL = """module m
node client : foreign { clearance Public; }
node api : authenticated { clearance Internal; }
node vault : trusted { clearance Secret; }
flow f_login : client -> api
boundary b_login endorse f_login : foreign -> authenticated when "jwt_verified"
"""

    def _selection(self, root: Path):  # noqa: ANN201
        from frob.testing._models import SelectionReport

        return SelectionReport(
            touched=(f"{root}/design/m.strata",),
            selected={"strata": (f"{root}/design/m.strata",)},
            ripple=(),
            unbound=(),
            fallback="package",
        )

    # frob:tests tests/test_testing.py::TestNativeStrataAudit.test_no_runner_config_needed
    def test_no_runner_config_needed(self, tmp_path: Path) -> None:
        """A `strata` selection with ZERO `[[test.runner]]` entries never
        hits `TestingError.NoRunner` -- `run_selected`'s empty `runners`
        tuple proves no per-repo config was consulted at all."""
        _write(tmp_path, "design/m.strata", self._MODEL)
        selection = self._selection(tmp_path)

        result = run_selected(selection, (), tmp_path)

        assert result.is_ok
        report = result.danger_ok
        assert len(report.outcomes) == 1
        outcome = report.outcomes[0]
        assert outcome.language == "strata"
        assert outcome.argv == ("<native>", "frob", "sys", "audit")

    # frob:tests tests/test_testing.py::TestNativeStrataAudit.test_no_models_is_neutral_pass
    def test_no_models_is_neutral_pass(self, tmp_path: Path) -> None:
        """No `.strata` files under the design dir at all -- `frob sys
        audit`'s own vacuous-but-honest "nothing to check yet" posture,
        not a fabricated failure."""
        selection = self._selection(tmp_path)

        result = run_selected(selection, (), tmp_path)

        assert result.is_ok
        report = result.danger_ok
        assert report.ok is True
        assert report.outcomes[0].exit_code == 0

    # frob:tests tests/test_testing.py::TestNativeStrataAudit.test_bad_design_file_fails
    def test_bad_design_file_fails(self, tmp_path: Path) -> None:
        """A `.strata` file that fails to parse surfaces as
        `TestingError.NativeAuditFailed`, not a spawn/timeout error --
        there is no subprocess to spawn or time out here."""
        _write(tmp_path, "design/bad.strata", "this is not valid strata {{{")
        selection = self._selection(tmp_path)

        result = run_selected(selection, (), tmp_path)

        assert result.is_err
        assert result.danger_err == TestingError.NativeAuditFailed


class TestWorktree:
    def test_select_and_run_in_linked_worktree(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _init_repo(repo)
        _write_files(
            repo,
            {
                "src/foo.py": """
                    def widget() -> int:
                        return 1
                    """,
                "tests/test_foo.py": """
                    def test_widget() -> None:
                        # frob:tests src/foo.py::widget
                        assert True
                    """,
            },
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


def _stub_collect_only(monkeypatch, collect_mod) -> list[tuple]:
    """Stub `collect_mod.run_argv` to return two fixed node ids; return the call log."""
    from typani import Ok

    calls: list[tuple] = []

    def fake_run_argv(argv, *, cwd=None, timeout_s=300.0):
        calls.append(tuple(argv))
        stdout = "tests/test_thing.py::test_a\ntests/test_thing.py::test_b\n"
        return Ok(ProcResult(argv=tuple(argv), returncode=0, stdout=stdout, stderr=""))

    monkeypatch.setattr(collect_mod, "run_argv", fake_run_argv)
    return calls


class TestCollectPythonTests:
    def test_parses_node_ids_and_caches_on_content_hash(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_python_tests
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
        calls = _stub_collect_only(monkeypatch, collect_mod)

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


class TestCollectPythonTestsNestedRunner:
    def test_nested_test_runner_cwd_is_collected_and_rerooted(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_python_tests
        # T-0317: a [[test.runner]] pointed at a nested subdir project must
        # have its node ids collected (not just run) -- the outer-tree-only
        # collection pass never visits it, so evidence bound inside it is
        # otherwise permanently unresolvable.
        import frob.testing._collect as collect_mod

        _write(
            tmp_path,
            "frob.toml",
            """
            [[test.runner]]
            language = "python"
            command = ["uv", "run", "pytest", "-q", "{ids}"]
            all_command = ["uv", "run", "pytest", "-q"]
            cwd = "."

            [[test.runner]]
            language = "python"
            command = ["uv", "run", "pytest", "-q", "{ids}"]
            all_command = ["uv", "run", "pytest", "-q"]
            cwd = "nested"
            """,
        )
        _write(
            tmp_path,
            "tests/test_outer.py",
            """
            def test_outer() -> None:
                assert True
            """,
        )
        _write(
            tmp_path,
            "nested/tests/test_inner.py",
            """
            def test_inner() -> None:
                assert True
            """,
        )

        calls: list[tuple[tuple[str, ...], Path | None]] = []

        def fake_run_argv(argv, *, cwd=None, timeout_s=300.0):
            calls.append((tuple(argv), cwd))
            if cwd == tmp_path / "nested":
                stdout = "tests/test_inner.py::test_inner\n"
            else:
                stdout = "tests/test_outer.py::test_outer\n"
            return Ok(
                ProcResult(argv=tuple(argv), returncode=0, stdout=stdout, stderr="")
            )

        monkeypatch.setattr(collect_mod, "run_argv", fake_run_argv)

        result = collect_mod.collect_python_tests(tmp_path)
        assert result.is_ok
        node_ids = result.danger_ok.node_ids
        assert node_ids == frozenset(
            {
                "tests/test_outer.py::test_outer",
                "nested/tests/test_inner.py::test_inner",
            }
        )
        # one spawn for the outer tree, one for the nested runner's own cwd
        assert len(calls) == 2
        nested_calls = [c for c in calls if c[1] == tmp_path / "nested"]
        assert len(nested_calls) == 1

    def test_missing_nested_runner_dir_degrades_to_empty_not_err(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_python_tests
        import frob.testing._collect as collect_mod

        _write(
            tmp_path,
            "frob.toml",
            """
            [[test.runner]]
            language = "python"
            command = ["uv", "run", "pytest", "-q", "{ids}"]
            all_command = ["uv", "run", "pytest", "-q"]
            cwd = "does-not-exist"
            """,
        )
        _write(
            tmp_path,
            "tests/test_outer.py",
            """
            def test_outer() -> None:
                assert True
            """,
        )
        calls = _stub_collect_only(monkeypatch, collect_mod)

        result = collect_mod.collect_python_tests(tmp_path)
        assert result.is_ok
        # only the outer-tree spawn happens; the missing nested cwd is
        # skipped rather than erroring the whole collection
        assert len(calls) == 1


class TestRustFilterPlaceholder:
    def test_to_rust_filter_strips_path_and_rejoins_dots(self) -> None:
        # frob:tests src/frob/testing/_runners.py::_to_rust_filter
        from frob.testing._runners import _to_rust_filter

        assert (
            _to_rust_filter("strata-core/src/lib.rs::tests.reachable")
            == "tests::reachable"
        )
        assert _to_rust_filter("nodots") == "nodots"

    def test_render_command_uses_rust_filter_for_rust_language(self) -> None:
        # frob:tests src/frob/testing/_runners.py::_render_command
        from frob.testing._runners import _render_command

        spec = RunnerSpec(
            language="rust",
            command=("cargo", "test", "--lib", "{filters}"),
            all_command=("cargo", "test", "--lib"),
        )
        argv = _render_command(
            spec, ("strata-core/src/lib.rs::tests.reachable_returns_witness_paths",)
        )
        assert argv == (
            "cargo",
            "test",
            "--lib",
            "tests::reachable_returns_witness_paths",
        )

    def test_python_filters_placeholder_unaffected(self) -> None:
        # {filters} for a non-rust language keeps raw items, unchanged behavior.
        from frob.testing._runners import _render_command

        spec = RunnerSpec(
            language="python", command=("pytest", "{filters}"), all_command=("pytest",)
        )
        argv = _render_command(spec, ("foo", "bar"))
        assert argv == ("pytest", "foo bar")


class TestCargoEnv:
    def test_cargo_env_ok_when_python311_and_libdir_found(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/testing/_runners.py::_cargo_env
        from typani import Ok

        import frob.testing._runners as runners_mod

        lib_dir = tmp_path / "py312-lib"
        lib_dir.mkdir()

        monkeypatch.delenv("PYO3_PYTHON", raising=False)
        monkeypatch.setattr(
            runners_mod.shutil, "which", lambda name: f"/usr/bin/{name}"
        )

        def fake_run_argv(argv, *, cwd=None, timeout_s=10.0):
            if "sys.version_info" in argv[-1]:
                return Ok(
                    ProcResult(argv=tuple(argv), returncode=0, stdout="3 12", stderr="")
                )
            return Ok(
                ProcResult(
                    argv=tuple(argv), returncode=0, stdout=f"{lib_dir}\n", stderr=""
                )
            )

        monkeypatch.setattr(runners_mod, "run_argv", fake_run_argv)
        result = runners_mod._cargo_env()
        assert result.is_ok
        overlay = result.danger_ok
        assert overlay["PYO3_PYTHON"] == "/usr/bin/python3.13"
        assert str(lib_dir) in overlay["LD_LIBRARY_PATH"]

    def test_cargo_env_err_when_no_qualifying_interpreter(self, monkeypatch) -> None:
        # frob:tests src/frob/testing/_runners.py::_cargo_env
        from typani import Ok

        import frob.testing._runners as runners_mod

        monkeypatch.delenv("PYO3_PYTHON", raising=False)
        monkeypatch.setattr(runners_mod.shutil, "which", lambda name: None)

        def fake_run_argv(argv, *, cwd=None, timeout_s=10.0):
            return Ok(
                ProcResult(argv=tuple(argv), returncode=1, stdout="", stderr="no such")
            )

        monkeypatch.setattr(runners_mod, "run_argv", fake_run_argv)
        result = runners_mod._cargo_env()
        assert result.is_err
        assert result.danger_err == TestingError.CargoEnvUnavailable

    def test_env_overlay_restores_prior_values(self, monkeypatch) -> None:
        # frob:tests src/frob/testing/_runners.py::_env_overlay
        import os

        from frob.testing._runners import _env_overlay

        # frob:waive SEC110 reason="synthetic test-only var this test itself sets via monkeypatch"
        monkeypatch.setenv("FROB_T0092_PROBE", "before")
        with _env_overlay({"FROB_T0092_PROBE": "during", "FROB_T0092_NEW": "x"}):
            assert os.environ["FROB_T0092_PROBE"] == "during"
            assert os.environ["FROB_T0092_NEW"] == "x"
        assert os.environ["FROB_T0092_PROBE"] == "before"
        assert "FROB_T0092_NEW" not in os.environ

    def test_rust_runner_refuses_to_spawn_when_env_unavailable(
        self, monkeypatch, tmp_path
    ) -> None:
        # frob:tests src/frob/testing/_runners.py::run_selected
        # Vacuous-pass guard (T-0102): a missing PyO3 env must surface as an
        # Err from run_selected, never a skipped-but-"ok" runner outcome.
        import frob.testing._runners as runners_mod
        from frob.testing._models import SelectionReport

        monkeypatch.setattr(
            runners_mod, "_cargo_env", lambda: Err(TestingError.CargoEnvUnavailable)
        )
        spec = RunnerSpec(
            language="rust",
            command=("cargo", "test", "--lib", "{filters}"),
            all_command=("cargo", "test", "--lib"),
        )
        selection = SelectionReport(
            touched=(),
            selected={"rust": ("crate/src/lib.rs::tests.foo",)},
            ripple=(),
            unbound=(),
            fallback="package",
        )
        result = run_selected(selection, (spec,), tmp_path)
        assert result.is_err
        assert result.danger_err == TestingError.CargoEnvUnavailable


class TestMultipleRunnersPerLanguage:
    """T-0128: two same-language `[[test.runner]]` entries (frob-core,
    strata-core), routed by which entry's `cwd` owns the touched file."""

    def _specs(self) -> tuple[RunnerSpec, RunnerSpec]:
        core = RunnerSpec(
            language="rust",
            command=("cargo", "test", "--lib", "{filters}"),
            all_command=("cargo", "test", "--lib"),
            cwd="frob-core",
        )
        strata = RunnerSpec(
            language="rust",
            command=("cargo", "test", "--lib", "{filters}"),
            all_command=("cargo", "test", "--lib"),
            cwd="strata-core",
        )
        return core, strata

    def _patch_env(self, monkeypatch) -> None:
        import frob.testing._runners as runners_mod

        monkeypatch.setattr(runners_mod, "_cargo_env", lambda: Ok({}))

    def test_routes_each_crate_to_its_own_runner(self, monkeypatch, tmp_path) -> None:
        # frob:tests src/frob/testing/_runners.py::run_selected
        import frob.testing._runners as runners_mod
        from frob.testing._models import SelectionReport

        self._patch_env(monkeypatch)
        seen: list[tuple[str, ...]] = []

        def fake_run_argv(argv, *, cwd=None, timeout_s=300.0):
            seen.append(tuple(argv))
            return Ok(ProcResult(argv=tuple(argv), returncode=0, stdout="", stderr=""))

        monkeypatch.setattr(runners_mod, "run_argv", fake_run_argv)
        core, strata = self._specs()
        selection = SelectionReport(
            touched=(),
            selected={
                "rust": (
                    "frob-core/src/dup_kernel.rs::tests.foo",
                    "strata-core/src/parse.rs::tests.bar",
                )
            },
            ripple=(),
            unbound=(),
            fallback="package",
        )
        result = run_selected(selection, (core, strata), tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert report.ok
        assert len(report.outcomes) == 2
        joined = [" ".join(argv) for argv in seen]
        assert any("tests::foo" in cmd for cmd in joined)
        assert any("tests::bar" in cmd for cmd in joined)

    def test_unowned_item_is_hard_error_not_vacuous_skip(
        self, monkeypatch, tmp_path
    ) -> None:
        # frob:tests src/frob/testing/_runners.py::run_selected
        import frob.testing._runners as runners_mod
        from frob.testing._models import SelectionReport

        self._patch_env(monkeypatch)
        monkeypatch.setattr(
            runners_mod,
            "run_argv",
            lambda *a, **k: Ok(ProcResult(argv=(), returncode=0, stdout="", stderr="")),
        )
        core, strata = self._specs()
        selection = SelectionReport(
            touched=(),
            selected={"rust": ("neither-crate/src/lib.rs::tests.foo",)},
            ripple=(),
            unbound=(),
            fallback="package",
        )
        result = run_selected(selection, (core, strata), tmp_path)
        assert result.is_err
        assert result.danger_err == TestingError.UnroutedItem

    def test_all_sentinel_runs_every_same_language_runner(
        self, monkeypatch, tmp_path
    ) -> None:
        # frob:tests src/frob/testing/_runners.py::run_selected
        import frob.testing._runners as runners_mod
        from frob.testing._models import SelectionReport
        from frob.testing._select import ALL_SENTINEL

        self._patch_env(monkeypatch)
        seen: list[tuple[str, ...]] = []

        def fake_run_argv(argv, *, cwd=None, timeout_s=300.0):
            seen.append(tuple(argv))
            return Ok(ProcResult(argv=tuple(argv), returncode=0, stdout="", stderr=""))

        monkeypatch.setattr(runners_mod, "run_argv", fake_run_argv)
        core, strata = self._specs()
        selection = SelectionReport(
            touched=(),
            selected={"rust": (ALL_SENTINEL,)},
            ripple=(),
            unbound=(),
            fallback="suite",
        )
        result = run_selected(selection, (core, strata), tmp_path)
        assert result.is_ok
        assert len(result.danger_ok.outcomes) == 2
        assert len(seen) == 2


class TestCollectRustTests:
    def _write_crate(self, root: Path) -> None:
        _write(
            root,
            "crate/Cargo.toml",
            """
            [package]
            name = "crate"
            version = "0.1.0"
            """,
        )
        _write(
            root,
            "crate/src/lib.rs",
            """
            #[cfg(test)]
            mod tests {
                #[test]
                fn reachable_returns_witness_paths() {}
            }
            """,
        )
        _write(
            root,
            "crate/src/parse.rs",
            """
            #[cfg(test)]
            mod tests {
                #[test]
                fn error_unknown_metric() {}
            }
            """,
        )

    def test_module_path_to_symref_inline_and_file_module(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_rust_tests
        from frob.testing._collect import _module_path_to_symref

        self._write_crate(tmp_path)
        crate_dir = tmp_path / "crate"
        assert (
            _module_path_to_symref(
                tmp_path, crate_dir, "tests::reachable_returns_witness_paths"
            )
            == "crate/src/lib.rs::tests::reachable_returns_witness_paths"
        )
        assert (
            _module_path_to_symref(
                tmp_path, crate_dir, "parse::tests::error_unknown_metric"
            )
            == "crate/src/parse.rs::tests::error_unknown_metric"
        )

    def test_collect_rust_tests_parses_and_caches(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_rust_tests
        from typani import Ok

        import frob.testing._collect as collect_mod

        self._write_crate(tmp_path)
        monkeypatch.setattr(
            collect_mod,
            "_cargo_env",
            lambda: Ok({"PYO3_PYTHON": "/usr/bin/python3.12"}),
        )

        calls: list[tuple] = []

        def fake_run_argv(argv, *, cwd=None, timeout_s=300.0):
            calls.append(tuple(argv))
            stdout = (
                "parse::tests::error_unknown_metric: test\n"
                "tests::reachable_returns_witness_paths: test\n"
                "\n2 tests, 0 benchmarks\n"
            )
            return Ok(
                ProcResult(argv=tuple(argv), returncode=0, stdout=stdout, stderr="")
            )

        monkeypatch.setattr(collect_mod, "run_argv", fake_run_argv)

        result = collect_mod.collect_rust_tests(tmp_path)
        assert result.is_ok
        assert result.danger_ok.node_ids == frozenset(
            {
                "crate/src/parse.rs::tests::error_unknown_metric",
                "crate/src/lib.rs::tests::reachable_returns_witness_paths",
            }
        )
        assert len(calls) == 1

        result2 = collect_mod.collect_rust_tests(tmp_path)
        assert result2.is_ok
        assert result2.danger_ok.node_ids == result.danger_ok.node_ids
        assert len(calls) == 1  # cache hit, no second spawn

    def test_collect_rust_tests_no_crates_is_ok_empty(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_rust_tests
        from frob.testing._collect import collect_rust_tests

        result = collect_rust_tests(tmp_path)
        assert result.is_ok
        assert result.danger_ok.node_ids == frozenset()

    def test_collect_rust_tests_skips_lib_less_crate(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # T-0301: a crate with no library target (a cargo-fuzz-shaped
        # bin-only harness) must be SKIPPED with an INFO log, not fail the
        # whole collection -- `cargo test --lib -- --list` exits nonzero for
        # it exactly like a genuine compile error would, so this is only
        # detected by cargo's own "no library targets found" wording.
        from typani import Ok

        import frob.testing._collect as collect_mod

        self._write_crate(tmp_path)
        _write(
            tmp_path,
            "libless/Cargo.toml",
            """
            [package]
            name = "libless"
            version = "0.1.0"
            """,
        )
        _write(tmp_path, "libless/src/main.rs", "fn main() {}\n")

        monkeypatch.setattr(
            collect_mod,
            "_cargo_env",
            lambda: Ok({"PYO3_PYTHON": "/usr/bin/python3.12"}),
        )

        def fake_run_argv(argv, *, cwd=None, timeout_s=300.0):
            if str(cwd).endswith("libless"):
                return Ok(
                    ProcResult(
                        argv=tuple(argv),
                        returncode=101,
                        stdout="",
                        stderr="error: no library targets found in package `libless`\n",
                    )
                )
            stdout = (
                "parse::tests::error_unknown_metric: test\n"
                "tests::reachable_returns_witness_paths: test\n"
                "\n2 tests, 0 benchmarks\n"
            )
            return Ok(
                ProcResult(argv=tuple(argv), returncode=0, stdout=stdout, stderr="")
            )

        monkeypatch.setattr(collect_mod, "run_argv", fake_run_argv)

        result = collect_mod.collect_rust_tests(tmp_path)
        assert result.is_ok
        assert result.danger_ok.node_ids == frozenset(
            {
                "crate/src/parse.rs::tests::error_unknown_metric",
                "crate/src/lib.rs::tests::reachable_returns_witness_paths",
            }
        )

    def test_collect_rust_tests_still_errs_on_genuine_compile_error(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # T-0301: a crate that fails to compile (not merely lib-less) must
        # still fail the whole collection -- only the specific "no library
        # targets found" wording is treated as a skip.
        from typani import Ok

        import frob.testing._collect as collect_mod

        self._write_crate(tmp_path)
        monkeypatch.setattr(
            collect_mod,
            "_cargo_env",
            lambda: Ok({"PYO3_PYTHON": "/usr/bin/python3.12"}),
        )

        def fake_run_argv(argv, *, cwd=None, timeout_s=300.0):
            return Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=101,
                    stdout="",
                    stderr="error: could not compile `crate` (lib test) due to 1 "
                    "previous error\n",
                )
            )

        monkeypatch.setattr(collect_mod, "run_argv", fake_run_argv)

        result = collect_mod.collect_rust_tests(tmp_path)
        assert result.is_err
        assert result.danger_err == TestingError.CollectFailed

    def test_collect_rust_tests_err_when_env_unavailable(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_rust_tests
        import frob.testing._collect as collect_mod

        self._write_crate(tmp_path)
        monkeypatch.setattr(
            collect_mod, "_cargo_env", lambda: Err(TestingError.CargoEnvUnavailable)
        )
        result = collect_mod.collect_rust_tests(tmp_path)
        assert result.is_err
        assert result.danger_err == TestingError.CargoEnvUnavailable


class TestFindCrates:
    """T-0271: a cargo virtual workspace root (`[workspace]`, no
    `[package]`) must be descended into, not collapsed into one bogus
    root "crate"."""

    def _workspace_root(self, root: Path) -> None:
        _write(
            root,
            "Cargo.toml",
            """
            [workspace]
            members = ["crates/a", "crates/b"]
            resolver = "2"
            """,
        )

    def _member_crate(self, root: Path, rel: str, name: str) -> None:
        _write(
            root,
            f"{rel}/Cargo.toml",
            f"""
            [package]
            name = "{name}"
            version = "0.1.0"
            """,
        )
        _write(root, f"{rel}/src/lib.rs", "pub fn noop() {}\n")

    def test_virtual_workspace_root_descends_to_members(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_rust_tests
        from frob.testing._collect import _find_crates

        self._workspace_root(tmp_path)
        self._member_crate(tmp_path, "crates/a", "a")
        self._member_crate(tmp_path, "crates/b", "b")

        found = _find_crates(tmp_path)
        assert found == sorted([tmp_path / "crates/a", tmp_path / "crates/b"])
        assert tmp_path not in found

    def test_root_package_with_nested_workspace_members(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_rust_tests
        from frob.testing._collect import _find_crates

        _write(
            tmp_path,
            "Cargo.toml",
            """
            [package]
            name = "root-crate"
            version = "0.1.0"

            [workspace]
            members = ["crates/a"]
            """,
        )
        _write(tmp_path, "src/lib.rs", "pub fn noop() {}\n")
        self._member_crate(tmp_path, "crates/a", "a")

        found = _find_crates(tmp_path)
        assert found == sorted([tmp_path, tmp_path / "crates/a"])

    def test_plain_single_crate_unchanged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_rust_tests
        from frob.testing._collect import _find_crates

        self._member_crate(tmp_path, ".", "solo")
        found = _find_crates(tmp_path)
        assert found == [tmp_path]

    def test_unparseable_manifest_keeps_old_behavior_and_warns(
        self, tmp_path: Path, caplog
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_rust_tests
        from frob.testing._collect import _find_crates

        _write(tmp_path, "Cargo.toml", "this is not [ valid toml")
        _write(tmp_path, "nested/Cargo.toml", "[package]\nname = 1 2 3 bad")

        with caplog.at_level("WARNING"):
            found = _find_crates(tmp_path)
        assert found == [tmp_path]  # old behavior: append + prune, no descent
        assert any("_find_crates" in msg for msg in caplog.messages)

    def test_find_crates_honors_graph_exclude(self, tmp_path: Path) -> None:
        # T-0274: a walker that doesn't consult [graph].exclude is exactly
        # the desync docs/strata/surface.md warns against -- a stale agent
        # worktree checkout (lithos's .claude/worktrees/**) must be pruned
        # before its own Cargo.toml is ever inspected.
        # frob:tests src/frob/testing/_collect.py::collect_rust_tests
        from frob.testing._collect import _find_crates

        self._member_crate(tmp_path, "crates/a", "a")
        self._member_crate(tmp_path, ".claude/worktrees/agent-x/crates/b", "b")
        _write(
            tmp_path,
            "frob.toml",
            """
            [graph]
            exclude = [".claude/worktrees/**"]
            """,
        )

        found = _find_crates(tmp_path)
        assert found == [tmp_path / "crates/a"]

    def test_walk_test_files_honors_graph_exclude(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_python_tests
        from frob.testing._collect import _find_test_files

        _write(tmp_path, "tests/test_real.py", "def test_x(): pass\n")
        _write(
            tmp_path,
            ".claude/worktrees/agent-x/tests/test_stale.py",
            "def test_x(): pass\n",
        )
        _write(
            tmp_path,
            "frob.toml",
            """
            [graph]
            exclude = [".claude/worktrees/**"]
            """,
        )

        found = _find_test_files(tmp_path)
        rels = {p.relative_to(tmp_path).as_posix() for p in found}
        assert rels == {"tests/test_real.py"}


class TestIntegrationTestCollection:
    """T-0271: `cargo test --lib` never lists `tests/*.rs` integration
    binaries, so `frob:tests` edges into a crate's tests/ files could
    never validate either -- verify the symref mapping directly."""

    def test_integration_module_path_to_symref_flat_case(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_rust_tests
        from frob.testing._collect import _integration_module_path_to_symref

        crate_dir = tmp_path / "crates" / "a"
        test_file = _write(
            tmp_path,
            "crates/a/tests/foo.rs",
            """
            #[test]
            fn end_to_end_smoke() {}
            """,
        )
        assert (
            _integration_module_path_to_symref(
                tmp_path, crate_dir, test_file, "end_to_end_smoke"
            )
            == "crates/a/tests/foo.rs::end_to_end_smoke"
        )

    def test_find_integration_test_files_lists_and_skips_missing_dir(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_rust_tests
        from frob.testing._collect import _find_integration_test_files

        crate_dir = tmp_path / "crates" / "a"
        assert _find_integration_test_files(crate_dir) == []

        _write(tmp_path, "crates/a/tests/foo.rs", "#[test]\nfn t() {}\n")
        _write(tmp_path, "crates/a/tests/bar.rs", "#[test]\nfn t() {}\n")
        found = _find_integration_test_files(crate_dir)
        assert found == sorted([crate_dir / "tests/foo.rs", crate_dir / "tests/bar.rs"])


# frob:waive DUP001 reason="parallel test fixtures across 2 sibling test \
# file(s) (2 sites) sharing an arrange-act scaffold typical of exhaustive \
# per-case/per-scenario coverage; extracting would obscure per-case intent"
def _fake_native_package(root: Path, name: str, so_bytes: bytes) -> Path:
    """A maturin-style extension PACKAGE on `root`: `name/__init__.py` plus a
    compiled `name.abi3.so` alongside it (the layout strata_core/frob_core
    install as). Returns `root` so the caller can put it on sys.path."""
    pkg = root / name
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("# fake native package\n")
    (pkg / f"{name}.abi3.so").write_bytes(so_bytes)
    return root


class TestNativeFingerprint:
    """T-0333: the collection cache must track native-extension build state."""

    def test_load_natives_parses_entries(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_runners.py::load_natives kind="unit"
        from frob.testing import load_natives

        toml_text = """
        [[native]]
        name = "strata_core"
        build_cmd = "make core"
        language = "rust"
        """
        (tmp_path / "frob.toml").write_text(textwrap.dedent(toml_text))
        result = load_natives(tmp_path)
        assert result.is_ok
        specs = result.danger_ok
        assert len(specs) == 1
        assert specs[0].name == "strata_core"
        assert specs[0].build_cmd == "make core"

    def test_load_natives_missing_table_is_ok_empty(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_runners.py::load_natives kind="unit"
        from frob.testing import load_natives

        (tmp_path / "frob.toml").write_text('[graph]\nsrc = ["src"]\n')
        result = load_natives(tmp_path)
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:waive DUP001 reason="parallel test methods within \
    # test_testing.py (2 sites) sharing an arrange-act scaffold typical of \
    # exhaustive per-case coverage; extracting would obscure per-case \
    # intent"
    def test_load_natives_missing_field_is_err(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_runners.py::load_natives kind="unit"
        from frob.testing import TestingError, load_natives

        (tmp_path / "frob.toml").write_text('[[native]]\nname = "x"\n')
        result = load_natives(tmp_path)
        assert result.is_err
        assert result.danger_err == TestingError.BadRunnerSpec

    def test_absent_native_fingerprints_as_absent(self) -> None:
        # frob:tests src/frob/testing/_collect.py::_native_artifact_digest kind="unit"
        from frob.testing import NativeSpec
        from frob.testing._collect import _native_artifact_digest

        spec = NativeSpec(name="frob_no_such_native_xyz", build_cmd="make core")
        assert _native_artifact_digest(spec) == "frob_no_such_native_xyz:absent"

    def test_fingerprint_changes_absent_to_built(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::_native_fingerprint kind="unit"
        # AC1: unbuilt->built must flip the fingerprint (and thus the cache key).
        import importlib

        from frob.testing import NativeSpec
        from frob.testing._collect import _native_fingerprint

        name = "fakenat_build"
        specs = (NativeSpec(name=name, build_cmd="make core"),)
        # absent -> deterministic "absent" fingerprint
        before = _native_fingerprint(specs)

        _fake_native_package(tmp_path, name, b"\x00compiled-v1")
        monkeypatch.syspath_prepend(str(tmp_path))
        importlib.invalidate_caches()
        after = _native_fingerprint(specs)
        assert before != after

    def test_fingerprint_changes_on_rebuild(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests src/frob/testing/_collect.py::_native_artifact_digest kind="unit"
        # AC1: a RECOMPILE (same package, different .so bytes) must flip it too,
        # even though the package __init__.py is unchanged.
        import importlib

        from frob.testing import NativeSpec
        from frob.testing._collect import _compiled_artifacts, _native_artifact_digest

        name = "fakenat_rebuild"
        spec = NativeSpec(name=name, build_cmd="make core")
        _fake_native_package(tmp_path, name, b"\x00compiled-v1")
        monkeypatch.syspath_prepend(str(tmp_path))
        importlib.invalidate_caches()
        # sanity: it resolves to the .so, not the __init__.py
        found = importlib.util.find_spec(name)
        assert found is not None
        assert [p.name for p in _compiled_artifacts(found)] == [f"{name}.abi3.so"]
        first = _native_artifact_digest(spec)

        (tmp_path / name / f"{name}.abi3.so").write_bytes(b"\x00compiled-v2")
        importlib.invalidate_caches()
        second = _native_artifact_digest(spec)
        assert first != second
        assert first != f"{name}:absent"

    def test_collection_cache_key_reflects_native_state(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_collect.py::_collection_cache_key kind="unit"
        from frob.testing import NativeSpec
        from frob.testing._collect import _collection_cache_key

        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_a.py").write_text("def test_x():\n    pass\n")
        absent = NativeSpec(name="frob_no_such_native_xyz", build_cmd="make core")
        key_no_native = _collection_cache_key(tmp_path, ())
        key_absent_native = _collection_cache_key(tmp_path, (absent,))
        # declaring a (currently-absent) native changes the key vs none declared
        assert key_no_native != key_absent_native

    def test_missing_natives_reports_unbuilt(self) -> None:
        # frob:tests src/frob/testing/_collect.py::_missing_natives kind="unit"
        from frob.testing import NativeSpec
        from frob.testing._collect import _missing_natives

        absent = NativeSpec(name="frob_no_such_native_xyz", build_cmd="make core")
        missing = _missing_natives((absent,))
        assert [s.name for s in missing] == ["frob_no_such_native_xyz"]

    def test_drop_collection_cache_removes_file(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_collect.py::drop_collection_cache kind="unit"
        from frob.testing import drop_collection_cache

        cache = tmp_path / ".frob" / "pytest-collect.json"
        cache.parent.mkdir(parents=True)
        cache.write_text("{}")
        assert drop_collection_cache(tmp_path) is True
        assert not cache.exists()
        # idempotent: dropping an absent cache is a no-op, not an error
        assert drop_collection_cache(tmp_path) is False

    def test_drop_collection_cache_unremovable_is_false(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_collect.py::drop_collection_cache kind="unit"
        # the OSError path: cache path is a non-empty directory, so unlink fails
        # -- reported as False, never raised.
        from frob.testing import drop_collection_cache

        cache_dir = tmp_path / ".frob" / "pytest-collect.json"
        cache_dir.mkdir(parents=True)
        (cache_dir / "sentinel").write_text("x")  # non-empty -> unlink raises
        assert drop_collection_cache(tmp_path) is False

    # frob:waive DUP001 reason="parallel test methods within \
    # test_testing.py (2 sites) sharing an arrange-act scaffold typical of \
    # exhaustive per-case coverage; extracting would obscure per-case \
    # intent"
    def test_load_natives_malformed_toml_is_err(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_runners.py::load_natives kind="unit"
        from frob.testing import TestingError, load_natives

        (tmp_path / "frob.toml").write_text("this is [not valid toml")
        result = load_natives(tmp_path)
        assert result.is_err
        assert result.danger_err == TestingError.BadRunnerSpec

    def test_native_digest_error_on_bad_name(self, monkeypatch) -> None:
        # frob:tests src/frob/testing/_collect.py::_native_artifact_digest kind="unit"
        # find_spec raising (half-installed/shadowed name) fingerprints as
        # ":error", never propagating the exception into collection.
        import importlib.util

        from frob.testing import NativeSpec
        from frob.testing._collect import _native_artifact_digest

        def _boom(name: str):
            raise ValueError("bad parent package")

        monkeypatch.setattr(importlib.util, "find_spec", _boom)
        spec = NativeSpec(name="whatever", build_cmd="make core")
        assert _native_artifact_digest(spec) == "whatever:error"

    def test_single_file_extension_fingerprinted(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::_compiled_artifacts kind="unit"
        # a single-FILE extension (origin IS the .so, no package dir) is
        # fingerprinted directly -- the c/c++-style layout, vs the maturin
        # package layout covered above.
        import importlib

        from frob.testing._collect import _compiled_artifacts

        so = tmp_path / "singlemod.abi3.so"
        so.write_bytes(b"\x00ext")
        monkeypatch.syspath_prepend(str(tmp_path))
        importlib.invalidate_caches()
        found = importlib.util.find_spec("singlemod")
        assert found is not None
        assert [p.name for p in _compiled_artifacts(found)] == ["singlemod.abi3.so"]


class TestCollectBranchGaps:
    """T-0160 batch 8: TEST005 branch-coverage gaps in
    src/frob/testing/_collect.py that the tests above never exercise --
    error/degraded paths in the python and rust collection pipelines."""

    def test_walk_test_files_matches_suffix_style_test_files(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_python_tests kind="unit"
        # the `*_test.py` naming convention (as opposed to `test_*.py`) is a
        # separate branch in _walk_test_files -- must be matched too.
        from frob.testing._collect import _find_test_files

        _write(tmp_path, "tests/thing_test.py", "def test_x(): pass\n")
        found = _find_test_files(tmp_path)
        rels = {p.relative_to(tmp_path).as_posix() for p in found}
        assert rels == {"tests/thing_test.py"}

    def test_content_key_unreadable_file_is_skipped_not_raised(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_python_tests kind="unit"
        # an OSError reading one test file's bytes must be logged and
        # skipped, not propagated -- one unreadable file must not take
        # down the whole content-hash computation.
        from frob.testing._collect import _content_key

        _write(tmp_path, "tests/test_a.py", "def test_x(): pass\n")
        real_read_bytes = Path.read_bytes

        def fake_read_bytes(self):
            if self.name == "test_a.py":
                raise OSError("permission denied")
            return real_read_bytes(self)

        monkeypatch.setattr(Path, "read_bytes", fake_read_bytes)
        # must not raise
        key = _content_key(tmp_path)
        assert isinstance(key, str) and key

    def test_native_artifact_digest_resolvable_no_compiled_artifact(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::_native_artifact_digest kind="unit"
        # a name that resolves (e.g. a pure-python stub standing in for an
        # unbuilt native) but has no compiled artifact must fingerprint as
        # "absent", the same as a name that does not resolve at all.
        import importlib

        from frob.testing import NativeSpec
        from frob.testing._collect import _native_artifact_digest

        name = "fakenat_purepy_stub"
        pkg = tmp_path / name
        pkg.mkdir()
        (pkg / "__init__.py").write_text("# pure-python stub, no .so\n")
        monkeypatch.syspath_prepend(str(tmp_path))
        importlib.invalidate_caches()
        spec = NativeSpec(name=name, build_cmd="make core")
        assert _native_artifact_digest(spec) == f"{name}:absent"

    def test_native_artifact_digest_unreadable_artifact(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::_native_artifact_digest kind="unit"
        # an OSError reading the compiled artifact's bytes reports
        # ":unreadable" rather than raising.
        import importlib

        from frob.testing import NativeSpec
        from frob.testing._collect import _native_artifact_digest

        name = "fakenat_unreadable"
        _fake_native_package(tmp_path, name, b"\x00v1")
        monkeypatch.syspath_prepend(str(tmp_path))
        importlib.invalidate_caches()

        real_read_bytes = Path.read_bytes

        def fake_read_bytes(self):
            if self.suffix == ".so":
                raise OSError("boom")
            return real_read_bytes(self)

        monkeypatch.setattr(Path, "read_bytes", fake_read_bytes)
        spec = NativeSpec(name=name, build_cmd="make core")
        assert _native_artifact_digest(spec) == f"{name}:unreadable"

    def test_missing_natives_treats_find_spec_error_as_missing(
        self, monkeypatch
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::_missing_natives kind="unit"
        # find_spec raising ImportError/ValueError for one declared native
        # must not crash the whole scan -- it counts as missing.
        import importlib.util

        from frob.testing import NativeSpec
        from frob.testing._collect import _missing_natives

        def _boom(name: str):
            raise ImportError("shadowed name")

        monkeypatch.setattr(importlib.util, "find_spec", _boom)
        specs = (NativeSpec(name="whatever", build_cmd="make core"),)
        missing = _missing_natives(specs)
        assert [s.name for s in missing] == ["whatever"]

    def test_load_natives_or_empty_degrades_on_malformed_config(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_python_tests kind="unit"
        # a malformed [[native]] table must not take down collection --
        # it degrades to an empty native tuple with a warning.
        from frob.testing._collect import _load_natives_or_empty

        (tmp_path / "frob.toml").write_text("this is [not valid toml")
        assert _load_natives_or_empty(tmp_path) == ()

    def test_load_cache_unreadable_json_is_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_python_tests kind="unit"
        from frob.testing._collect import _load_cache

        cache_path = tmp_path / "cache.json"
        cache_path.write_text("not valid json{{{")
        assert _load_cache(cache_path, "somekey") is None

    def test_load_cache_key_mismatch_is_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_python_tests kind="unit"
        import json

        from frob.testing._collect import _load_cache

        cache_path = tmp_path / "cache.json"
        cache_path.write_text(json.dumps({"key": "old-key", "node_ids": ["a::b"]}))
        assert _load_cache(cache_path, "new-key") is None

    def test_run_collect_only_spawn_failure_is_err(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_python_tests kind="unit"
        import frob.testing._collect as collect_mod
        from frob.gitio import GitError
        from frob.testing import TestingError

        def fake_run_argv(argv, *, cwd=None, timeout_s=300.0):
            return Err(GitError.GitFailed)

        monkeypatch.setattr(collect_mod, "run_argv", fake_run_argv)
        result = collect_mod._run_collect_only(tmp_path)
        assert result.is_err
        assert result.danger_err == TestingError.CollectFailed

    def test_run_collect_only_bad_exit_code_is_err(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_python_tests kind="unit"
        import frob.testing._collect as collect_mod
        from frob.testing import TestingError

        def fake_run_argv(argv, *, cwd=None, timeout_s=300.0):
            return Ok(
                ProcResult(argv=tuple(argv), returncode=2, stdout="", stderr="boom")
            )

        monkeypatch.setattr(collect_mod, "run_argv", fake_run_argv)
        result = collect_mod._run_collect_only(tmp_path)
        assert result.is_err
        assert result.danger_err == TestingError.CollectFailed

    def test_reroot_node_ids_noop_for_dot_cwd(self) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_python_tests kind="unit"
        # cwd_rel == "." (the outer collection's own runner) must be a
        # no-op -- the untouched no-op branch is never hit by the outer
        # collection pass itself, only via a direct call.
        from frob.testing._collect import _reroot_node_ids

        ids = frozenset({"tests/test_a.py::test_x"})
        assert _reroot_node_ids(ids, ".") == ids
        assert _reroot_node_ids(ids, "") == ids

    def test_python_runner_cwds_degrades_on_bad_runner_config(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_python_tests kind="unit"
        # a malformed [[test.runner]] table must degrade to "outer tree
        # only" rather than crashing collection.
        from frob.testing._collect import _python_runner_cwds

        (tmp_path / "frob.toml").write_text("this is [not valid toml")
        assert _python_runner_cwds(tmp_path) == []

    def test_python_runner_cwds_dedupes_repeated_cwd(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_python_tests kind="unit"
        # two [[test.runner]] entries pointed at the SAME nested cwd must
        # only be visited once.
        from frob.testing._collect import _python_runner_cwds

        _write(
            tmp_path,
            "frob.toml",
            """
            [[test.runner]]
            language = "python"
            command = ["uv", "run", "pytest", "-q", "{ids}"]
            all_command = ["uv", "run", "pytest", "-q"]
            cwd = "nested"

            [[test.runner]]
            language = "python"
            command = ["pytest", "{ids}"]
            all_command = ["pytest"]
            cwd = "nested"
            """,
        )
        assert _python_runner_cwds(tmp_path) == ["nested"]

    def test_collect_nested_python_propagates_collect_failure(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_python_tests kind="unit"
        import frob.testing._collect as collect_mod
        from frob.testing import TestingError

        (tmp_path / "nested").mkdir()

        def fake_run_argv(argv, *, cwd=None, timeout_s=300.0):
            return Ok(ProcResult(argv=tuple(argv), returncode=2, stdout="", stderr="x"))

        monkeypatch.setattr(collect_mod, "run_argv", fake_run_argv)
        result = collect_mod._collect_nested_python(tmp_path, "nested")
        assert result.is_err
        assert result.danger_err == TestingError.CollectFailed

    def test_collect_python_tests_outer_collection_failure_is_err(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_python_tests kind="unit"
        import frob.testing._collect as collect_mod
        from frob.testing import TestingError

        def fake_run_argv(argv, *, cwd=None, timeout_s=300.0):
            return Ok(ProcResult(argv=tuple(argv), returncode=2, stdout="", stderr="x"))

        monkeypatch.setattr(collect_mod, "run_argv", fake_run_argv)
        result = collect_mod.collect_python_tests(tmp_path)
        assert result.is_err
        assert result.danger_err == TestingError.CollectFailed

    def test_collect_python_tests_nested_failure_degrades_with_warning(
        self, tmp_path: Path, monkeypatch, caplog
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_python_tests kind="unit"
        # a nested runner cwd that fails to collect must be logged and
        # skipped -- the outer tree's own results still come back Ok.
        import frob.testing._collect as collect_mod

        _write(
            tmp_path,
            "frob.toml",
            """
            [[test.runner]]
            language = "python"
            command = ["uv", "run", "pytest", "-q", "{ids}"]
            all_command = ["uv", "run", "pytest", "-q"]
            cwd = "nested"
            """,
        )
        _write(tmp_path, "tests/test_outer.py", "def test_outer(): pass\n")
        (tmp_path / "nested").mkdir()

        def fake_run_argv(argv, *, cwd=None, timeout_s=300.0):
            if cwd == tmp_path / "nested":
                return Ok(
                    ProcResult(argv=tuple(argv), returncode=2, stdout="", stderr="x")
                )
            return Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=0,
                    stdout="tests/test_outer.py::test_outer\n",
                    stderr="",
                )
            )

        monkeypatch.setattr(collect_mod, "run_argv", fake_run_argv)
        with caplog.at_level("WARNING"):
            result = collect_mod.collect_python_tests(tmp_path)
        assert result.is_ok
        assert result.danger_ok.node_ids == frozenset(
            {"tests/test_outer.py::test_outer"}
        )
        assert any("nested collection failed" in msg for msg in caplog.messages)

    def test_rust_content_key_unreadable_file_is_skipped(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_rust_tests kind="unit"
        from frob.testing._collect import _rust_content_key

        _write(tmp_path, "src/lib.rs", "pub fn noop() {}\n")
        _write(
            tmp_path,
            "Cargo.toml",
            """
            [package]
            name = "solo"
            version = "0.1.0"
            """,
        )
        real_read_bytes = Path.read_bytes

        def fake_read_bytes(self):
            if self.name == "lib.rs":
                raise OSError("boom")
            return real_read_bytes(self)

        monkeypatch.setattr(Path, "read_bytes", fake_read_bytes)
        key = _rust_content_key(tmp_path)
        assert isinstance(key, str) and key

    def test_cargo_list_result_spawn_failure_is_err(self) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_rust_tests kind="unit"
        from frob.gitio import GitError
        from frob.testing import TestingError
        from frob.testing._collect import _cargo_list_result

        result = _cargo_list_result(Err(GitError.GitFailed), Path("/tmp/crate"))
        assert result.is_err
        assert result.danger_err == TestingError.CollectFailed

    def test_run_cargo_test_list_integration_failure_propagates(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/testing/_collect.py::collect_rust_tests kind="unit"
        # an integration binary's `cargo test --test <stem> -- --list`
        # failing (real compile error, not the no-lib-target case) must
        # propagate as Err from _collect_rust_uncached, not be swallowed.
        import frob.testing._collect as collect_mod
        from frob.testing import TestingError

        self_member = tmp_path
        _write(
            self_member,
            "Cargo.toml",
            """
            [package]
            name = "solo"
            version = "0.1.0"
            """,
        )
        _write(self_member, "src/lib.rs", "pub fn noop() {}\n")
        _write(self_member, "tests/foo.rs", "#[test]\nfn t() {}\n")

        def fake_cargo_env():
            return Ok({})

        def fake_run_argv(argv, *, cwd=None, timeout_s=300.0):
            if "--test" in argv:
                return Ok(
                    ProcResult(
                        argv=tuple(argv),
                        returncode=101,
                        stdout="",
                        stderr="error[E0433]: real compile error",
                    )
                )
            return Ok(ProcResult(argv=tuple(argv), returncode=0, stdout="", stderr=""))

        monkeypatch.setattr(collect_mod, "_cargo_env", fake_cargo_env)
        monkeypatch.setattr(collect_mod, "run_argv", fake_run_argv)
        result = collect_mod._collect_rust_uncached(tmp_path)
        assert result.is_err
        assert result.danger_err == TestingError.CollectFailed
