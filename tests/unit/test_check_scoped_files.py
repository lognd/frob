"""T-4413: `frob check --files ...` scopes the ruff/ty/gate compute floor
to a caller-given path set instead of walking the whole tree -- the
speedup a rapid land's synchronous pre-land check needs to fit its budget.
Covers: CLI/config parsing, ruff/ty argv actually receiving the file list,
`_python_tasks` leaving `arch`/`cycle`/`dup`/`exports` unscoped, `GateConfig.
files` reaching `run_gates`, and rapid land passing `--files` to its shared
check spawn while standard does not."""

from __future__ import annotations

from pathlib import Path

from typani import Ok


def _FakeProc(stdout: str = "", returncode: int = 0, stderr: str = ""):  # noqa: N802
    """Minimal `subprocess.CompletedProcess`-shaped stand-in, matching the
    sibling helper in `test_check.py`."""

    class _P:
        def __init__(self):
            self.stdout = stdout
            self.stderr = stderr
            self.returncode = returncode

    return _P()


class TestCheckFilesConfigParsing:
    """`AppConfig.check_files`: `None` by default, a tuple when `--files`
    is repeated on the CLI."""

    def test_default_is_none(self) -> None:
        # frob:tests src/frob/app/config.py::AppConfig kind="unit"
        from frob.app.config import AppConfig

        assert AppConfig().check_files is None

    def test_from_external_collects_repeated_files_flag(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/_config_external.py::_apply_list_fields kind="unit"
        import argparse

        from frob.app.config import AppConfig

        args = argparse.Namespace(check_files=["a.py", "b/c.py"])
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        assert cfg.check_files == ("a.py", "b/c.py")

    def test_from_external_unset_stays_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/_config_external.py::_apply_list_fields kind="unit"
        import argparse

        from frob.app.config import AppConfig

        args = argparse.Namespace(check_files=None)
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        assert cfg.check_files is None


class TestRunRuffFilesArgv:
    """`_run_ruff`/`_run_ty` receive `files` and pass those paths to the
    tool's argv instead of `str(root)`."""

    def test_ruff_check_uses_files_not_root(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests src/frob/check/_python.py::_run_ruff kind="unit"
        import frob.check._python as python_mod

        seen: list[list[str]] = []

        def _fake_run(argv, **kw):  # noqa: ANN001
            seen.append(argv)
            return Ok(_FakeProc("[]", 0))

        monkeypatch.setattr(python_mod, "guarded_subprocess_run", _fake_run)
        python_mod._run_ruff(tmp_path, None, files=("a.py", "b/c.py"))
        check_argv = seen[0]
        assert "a.py" in check_argv
        assert "b/c.py" in check_argv
        # T-4413: the LAST two argv entries are the target path list;
        # `root` still appears earlier as `--project <root>` (uv's own
        # project-resolution flag, unrelated to what gets linted).
        assert check_argv[-2:] == ["a.py", "b/c.py"]

    def test_ruff_format_uses_files_not_root(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests src/frob/check/_python.py::_ruff_format_result kind="unit"
        import frob.check._python as python_mod

        seen: list[list[str]] = []

        def _fake_run(argv, **kw):  # noqa: ANN001
            seen.append(argv)
            return Ok(_FakeProc("", 0))

        monkeypatch.setattr(python_mod, "guarded_subprocess_run", _fake_run)
        python_mod._run_ruff(tmp_path, None, skip_check=True, files=("a.py",))
        assert seen[0][-1] == "a.py"

    def test_ruff_no_files_falls_back_to_root(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_ruff kind="unit"
        import frob.check._python as python_mod

        seen: list[list[str]] = []

        def _fake_run(argv, **kw):  # noqa: ANN001
            seen.append(argv)
            return Ok(_FakeProc("[]", 0))

        monkeypatch.setattr(python_mod, "guarded_subprocess_run", _fake_run)
        python_mod._run_ruff(tmp_path, None)
        assert str(tmp_path) in seen[0]

    def test_ty_base_cmd_uses_files_not_root(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/_python.py::_ty_base_cmd kind="unit"
        import frob.check._python as python_mod

        cmd, _scan = python_mod._ty_base_cmd(tmp_path, files=("x/y.py",))
        # T-4413: "ty check <targets>" -- the target argv slot is
        # `x/y.py`, not `str(tmp_path)` (root still appears via
        # `--project`, unrelated to the check target itself).
        assert cmd[cmd.index("check") + 1] == "x/y.py"

    def test_ty_base_cmd_no_files_falls_back_to_root(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/_python.py::_ty_base_cmd kind="unit"
        import frob.check._python as python_mod

        cmd, _scan = python_mod._ty_base_cmd(tmp_path)
        assert str(tmp_path) in cmd


class TestPythonTasksScoping:
    """`_python_tasks`: `files` reaches ruff/ty/gates; `arch`/`cycle`/
    `dup`/`exports` (`_REPO_WIDE_STAGES`) are called with the plain `root`
    signature they always used, never a `files=` kwarg."""

    def test_ruff_ty_gates_receive_files(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests src/frob/check/__init__.py::_python_tasks kind="unit"
        import frob.check as check_mod

        calls: dict[str, dict] = {}

        def _spy(name):
            def _fn(*a, **kw):  # noqa: ANN001
                calls[name] = kw
                return None

            return _fn

        monkeypatch.setattr(
            check_mod,
            "_run_ruff",
            lambda root, args, **kw: calls.setdefault("ruff", kw),
        )  # noqa: E501
        monkeypatch.setattr(
            check_mod, "_run_ty", lambda root, **kw: calls.setdefault("ty", kw)
        )  # noqa: E501
        monkeypatch.setattr(
            check_mod, "_run_gates", lambda root, **kw: calls.setdefault("gates", kw)
        )  # noqa: E501
        monkeypatch.setattr(
            check_mod, "_run_arch", lambda root: calls.setdefault("arch", {})
        )
        monkeypatch.setattr(
            check_mod, "_run_cycle", lambda root: calls.setdefault("cycle", {})
        )
        monkeypatch.setattr(
            check_mod, "_run_dup", lambda root: calls.setdefault("dup", {})
        )
        monkeypatch.setattr(
            check_mod, "_run_exports", lambda root: calls.setdefault("exports", {})
        )  # noqa: E501
        monkeypatch.setattr(
            check_mod, "_run_bind", lambda root: calls.setdefault("bind", {})
        )

        skips = check_mod._python_skip_flags(
            skip_ruff=False,
            skip_ty=False,
            skip_arch=False,
            skip_cycle=False,
            skip_dup=False,
            skip_bind=False,
            skip_exports=False,
            skip_gates=False,
        )
        tasks = check_mod._python_tasks(
            tmp_path,
            only=None,
            gate_only=frozenset(),
            ruff_args=None,
            ticket=None,
            base=None,
            skips=skips,
            files=("scoped.py",),
        )
        for _label, fn in tasks:
            fn()

        assert calls["ruff"]["files"] == ("scoped.py",)
        assert calls["ty"]["files"] == ("scoped.py",)
        assert calls["gates"]["files"] == ("scoped.py",)
        # repo-wide stages: no files kwarg was passed to them at all.
        for name in ("arch", "cycle", "dup", "exports"):
            assert calls[name] == {}

    def test_no_files_is_unscoped(self, tmp_path: Path, monkeypatch) -> None:
        # frob:tests src/frob/check/__init__.py::_python_tasks kind="unit"
        import frob.check as check_mod

        calls: dict[str, dict] = {}
        monkeypatch.setattr(
            check_mod,
            "_run_ruff",
            lambda root, args, **kw: calls.setdefault("ruff", kw),
        )  # noqa: E501
        monkeypatch.setattr(
            check_mod, "_run_ty", lambda root, **kw: calls.setdefault("ty", kw)
        )  # noqa: E501
        monkeypatch.setattr(
            check_mod, "_run_gates", lambda root, **kw: calls.setdefault("gates", kw)
        )  # noqa: E501
        monkeypatch.setattr(check_mod, "_run_arch", lambda root: None)
        monkeypatch.setattr(check_mod, "_run_cycle", lambda root: None)
        monkeypatch.setattr(check_mod, "_run_dup", lambda root: None)
        monkeypatch.setattr(check_mod, "_run_exports", lambda root: None)
        monkeypatch.setattr(check_mod, "_run_bind", lambda root: None)

        skips = check_mod._python_skip_flags(
            skip_ruff=False,
            skip_ty=False,
            skip_arch=False,
            skip_cycle=False,
            skip_dup=False,
            skip_bind=False,
            skip_exports=False,
            skip_gates=False,
        )
        tasks = check_mod._python_tasks(
            tmp_path,
            only=None,
            gate_only=frozenset(),
            ruff_args=None,
            ticket=None,
            base=None,
            skips=skips,
        )
        for _label, fn in tasks:
            fn()

        assert calls["ruff"]["files"] is None
        assert calls["ty"]["files"] is None
        assert calls["gates"]["files"] is None


class TestGateConfigFiles:
    """`GateConfig.files` defaults `None` and round-trips through the
    model unchanged."""

    def test_default_none(self) -> None:
        # frob:tests src/frob/gates/_models.py::GateConfig kind="unit"
        from frob.gates import GateConfig

        assert GateConfig(root=".").files is None

    def test_explicit_files(self) -> None:
        # frob:tests src/frob/gates/_models.py::GateConfig kind="unit"
        from frob.gates import GateConfig

        cfg = GateConfig(root=".", files=("a.py", "b.py"))
        assert cfg.files == ("a.py", "b.py")

    def test_repo_wide_gates_constant(self) -> None:
        # frob:tests src/frob/gates/__init__.py::REPO_WIDE_GATES kind="unit"
        from frob.gates import REPO_WIDE_GATES

        assert REPO_WIDE_GATES == frozenset(
            {"tickets", "milestone", "release", "cross_ticket_leakage", "sys"}
        )


class TestRapidLandFilesWiring:
    """`_land_core_invoke`: rapid passes `--files` (diff-touched + direct
    dependents) to the shared check spawn; standard passes nothing."""

    def test_rapid_check_scope_files_none_touched_paths_is_none(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_rapid_check_scope_files \
        # kind="unit"
        from frob.app.ticket_runner._land_cmd import _rapid_check_scope_files

        assert _rapid_check_scope_files(tmp_path, "T-0001", None) is None

    def test_rapid_check_scope_files_empty_touched_paths_is_none(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_rapid_check_scope_files \
        # kind="unit"
        from frob.app.ticket_runner._land_cmd import _rapid_check_scope_files

        assert _rapid_check_scope_files(tmp_path, "T-0001", frozenset()) is None

    def test_rapid_check_scope_files_falls_back_on_graph_error(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_rapid_check_scope_files \
        # kind="unit"
        from typani import Err

        import frob.app.ticket_runner._land_cmd as land_cmd_mod
        import frob.graph as graph_mod

        monkeypatch.setattr(graph_mod, "build_graph", lambda root, cache: Err("boom"))
        result = land_cmd_mod._rapid_check_scope_files(
            tmp_path, "T-0001", frozenset({"a.py"})
        )
        assert result is None

    def test_rapid_check_scope_files_includes_touched_and_dependents(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_rapid_check_scope_files \
        # kind="unit"
        import sys

        from typani import Ok

        import frob.app.ticket_runner._land_cmd as land_cmd_mod
        import frob.graph as graph_mod
        import frob.graph.affects  # noqa: F401 -- ensures sys.modules entry exists

        affects_mod = sys.modules["frob.graph.affects"]

        class _Snapshot:
            symbols = {"a.py::f": object(), "b.py::g": object()}

        monkeypatch.setattr(
            graph_mod, "build_graph", lambda root, cache: Ok(_Snapshot())
        )  # noqa: E501

        class _Affected:
            def __init__(self, dependents):
                self.dependents = dependents

        def _fake_affects(snapshot, symref, *, max_depth=1, **kw):  # noqa: ANN001
            if symref == "a.py::f":
                return _Affected(("b.py::g",))
            return _Affected(())

        monkeypatch.setattr(affects_mod, "affects", _fake_affects)

        result = land_cmd_mod._rapid_check_scope_files(
            tmp_path, "T-0001", frozenset({"a.py"})
        )
        assert result is not None
        assert set(result) == {"a.py", "b.py"}

    def test_land_touched_paths_against_main_includes_unrelated_dev_commit(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_land_touched_paths \
        # kind="unit"
        # frob:ticket T-4547
        """Repro (T-4547, designated BUG002 repro): a worktree branched
        from `dev` after `dev` has diverged from `main` by an unrelated
        commit. Diffing against the hardcoded/default `target_branch=
        "main"` (today's pre-fix behaviour, still the function's default)
        picks up `dev`'s unrelated commit too, since `merge-base(worktree,
        main)` sits BEFORE that commit -- this is the exact 252-vs-6-file
        defect measured in the T-4511 land log."""
        import subprocess

        from frob.app.ticket_runner._land_cmd import _land_touched_paths
        from tests.conftest import _git_init, _write

        _git_init(tmp_path)
        subprocess.run(["git", "checkout", "-q", "-b", "dev"], cwd=tmp_path, check=True)
        _write(tmp_path, "unrelated.py", "x = 1\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "unrelated dev commit"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(
            ["git", "checkout", "-q", "-b", "t-0001", "dev"], cwd=tmp_path, check=True
        )
        _write(tmp_path, "own.py", "y = 2\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "own ticket commit"],
            cwd=tmp_path,
            check=True,
        )

        against_main = _land_touched_paths(tmp_path, "T-0001")
        assert against_main is not None
        assert "unrelated.py" in against_main, (
            "pre-fix behaviour: main-relative diff picks up dev's own unrelated commit"
        )
        assert "own.py" in against_main

        against_dev = _land_touched_paths(tmp_path, "T-0001", target_branch="dev")
        assert against_dev is not None
        assert "unrelated.py" not in against_dev, (
            "T-4547 fix: diffing against the resolved land target (dev) "
            "excludes dev's own prior, unrelated commit"
        )
        assert "own.py" in against_dev

    def test_shared_check_spawn_fn_appends_files_argv(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_verify.py::_shared_check_spawn_fn \
        # kind="unit"
        from typani import Err

        import frob.app.ticket_runner as ticket_runner_mod
        import frob.app.ticket_runner._verify as verify_mod

        seen: list[list[str]] = []

        def _fake_guarded(argv, **kw):  # noqa: ANN001
            seen.append(argv)
            return Err("stop-here")

        monkeypatch.setattr(ticket_runner_mod, "guarded_subprocess_run", _fake_guarded)
        spawn = verify_mod._shared_check_spawn_fn(
            tmp_path, "T-0001", files=("a.py", "b.py")
        )
        spawn()
        argv = seen[0]
        assert argv.count("--files") == 2
        assert "a.py" in argv
        assert "b.py" in argv

    def test_shared_check_spawn_fn_no_files_omits_flag(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_verify.py::_shared_check_spawn_fn \
        # kind="unit"
        from typani import Err

        import frob.app.ticket_runner as ticket_runner_mod
        import frob.app.ticket_runner._verify as verify_mod

        seen: list[list[str]] = []

        def _fake_guarded(argv, **kw):  # noqa: ANN001
            seen.append(argv)
            return Err("stop-here")

        monkeypatch.setattr(ticket_runner_mod, "guarded_subprocess_run", _fake_guarded)
        spawn = verify_mod._shared_check_spawn_fn(tmp_path, "T-0001")
        spawn()
        assert "--files" not in seen[0]
