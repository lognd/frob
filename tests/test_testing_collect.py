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
    # frob:tests \
    # src/frob/testing/_collect_python_cache.py::python_collection_failure_detail
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


class TestPlatformSkippedSurvivesCacheHit:
    """T-4390: measured live on Windows CI (run 34415921529) -- COV003 kept
    erroring on the SAME platform-skipped evidence T-4382's fix targets,
    because the job's `frob check` self-gate step runs AFTER an earlier
    `frob test` step already warmed `.frob/pytest-collect.json`; T-4382's
    cache-HIT path read `platform_skipped` back as `()` regardless of what
    the ORIGINAL (cache-MISS) collection found, since the plain node-id
    cache never carried skip reasons at all. `_load_cache_extra`/
    `_store_cache`'s `extra` payload (T-4390) closes that gap."""

    # frob:tests src/frob/testing/_collect.py::collect_python_tests
    def test_platform_skipped_round_trips_through_a_cache_hit(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """A cache MISS that discovers a platform-skipped module, followed
        by a cache HIT on an unchanged tree, must report the SAME
        `platform_skipped` pairs both times -- not `()` on the hit."""
        import frob.testing._collect as collect_mod
        from tests.conftest import _write

        _write(
            tmp_path,
            "tests/test_posix_only.py",
            "import sys\nimport pytest\n"
            'if sys.platform == "win32":\n'
            '    pytest.skip("SIGUSR1 is POSIX-only", allow_module_level=True)\n'
            "def test_a():\n    pass\n",
        )

        def fake_run_argv(argv, *, cwd=None, timeout_s=300.0):
            return Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=0,
                    stdout=(
                        "tests/test_posix_only.py::test_a\n"
                        "SKIPPED [1] tests/test_posix_only.py:4: "
                        "SIGUSR1 is POSIX-only\n"
                    ),
                    stderr="",
                )
            )

        monkeypatch.setattr(collect_mod, "run_argv", fake_run_argv)
        collect_mod.drop_collection_cache(tmp_path)
        first = collect_mod.collect_python_tests(tmp_path)
        assert first.is_ok
        assert first.danger_ok.platform_skipped == (
            ("tests/test_posix_only.py", "SIGUSR1 is POSIX-only"),
        )

        def failing_if_called_run_argv(argv, *, cwd=None, timeout_s=300.0):
            raise AssertionError(
                "a cache HIT must never re-spawn pytest --collect-only"
            )

        monkeypatch.setattr(collect_mod, "run_argv", failing_if_called_run_argv)
        second = collect_mod.collect_python_tests(tmp_path)
        assert second.is_ok
        assert second.danger_ok.platform_skipped == (
            ("tests/test_posix_only.py", "SIGUSR1 is POSIX-only"),
        )


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


