"""T-1161: `frob.testing.python_collection_failure_detail` -- the honest
detail (argv/exit-code/stderr-tail) `collect_python_tests` records when
its outer `pytest --collect-only` fails outright, read by `frob.gates.
coverage_gate`'s COV003 wiring so a broken collector reports as ONE
finding instead of one per archived evidence id (the 2026-07-28 incident:
a corrupted `.venv/bin/pytest` shim broke `uv run pytest` entirely, and
6219 archived evidence ids each independently "failed to resolve" with no
hint at the shared root cause)."""

from __future__ import annotations

from pathlib import Path

from typani import Err, Ok

from frob.gitio import ProcResult
from frob.process._pytest_spawn import PytestSpawnError


class TestPythonCollectionFailureDetail:
    # frob:tests src/frob/testing/_collect.py::python_collection_failure_detail
    def test_none_before_any_call(self) -> None:
        """Freshly imported, no collection has happened yet -- detail is
        `None`. Guarded by an explicit reset so an earlier test's failure
        in the same process cannot leak into this assertion."""
        import frob.testing._collect as collect_mod

        collect_mod._set_collection_failure_detail(None)
        assert collect_mod.python_collection_failure_detail() is None

    # frob:tests src/frob/testing/_collect.py::collect_python_tests
    def test_outer_collection_failure_records_detail_with_stderr_tail(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """A failing outer `pytest --collect-only` still returns the same
        `Err(TestingError.CollectFailed)` every existing caller already
        handles (T-1161 is additive, not a contract break) -- but ALSO
        populates `python_collection_failure_detail()` with the exit code
        and stderr tail, so a caller that wants richer diagnosis (`frob.
        gates`'s coverage gate) can read it right after seeing the Err."""
        import frob.testing._collect as collect_mod
        from frob.testing import TestingError

        def fake_run_argv(argv, *, cwd=None, timeout_s=300.0):
            return Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=2,
                    stdout="",
                    stderr="ModuleNotFoundError: no module named strata_core",
                )
            )

        monkeypatch.setattr(collect_mod, "run_argv", fake_run_argv)
        result = collect_mod.collect_python_tests(tmp_path)
        assert result.is_err
        assert result.danger_err == TestingError.CollectFailed

        detail = collect_mod.python_collection_failure_detail()
        assert detail is not None
        assert "exited 2" in detail
        assert "ModuleNotFoundError" in detail

    # frob:tests src/frob/testing/_collect.py::collect_python_tests
    def test_successful_collection_clears_a_prior_failure_detail(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """A stale failure detail from a PRIOR call must not survive a
        subsequent successful collection -- otherwise a transient failure
        (e.g. a flaky spawn) could misattribute a later, healthy run's
        COV003s to a collection failure that no longer exists."""
        import frob.testing._collect as collect_mod

        def failing_run_argv(argv, *, cwd=None, timeout_s=300.0):
            return Ok(
                ProcResult(argv=tuple(argv), returncode=2, stdout="", stderr="boom")
            )

        monkeypatch.setattr(collect_mod, "run_argv", failing_run_argv)
        first = collect_mod.collect_python_tests(tmp_path)
        assert first.is_err
        assert collect_mod.python_collection_failure_detail() is not None

        def ok_run_argv(argv, *, cwd=None, timeout_s=300.0):
            return Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=0,
                    stdout="tests/test_x.py::test_a\n",
                    stderr="",
                )
            )

        monkeypatch.setattr(collect_mod, "run_argv", ok_run_argv)
        collect_mod.drop_collection_cache(tmp_path)
        second = collect_mod.collect_python_tests(tmp_path)
        assert second.is_ok
        assert collect_mod.python_collection_failure_detail() is None


class TestRunCollectOnlySpawnShape:
    """T-4327: `_run_collect_only` must never shell out through `uv` --
    the macOS CI cascade (68 -> 61 failing tests across two spawn-mechanism
    attempts) traced to exactly that: `uv run pytest` in a throwaway
    fixture `cwd` relies on `uv`'s VIRTUAL_ENV-fallback, which a newer `uv`
    (pulled fresh by a setup-uv cache miss, unrelated to `sys.platform`)
    validates by path and ignores, building an empty venv with no `pytest`
    installed. Routing through `frob.process._pytest_spawn.
    resolve_pytest_argv` instead spawns `pytest` as a module of THIS
    interpreter (`sys.executable`) -- `uv` is never invoked for this spawn,
    so there is nothing for a `uv` version/cache change to break."""

    # frob:tests src/frob/testing/_collect.py::collect_python_tests
    def test_argv_never_names_uv(self, tmp_path: Path, monkeypatch) -> None:
        """The regression itself: the argv `run_argv` is actually called
        with must start with `sys.executable`, never the literal `"uv"`."""
        import sys

        import frob.testing._collect as collect_mod

        captured: dict[str, tuple[str, ...]] = {}

        def capture_run_argv(argv, *, cwd=None, timeout_s=300.0):
            captured["argv"] = tuple(argv)
            return Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=0,
                    stdout="tests/test_x.py::test_a\n",
                    stderr="",
                )
            )

        monkeypatch.setattr(collect_mod, "run_argv", capture_run_argv)
        result = collect_mod.collect_python_tests(tmp_path)
        assert result.is_ok
        assert captured["argv"][0] == sys.executable
        assert "uv" not in captured["argv"]
        assert captured["argv"][1:4] == ("-m", "pytest", "--collect-only")

    # frob:tests src/frob/testing/_collect.py::collect_python_tests
    def test_pytest_not_importable_is_a_collect_failure_without_spawning(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """When `resolve_pytest_argv` itself reports `pytest` is not
        importable through this interpreter, collection must fail loudly
        (`Err(CollectFailed)` with a detail naming the interpreter) --
        and must never fall through to a `run_argv` spawn at all, since
        there is no argv to spawn."""
        import frob.testing._collect as collect_mod
        from frob.testing import TestingError

        def unreachable_run_argv(argv, *, cwd=None, timeout_s=300.0):
            raise AssertionError(
                "run_argv must not be called when pytest is unimportable"
            )

        monkeypatch.setattr(collect_mod, "run_argv", unreachable_run_argv)
        monkeypatch.setattr(
            collect_mod,
            "resolve_pytest_argv",
            lambda *args, python=None: Err(PytestSpawnError.NotImportable),
        )
        result = collect_mod.collect_python_tests(tmp_path)
        assert result.is_err
        assert result.danger_err == TestingError.CollectFailed
        detail = collect_mod.python_collection_failure_detail()
        assert detail is not None
        assert "not importable" in detail
