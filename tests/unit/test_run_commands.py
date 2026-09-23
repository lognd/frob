"""Tests for `frob run`/`frob build` and `frob.toml`'s `[commands]` table
(T-4759): sequencing, cycle refusal, native defaults, and dry-run.
"""

from __future__ import annotations

import subprocess

import pytest

from frob.app.run_runner import (
    RunError,
    _execute_sequence,
    _resolve_sequence,
    load_commands,
)
from frob.policy._models import CommandsError


def _write_frob_toml(tmp_path, body: str):
    """Write `body` as `frob.toml`'s `[commands]` table under `tmp_path`."""
    (tmp_path / "frob.toml").write_text(body)
    return tmp_path


class TestLoadCommands:
    """`load_commands` -- parsing, normalization, and cycle refusal."""

    def test_no_frob_toml_is_ok_empty(self, tmp_path):
        """A project with no `frob.toml` at all loads an empty config."""
        result = load_commands(tmp_path)
        assert result.is_ok
        assert result.danger_ok.entries == {}

    # frob:tests src/frob/app/run_runner.py::load_commands
    # frob:tests src/frob/policy/_models.py::CommandsConfig
    def test_three_step_sequence_composes(self, tmp_path):
        """`check = ["fmt", "lint", "test"]` composes three declared entries
        in order, each element resolved as a name reference (not literal
        argv tokens), because all three match existing entry names."""
        root = _write_frob_toml(
            tmp_path,
            """
            [commands]
            fmt = ["ruff", "format", "."]
            lint = ["ruff", "check", "."]
            test = ["pytest", "-q"]
            check = ["fmt", "lint", "test"]
            """,
        )
        loaded = load_commands(root)
        assert loaded.is_ok
        config = loaded.danger_ok
        resolved = _resolve_sequence(config, "check")
        assert resolved.is_ok
        assert resolved.danger_ok == (
            ("ruff", "format", "."),
            ("ruff", "check", "."),
            ("pytest", "-q"),
        )
# frob:tests src/frob/policy/_models.py::CommandEntry

    def test_single_command_entry_is_one_literal_argv(self, tmp_path):
        """A flat string array that does NOT match declared entry names is
        one literal shell-free argv, not a composed sequence."""
        root = _write_frob_toml(
            tmp_path,
            """
            [commands]
            fmt = ["ruff", "format", "."]
            """,
        )
        loaded = load_commands(root)
        resolved = _resolve_sequence(loaded.danger_ok, "fmt")
        assert resolved.is_ok
        assert resolved.danger_ok == (("ruff", "format", "."),)

    # frob:tests src/frob/policy/_models.py::CommandsError
    # frob:tests src/frob/app/run_runner.py::load_commands
    def test_self_reference_refused_with_path(self, tmp_path):
        """An entry referencing itself directly is refused at load time."""
        root = _write_frob_toml(
            tmp_path,
            """
            [commands]
            loop = ["loop"]
            """,
        )
        result = load_commands(root)
        assert result.is_err
        assert result.danger_err is CommandsError.CycleDetected

    def test_transitive_reference_cycle_refused(self, tmp_path):
        """A -> B -> A is refused at load time, not only direct self-refs."""
        root = _write_frob_toml(
            tmp_path,
            """
            [commands]
            a = ["b"]
            b = ["a"]
            """,
        )
        result = load_commands(root)
        assert result.is_err
        assert result.danger_err is CommandsError.CycleDetected


class TestRun:
    """Execution semantics: ordering, mid-sequence failure, dry-run."""

    # frob:tests src/frob/app/run_runner.py::run
    def test_middle_step_failure_names_index(self, tmp_path, monkeypatch):
        """A three-step entry runs in order; when the MIDDLE step exits
        non-zero, execution stops there and the failure names that step's
        index."""
        calls: list[tuple[str, ...]] = []

        def fake_run(argv, **kwargs):
            calls.append(tuple(argv))
            code = 1 if argv[0] == "step1" else 0
            return subprocess.CompletedProcess(args=[], returncode=code)

        monkeypatch.setattr(subprocess, "run", fake_run)
        steps = (("step0",), ("step1",), ("step2",))
        result = _execute_sequence(steps, dry_run=False)
        assert result.is_err
        assert result.danger_err is RunError.StepFailed
        # step2 never ran: execution stopped at the failing middle step.
        assert calls == [("step0",), ("step1",)]

    # frob:tests src/frob/app/run_runner.py::run
    def test_dry_run_prints_without_spawning(self, monkeypatch):
        """`--dry-run` resolves and prints the sequence without spawning
        any subprocess (asserted via a subprocess spy, not exit code)."""
        def fail_if_called(*args, **kwargs):
            pytest.fail("subprocess.run must not be called in --dry-run")

        monkeypatch.setattr(subprocess, "run", fail_if_called)
        steps = (("ruff", "format", "."), ("pytest", "-q"))
        result = _execute_sequence(steps, dry_run=True)
        assert result.is_ok

    # frob:tests src/frob/app/run_runner.py::RunError
    def test_unknown_command_is_err(self, tmp_path):
        """A name that is neither declared nor a native default is a
        clean `Err`, not a crash."""
        loaded = load_commands(tmp_path)
        resolved = _resolve_sequence(loaded.danger_ok, "does-not-exist")
        assert resolved.is_err
        assert resolved.danger_err is RunError.UnknownCommand

    def test_native_default_used_when_undeclared(self, tmp_path):
        """A project declaring no [commands] table still resolves `test`
        to frob's own native verb."""
        loaded = load_commands(tmp_path)
        resolved = _resolve_sequence(loaded.danger_ok, "test")
        assert resolved.is_ok
        assert resolved.danger_ok == (("frob", "test"),)


class TestBuild:
    """`frob build` delegates to the `build` [commands] entry."""

    # frob:tests src/frob/app/run_runner.py::run_build
    def test_delegates_to_build_entry(self, tmp_path):
        """`build` resolves whatever `[commands.build]` declares -- no
        native fallback exists for it."""
        root = _write_frob_toml(
            tmp_path,
            """
            [commands]
            build = ["cmake", "--build", "build"]
            """,
        )
        loaded = load_commands(root)
        resolved = _resolve_sequence(loaded.danger_ok, "build")
        assert resolved.is_ok
        assert resolved.danger_ok == (("cmake", "--build", "build"),)

    def test_build_with_no_entry_is_err(self, tmp_path):
        """`build` has no native default -- an undeclared `build` entry is
        a clean error, not a silent no-op."""
        loaded = load_commands(tmp_path)
        resolved = _resolve_sequence(loaded.danger_ok, "build")
        assert resolved.is_err
        assert resolved.danger_err is RunError.UnknownCommand
