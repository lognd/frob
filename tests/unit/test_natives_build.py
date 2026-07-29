"""T-0864: `frob.natives.build_natives` (`maturin develop` per declared
`[[native]]` rust crate, shared git-common-dir-keyed `CARGO_TARGET_DIR`) and
`frob.app.natives_runner`'s CLI wiring."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typani import Err, Ok

from frob.app import natives_runner
from frob.app.config import AppConfig
from frob.natives import BuildReport, CrateBuildResult, NativesError, build_natives
from frob.natives import _build as native_build_module
from frob.process._guard import ProcessGuardError

_ROOT = Path(__file__).resolve().parent.parent.parent


def _core_recipe() -> str:
    """The `core:` target's recipe lines from the repo's real Makefile,
    verbatim -- a static assertion that `make core` stays a one-line
    `frob natives build` shim (T-0864 acceptance criterion 3) rather than
    re-parsing a copy that could drift from the real file."""
    text = (_ROOT / "Makefile").read_text(encoding="utf-8")
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("core:"))
    end = start + 1
    while end < len(lines) and (lines[end].startswith("\t") or not lines[end].strip()):
        end += 1
    return "\n".join(lines[start:end])


# frob:ticket T-0864
class TestMakefileCoreShim:
    """T-0864 acceptance criterion 3: `make core` is a one-line delegation
    to `uv run frob natives build`, with no cache logic hand-maintained in
    the Makefile."""

    def test_core_recipe_is_one_line_natives_build_shim(self) -> None:
        # frob:tests tests/unit/test_natives_build.py::TestMakefileCoreShim.test_core_recipe_is_one_line_natives_build_shim kind="unit"  # noqa: E501
        recipe = _core_recipe()
        body_lines = [ln for ln in recipe.splitlines()[1:] if ln.strip()]
        assert body_lines == ["\tuv run frob natives build"]

    def test_core_recipe_has_no_cargo_target_dir_variable(self) -> None:
        # frob:tests tests/unit/test_natives_build.py::TestMakefileCoreShim.test_core_recipe_has_no_cargo_target_dir_variable kind="unit"  # noqa: E501
        assert "CARGO_TARGET_DIR" not in _core_recipe()


def _write_frob_toml(root: Path, *entries: str) -> None:
    """Write a minimal `frob.toml` with the given `[[native]]` TOML blocks."""
    (root / "frob.toml").write_text("\n".join(entries) + "\n")


def _rust_native_entry(name: str) -> str:
    """One `[[native]]` TOML block declaring a rust native named `name`."""
    return f'[[native]]\nname = "{name}"\nbuild_cmd = "make core"\nlanguage = "rust"\n'


def _make_crate_dir(root: Path, name: str) -> Path:
    """Create `root/<name-with-hyphens>/Cargo.toml`, the crate directory
    `_crate_dir_for`'s underscore/hyphen convention expects."""
    crate_dir = root / name.replace("_", "-")
    crate_dir.mkdir(parents=True)
    (crate_dir / "Cargo.toml").write_text(f'[package]\nname = "{name}"\n')
    return crate_dir