class TestCollectorPython:
    """T-4349: `_run_collect_only` must collect a project that HAS its own
    real `.venv` (a scaffolded project after `uv sync`, T-4327's docstring
    calls out this exact case) through THAT venv's interpreter, not the
    calling frob process's own `sys.executable` -- the latter has none of
    the target project's dependencies installed and fails collection with
    e.g. `ModuleNotFoundError` on every test module importing the
    project's own package. A `cwd` with no usable venv of its own (T-4327's
    original throwaway-fixture case) must still fall back to `sys.
    executable` exactly as before."""

    # frob:tests src/frob/testing/_collect.py::_collector_python
    def test_prefers_cwds_own_venv_when_pytest_importable(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """A `cwd` with a `.venv/bin/python` that has `pytest` importable
        is preferred over `sys.executable`."""
        import frob.testing._collect as collect_mod

        venv_python = tmp_path / ".venv" / "bin" / "python"
        venv_python.parent.mkdir(parents=True)
        venv_python.touch()

        monkeypatch.setattr(collect_mod, "pytest_importable", lambda python: True)
        assert collect_mod._collector_python(tmp_path) == str(venv_python)

    # frob:tests src/frob/testing/_collect.py::_collector_python
    def test_falls_back_to_sys_executable_with_no_venv(self, tmp_path: Path) -> None:
        """No `.venv/bin/python` at all (the throwaway-fixture case T-4327
        fixed) -- unchanged `sys.executable` fallback."""
        import sys

        import frob.testing._collect as collect_mod

        assert collect_mod._collector_python(tmp_path) == sys.executable

    # frob:tests src/frob/testing/_collect.py::_collector_python
    def test_falls_back_to_sys_executable_when_venv_pytest_unimportable(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """A `.venv/bin/python` exists but `pytest` is NOT importable
        through it (e.g. a venv `uv sync` never populated) -- falls back
        to `sys.executable` rather than handing back an unusable
        interpreter."""
        import sys

        import frob.testing._collect as collect_mod

        venv_python = tmp_path / ".venv" / "bin" / "python"
        venv_python.parent.mkdir(parents=True)
        venv_python.touch()

        monkeypatch.setattr(collect_mod, "pytest_importable", lambda python: False)
        assert collect_mod._collector_python(tmp_path) == sys.executable


class TestCollectionFailureStdoutFallback:
    """T-4349: pytest writes its own collection errors (ImportError
    tracebacks, "N errors during collection") to STDOUT, not stderr --
    the empty-stderr-tail diagnostic on the scaffold-check CI failure
    traced to exactly this. The recorded detail must fall back to the
    stdout tail whenever stderr has nothing in it."""

    # frob:tests src/frob/testing/_collect.py::collect_python_tests
    def test_empty_stderr_falls_back_to_stdout_tail(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        import frob.testing._collect as collect_mod

        def fake_run_argv(argv, *, cwd=None, timeout_s=300.0):
            return Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=2,
                    stdout="ModuleNotFoundError: No module named 'demo'",
                    stderr="",
                )
            )

        monkeypatch.setattr(collect_mod, "run_argv", fake_run_argv)
        result = collect_mod.collect_python_tests(tmp_path)
        assert result.is_err

        detail = collect_mod.python_collection_failure_detail()
        assert detail is not None
        assert "stderr was empty" in detail
        assert "ModuleNotFoundError: No module named 'demo'" in detail


class TestParsePlatformSkippedWindowsPathShape:
    """T-4408: measured live on Windows CI -- COV003/TEST002 kept flooding
    on POSIX-only test modules T-4382/T-4386's platform-skip attribution
    was supposed to cover, because `pytest --collect-only -rs` reports the
    skipped module's file with the platform's native path separator (a
    backslash path on Windows), while every consumer of
    `platform_skipped` (`_evidence_platform_skip_reason`,
    `_edges_platform_skip_reason`) compares it against POSIX-style
    (forward-slash) evidence ids and `frob:tests` symrefs with plain
    `==`. `_parse_platform_skipped` must normalize the captured path to
    forward-slash so the comparison holds regardless of platform."""

    # frob:tests src/frob/testing/_collect_python_cache.py::_parse_platform_skipped
    def test_windows_backslash_path_normalizes_to_posix(self) -> None:
        import frob.testing._collect as collect_mod

        stdout = "SKIPPED [1] tests\\unit\\test_stackdump.py:12: posix-only\r\n"
        found = collect_mod._parse_platform_skipped(stdout)
        assert found == (("tests/unit/test_stackdump.py", "posix-only"),)

    # frob:tests src/frob/testing/_collect_python_cache.py::_parse_platform_skipped
    def test_windows_crlf_and_nested_backslash_path(self) -> None:
        import frob.testing._collect as collect_mod

        stdout = (
            "..\r\n"
            "SKIPPED [3] tests\\unit\\test_conftest_stackdump.py:7: "
            "posix-only fixture\r\n"
            "5 passed, 3 skipped in 1.23s\r\n"
        )
        found = collect_mod._parse_platform_skipped(stdout)
        assert found == (
            ("tests/unit/test_conftest_stackdump.py", "posix-only fixture"),
        )

    # frob:tests src/frob/testing/_collect_python_cache.py::_parse_platform_skipped
    def test_posix_path_is_unaffected(self) -> None:
        import frob.testing._collect as collect_mod

        stdout = "SKIPPED [1] tests/unit/test_stackdump.py:12: posix-only\n"
        found = collect_mod._parse_platform_skipped(stdout)
        assert found == (("tests/unit/test_stackdump.py", "posix-only"),)