def _fake_completed(returncode: int, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(
        args=["uvx"], returncode=returncode, stdout=stdout, stderr=stderr
    )


# frob:ticket T-0864
class TestBuildNatives:
    """`build_natives`'s infra-failure and per-crate build paths."""

    def test_no_native_entries_is_err_no_natives(self, tmp_path: Path) -> None:
        # frob:tests src/frob/natives/_build.py::build_natives kind="unit"
        _write_frob_toml(tmp_path)  # empty frob.toml, no [[native]] entries
        result = build_natives(tmp_path)
        assert result.is_err
        assert result.danger_err is NativesError.NoNatives

    def test_no_frob_toml_is_err_no_natives(self, tmp_path: Path) -> None:
        # frob:tests src/frob/natives/_build.py::build_natives kind="unit"
        result = build_natives(tmp_path)
        assert result.is_err
        assert result.danger_err is NativesError.NoNatives

    def test_unparseable_frob_toml_is_err_load_failed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/natives/_build.py::build_natives kind="unit"
        # Proves the `load_natives(...).is_err` branch: a malformed
        # frob.toml (unparseable TOML, not merely "no [[native]] entries")
        # surfaces as `NativesError.LoadFailed`, distinct from the empty-
        # declarations `NoNatives` case covered above.
        (tmp_path / "frob.toml").write_text("this is not valid toml [[[")
        result = build_natives(tmp_path)
        assert result.is_err
        assert result.danger_err is NativesError.LoadFailed

    def test_not_a_git_repo_is_err(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/natives/_build.py::build_natives kind="unit"
        from frob.gitio import GitError

        _write_frob_toml(tmp_path, _rust_native_entry("strata_core"))
        _make_crate_dir(tmp_path, "strata_core")
        monkeypatch.setattr(
            native_build_module, "git_common_dir", lambda root: Err(GitError.GitFailed)
        )
        result = build_natives(tmp_path)
        assert result.is_err
        assert result.danger_err is NativesError.NotAGitRepo

    def test_builds_declared_rust_natives(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/natives/_build.py::build_natives kind="unit"
        _write_frob_toml(
            tmp_path,
            _rust_native_entry("strata_core"),
            _rust_native_entry("frob_core"),
        )
        _make_crate_dir(tmp_path, "strata_core")
        _make_crate_dir(tmp_path, "frob_core")
        monkeypatch.setattr(
            native_build_module, "git_common_dir", lambda root: Ok(tmp_path / ".git")
        )
        spawned: list[list[str]] = []

        def _fake_run(args, **kwargs):  # noqa: ANN001, ANN002, ANN003
            spawned.append(list(args))
            assert kwargs["env"]["CARGO_TARGET_DIR"] == str(
                tmp_path / ".git" / native_build_module.CARGO_CACHE_DIRNAME
            )
            return Ok(_fake_completed(0, stdout="built"))

        monkeypatch.setattr(native_build_module, "guarded_subprocess_run", _fake_run)

        result = build_natives(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert report.ok
        assert {r.name for r in report.results} == {"strata_core", "frob_core"}
        assert len(spawned) == 2
        for args in spawned:
            assert args[:3] == ["uvx", "maturin", "develop"]

    def test_skips_native_with_no_matching_crate_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/natives/_build.py::build_natives kind="unit"
        _write_frob_toml(tmp_path, _rust_native_entry("no_such_crate"))
        monkeypatch.setattr(
            native_build_module, "git_common_dir", lambda root: Ok(tmp_path / ".git")
        )

        def _fail_if_called(args, **kwargs):  # noqa: ANN001, ANN002, ANN003
            raise AssertionError("must not spawn maturin for a missing crate dir")

        monkeypatch.setattr(
            native_build_module, "guarded_subprocess_run", _fail_if_called
        )

        result = build_natives(tmp_path)
        assert result.is_ok
        assert result.danger_ok.results == []

    def test_skips_non_rust_native(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/natives/_build.py::build_natives kind="unit"
        _write_frob_toml(
            tmp_path,
            '[[native]]\nname = "some_ts_native"\nbuild_cmd = "npm run build"\n'
            'language = "typescript"\n',
        )
        monkeypatch.setattr(
            native_build_module, "git_common_dir", lambda root: Ok(tmp_path / ".git")
        )

        def _fail_if_called(args, **kwargs):  # noqa: ANN001, ANN002, ANN003
            raise AssertionError("must not spawn maturin for a non-rust native")

        monkeypatch.setattr(
            native_build_module, "guarded_subprocess_run", _fail_if_called
        )

        result = build_natives(tmp_path)
        assert result.is_ok
        assert result.danger_ok.results == []

    def test_missing_toolchain_is_best_effort_skip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/natives/_build.py::build_natives kind="unit"
        _write_frob_toml(tmp_path, _rust_native_entry("strata_core"))
        _make_crate_dir(tmp_path, "strata_core")
        monkeypatch.setattr(
            native_build_module, "git_common_dir", lambda root: Ok(tmp_path / ".git")
        )

        def _raise_not_found(args, **kwargs):  # noqa: ANN001, ANN002, ANN003
            raise FileNotFoundError("uvx not found")

        monkeypatch.setattr(
            native_build_module, "guarded_subprocess_run", _raise_not_found
        )

        result = build_natives(tmp_path)
        assert result.is_ok
        assert result.danger_ok.results == []

    def test_exec_disabled_is_err(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/natives/_build.py::build_natives kind="unit"
        _write_frob_toml(tmp_path, _rust_native_entry("strata_core"))
        _make_crate_dir(tmp_path, "strata_core")
        monkeypatch.setattr(
            native_build_module, "git_common_dir", lambda root: Ok(tmp_path / ".git")
        )
        monkeypatch.setattr(
            native_build_module,
            "guarded_subprocess_run",
            lambda args, **kwargs: Err(ProcessGuardError.ExecDisabled),
        )

        result = build_natives(tmp_path)
        assert result.is_err
        assert result.danger_err is NativesError.ExecDisabled

    def test_failed_crate_build_reports_not_ok(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/natives/_build.py::build_natives kind="unit"
        _write_frob_toml(tmp_path, _rust_native_entry("strata_core"))
        _make_crate_dir(tmp_path, "strata_core")
        monkeypatch.setattr(
            native_build_module, "git_common_dir", lambda root: Ok(tmp_path / ".git")
        )
        monkeypatch.setattr(
            native_build_module,
            "guarded_subprocess_run",
            lambda args, **kwargs: Ok(_fake_completed(1, stderr="compile error")),
        )

        result = build_natives(tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert not report.ok
        assert report.results[0].returncode == 1
        assert not report.results[0].ok

    def test_crate_dir_outside_root_falls_back_to_absolute_display(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/natives/_build.py::build_natives kind="unit"
        # Proves the `except ValueError` fallback in `_build_one_crate`:
        # when the resolved crate directory is not actually underneath
        # `root` (so `Path.relative_to` raises), the recorded
        # `CrateBuildResult.crate_dir` falls back to the crate dir's
        # absolute string form instead of propagating the exception.
        # `_build_one_crate` is exercised directly since `build_natives`'s
        # own `_crate_dir_for` always resolves a crate dir under `root` --
        # this is a defensive branch for the private helper's own contract.
        from frob.natives._build import _build_one_crate

        outside_dir = tmp_path.parent / f"outside-crate-{tmp_path.name}"
        outside_dir.mkdir()
        (outside_dir / "Cargo.toml").write_text("[package]\nname = \"x\"\n")

        class _Spec:
            name = "strata_core"
            language = "rust"

        monkeypatch.setattr(
            native_build_module,
            "_resolve_buildable_crate",
            lambda root, spec: outside_dir,
        )
        monkeypatch.setattr(
            native_build_module,
            "guarded_subprocess_run",
            lambda args, **kwargs: Ok(_fake_completed(0, stdout="built")),
        )

        result = _build_one_crate(tmp_path, _Spec(), tmp_path / ".cargo-target")
        assert result.is_ok
        built = result.danger_ok
        assert built is not None
        assert built.crate_dir == str(outside_dir)


# frob:ticket T-0864
class TestCrateBuildResultAndReport:
    """`CrateBuildResult.ok`/`BuildReport.ok` derived-property behavior."""

    def test_crate_result_ok_true_on_zero_exit(self) -> None:
        # frob:tests src/frob/natives/_build.py::CrateBuildResult.ok kind="unit"
        r = CrateBuildResult(
            name="x", crate_dir="x", returncode=0, stdout="", stderr=""
        )
        assert r.ok

    def test_crate_result_ok_false_on_nonzero_exit(self) -> None:
        # frob:tests src/frob/natives/_build.py::CrateBuildResult.ok kind="unit"
        r = CrateBuildResult(
            name="x", crate_dir="x", returncode=1, stdout="", stderr=""
        )
        assert not r.ok

    def test_report_ok_vacuously_true_with_no_results(self, tmp_path: Path) -> None:
        # frob:tests src/frob/natives/_build.py::BuildReport.ok kind="unit"
        report = BuildReport(cargo_target_dir=tmp_path, results=[])
        assert report.ok

    def test_report_ok_false_if_any_result_failed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/natives/_build.py::BuildReport.ok kind="unit"
        report = BuildReport(
            cargo_target_dir=tmp_path,
            results=[
                CrateBuildResult(
                    name="a", crate_dir="a", returncode=0, stdout="", stderr=""
                ),
                CrateBuildResult(
                    name="b", crate_dir="b", returncode=1, stdout="", stderr=""
                ),
            ],
        )
        assert not report.ok


# frob:ticket T-0864
class TestNativesRunner:
    """`frob.app.natives_runner.run`'s CLI-facing exit-code behavior."""

    def _cfg(self, tmp_path: Path, command: str | None = "build") -> AppConfig:
        return AppConfig(natives_command=command, natives_path=tmp_path)

    def test_unknown_action_exits_2(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/natives_runner.py::run kind="unit"
        with pytest.raises(SystemExit) as exc:
            natives_runner.run(self._cfg(tmp_path, command=None))
        assert exc.value.code == 2

    def test_no_natives_declared_is_a_quiet_noop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/natives_runner.py::run kind="unit"
        monkeypatch.setattr(
            natives_runner, "build_natives", lambda root: Err(NativesError.NoNatives)
        )
        natives_runner.run(self._cfg(tmp_path))  # must not raise

    def test_infra_failure_exits_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/natives_runner.py::run kind="unit"
        monkeypatch.setattr(
            natives_runner,
            "build_natives",
            lambda root: Err(NativesError.NotAGitRepo),
        )
        with pytest.raises(SystemExit) as exc:
            natives_runner.run(self._cfg(tmp_path))
        assert exc.value.code == 1

    def test_build_reports_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/natives_runner.py::run kind="unit"
        report = BuildReport(
            cargo_target_dir=tmp_path,
            results=[
                CrateBuildResult(
                    name="strata_core",
                    crate_dir="strata-core",
                    returncode=0,
                    stdout="ok",
                    stderr="",
                )
            ],
        )
        monkeypatch.setattr(natives_runner, "build_natives", lambda root: Ok(report))
        natives_runner.run(self._cfg(tmp_path))  # must not raise

    def test_build_failure_exits_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/natives_runner.py::run kind="unit"
        report = BuildReport(
            cargo_target_dir=tmp_path,
            results=[
                CrateBuildResult(
                    name="strata_core",
                    crate_dir="strata-core",
                    returncode=1,
                    stdout="",
                    stderr="compile error",
                )
            ],
        )
        monkeypatch.setattr(natives_runner, "build_natives", lambda root: Ok(report))
        with pytest.raises(SystemExit) as exc:
            natives_runner.run(self._cfg(tmp_path))
        assert exc.value.code == 1
